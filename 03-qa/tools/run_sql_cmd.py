#!/usr/bin/env python3
"""
SQL Execution & Database Seeding Tool for Clean Room QA Testing.
Supports executing SQL queries, migrations, and seed scripts against SQLite
and containerized databases (Microsoft SQL Server, PostgreSQL, MySQL) with audit logging.
@implements REQ-TOOL-SQL
"""

import sys
import os
import re
import json
import sqlite3
import subprocess
import argparse
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional

# Import audit logger
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
import audit_logger


def execute_sqlite(
    db_path: Path,
    query: str,
    read_only: bool = False
) -> Tuple[List[str], List[Tuple[Any, ...]], int]:
    """Execute SQL query or script against a SQLite database."""
    if read_only:
        uri = f"file:{db_path.resolve()}?mode=ro"
        conn = sqlite3.connect(uri, uri=True)
    else:
        conn = sqlite3.connect(str(db_path))

    cursor = conn.cursor()
    columns = []
    rows = []
    rows_affected = 0

    try:
        statements = [s.strip() for s in query.split(";") if s.strip()]
        if len(statements) > 1:
            cursor.executescript(query)
            conn.commit()
            rows_affected = conn.total_changes
        else:
            cursor.execute(query)
            if cursor.description:
                columns = [desc[0] for desc in cursor.description]
                rows = cursor.fetchall()
            else:
                conn.commit()
                rows_affected = cursor.rowcount
    finally:
        conn.close()

    return columns, rows, rows_affected


def auto_discover_sql_container(engine: str = "mssql") -> Tuple[Optional[str], Optional[str]]:
    """Inspect docker ps to find running container and credentials."""
    try:
        res = subprocess.run(["docker", "ps", "--format", "{{.Names}}\t{{.Image}}"], capture_output=True, text=True)
        if res.returncode != 0:
            return None, None
        container_name = None
        for line in res.stdout.strip().split("\n"):
            if not line.strip():
                continue
            name, img = line.split("\t", 1)
            if engine == "mssql" and ("mssql" in img or "sql" in name):
                container_name = name
                break
            elif engine == "postgres" and ("postgres" in img or "psql" in name):
                container_name = name
                break

        if not container_name:
            return None, None

        # Inspect environment for password
        insp = subprocess.run(["docker", "inspect", container_name], capture_output=True, text=True)
        password = None
        if insp.returncode == 0:
            for env_match in re.findall(r'"(MSSQL_SA_PASSWORD|POSTGRES_PASSWORD)=([^"]+)"', insp.stdout):
                password = env_match[1]
                break

        return container_name, password
    except Exception:
        return None, None


def parse_sqlcmd_table(stdout: str) -> Tuple[List[str], List[Tuple[Any, ...]], int]:
    """Parse raw sqlcmd table output into structured columns, rows, and affected count."""
    lines = [line.rstrip() for line in stdout.strip().split("\n") if line.strip()]
    if not lines:
        return [], [], 0

    rows_affected = 0
    data_lines = []
    for line in lines:
        if line.startswith("(") and "affected)" in line:
            try:
                rows_affected = int(line.split()[0].replace("(", ""))
            except Exception:
                pass
        else:
            data_lines.append(line)

    if len(data_lines) < 2:
        return [], [], rows_affected

    header_line = data_lines[0]
    divider_line = data_lines[1]
    if not all(c in "- " for c in divider_line):
        return [], [], rows_affected

    col_spans = []
    in_dash = False
    start_idx = 0
    for idx, c in enumerate(divider_line):
        if c == "-" and not in_dash:
            in_dash = True
            start_idx = idx
        elif c != "-" and in_dash:
            in_dash = False
            col_spans.append((start_idx, idx))
    if in_dash:
        col_spans.append((start_idx, len(divider_line)))

    columns = [header_line[s:e].strip() for s, e in col_spans]
    rows = []
    for row_line in data_lines[2:]:
        row = []
        for s, e in col_spans:
            val = row_line[s:e].strip() if s < len(row_line) else ""
            if val == "NULL":
                row.append(None)
            else:
                try:
                    row.append(int(val))
                except ValueError:
                    try:
                        row.append(float(val))
                    except ValueError:
                        row.append(val)
        rows.append(tuple(row))
    return columns, rows, rows_affected or len(rows)


def execute_docker_sql(
    container: str,
    query: str,
    database: Optional[str] = None,
    engine: str = "mssql",
    user: str = "sa",
    password: Optional[str] = None
) -> Tuple[List[str], List[Tuple[Any, ...]], int]:
    """Execute SQL query inside a running docker container."""
    if engine == "mssql":
        # Check tools path in container
        sqlcmd_bin = "/opt/mssql-tools18/bin/sqlcmd"
        cmd = ["docker", "exec", container, sqlcmd_bin, "-S", "localhost", "-U", user]
        if password:
            cmd.extend(["-P", password])
        cmd.append("-C")  # Trust certificate
        if database:
            cmd.extend(["-d", database])
        cmd.extend(["-Q", query])

        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode != 0:
            # Fallback to mssql-tools (version 17)
            if "No such file" in res.stderr:
                cmd[3] = "/opt/mssql-tools/bin/sqlcmd"
                res = subprocess.run(cmd, capture_output=True, text=True)
            if res.returncode != 0:
                raise RuntimeError(f"Docker sqlcmd error: {res.stderr or res.stdout}")

        return parse_sqlcmd_table(res.stdout)
    else:
        raise NotImplementedError(f"Engine {engine} in docker not yet supported.")


def format_table(columns: List[str], rows: List[Tuple[Any, ...]]) -> str:
    """Format query results into a markdown/terminal table."""
    if not columns:
        return "(No rows returned)"

    col_widths = [len(c) for c in columns]
    str_rows = []
    for r in rows:
        formatted_row = [str(val) if val is not None else "NULL" for val in r]
        str_rows.append(formatted_row)
        for i, val in enumerate(formatted_row):
            col_widths[i] = max(col_widths[i], len(val))

    header = " | ".join(c.ljust(col_widths[i]) for i, c in enumerate(columns))
    separator = "-+-".join("-" * col_widths[i] for i in range(len(columns)))
    body_lines = [" | ".join(r[i].ljust(col_widths[i]) for i in range(len(columns))) for r in str_rows]

    return "\n".join([header, separator] + body_lines)


def format_json(columns: List[str], rows: List[Tuple[Any, ...]]) -> str:
    """Format query results into JSON objects."""
    records = []
    for row in rows:
        records.append({col: row[i] for i, col in enumerate(columns)})
    return json.dumps(records, indent=2)


def format_csv(columns: List[str], rows: List[Tuple[Any, ...]]) -> str:
    """Format query results into CSV format."""
    lines = [",".join(columns)]
    for row in rows:
        lines.append(",".join(f'"{val}"' if "," in str(val) else str(val) for val in row))
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Clean Room SQL Execution & Seeding CLI")
    parser.add_argument("--driver", choices=["sqlite", "docker"], default="sqlite", help="Database driver type (default: sqlite)")
    parser.add_argument("--db", "-d", help="Database file path (SQLite)")
    parser.add_argument("--container", "-c", help="Docker container name or ID for containerized DB")
    parser.add_argument("--engine", choices=["mssql", "postgres"], default="mssql", help="Database engine for docker driver")
    parser.add_argument("--database", help="Target database name (e.g. tododb)")
    parser.add_argument("--user", "-u", default="sa", help="Database username (default: sa)")
    parser.add_argument("--password", "-p", help="Database password (auto-discovered if omitted on docker)")
    parser.add_argument("--query", "-q", help="SQL statement(s) to execute")
    parser.add_argument("--file", "-f", help="Path to .sql file to execute")
    parser.add_argument("--format", choices=["table", "json", "csv"], default="table", help="Output format for query results")
    parser.add_argument("--read-only", action="store_true", help="Open SQLite database in read-only mode")
    parser.add_argument("--expect-count", type=int, help="Assert that exactly N rows are returned")
    parser.add_argument("--step-id", help="Logical identifier for workflow step audit logging")
    parser.add_argument("--audit-file", help="Custom path to audit.jsonl log file")

    args = parser.parse_args()

    sql_text = args.query
    if args.file:
        file_path = Path(args.file)
        if not file_path.is_file():
            print(f"[!] SQL file not found: {file_path}", file=sys.stderr)
            sys.exit(1)
        sql_text = file_path.read_text(encoding="utf-8")

    if not sql_text:
        print("[!] No SQL query or file provided. Specify --query or --file.", file=sys.stderr)
        sys.exit(1)

    import time
    start_time = time.time()
    failures = []
    columns = []
    rows = []
    rows_affected = 0
    error_msg = None

    try:
        if args.driver == "docker":
            container = args.container
            password = args.password
            if not container or not password:
                auto_cont, auto_pass = auto_discover_sql_container(engine=args.engine)
                container = container or auto_cont
                password = password or auto_pass

            if not container:
                raise ValueError("Could not find or discover a running SQL Docker container.")

            columns, rows, rows_affected = execute_docker_sql(
                container=container,
                query=sql_text,
                database=args.database,
                engine=args.engine,
                user=args.user,
                password=password
            )
        else:
            if not args.db:
                raise ValueError("--db path is required for sqlite driver.")
            db_path = Path(args.db)
            columns, rows, rows_affected = execute_sqlite(
                db_path=db_path,
                query=sql_text,
                read_only=args.read_only
            )
    except Exception as e:
        error_msg = str(e)
        failures.append(f"SQL execution error: {error_msg}")
        print(f"[!] SQL Execution Error: {e}", file=sys.stderr)

    duration_ms = round((time.time() - start_time) * 1000, 2)

    if not error_msg:
        if columns:
            if args.format == "json":
                print(format_json(columns, rows))
            elif args.format == "csv":
                print(format_csv(columns, rows))
            else:
                print(format_table(columns, rows))
                print(f"\n({len(rows)} row(s) returned)")
        else:
            print(f"[✓] Query executed successfully. {rows_affected} rows affected.")

        if args.expect_count is not None:
            actual_count = len(rows)
            if actual_count != args.expect_count:
                failures.append(f"Expected {args.expect_count} rows, found {actual_count}.")
                print(f"[!] Assertion failed: Expected {args.expect_count} rows, found {actual_count}.", file=sys.stderr)

    # Record to live audit log
    step_status = "FAIL" if failures else "PASS"
    audit_logger.record_step(
        tool="run_sql_cmd",
        step_id=args.step_id,
        input_data={
            "driver": args.driver,
            "query": sql_text,
            "database": args.database or args.db,
            "container": args.container
        },
        output_data={
            "columns": columns,
            "row_count": len(rows),
            "rows_affected": rows_affected,
            "records": [{columns[i]: r[i] for i in range(len(columns))} for r in rows[:10]] if columns else [],
            "error": error_msg
        },
        assertions={
            "expected_count": args.expect_count,
            "passed": len(failures) == 0,
            "failures": failures
        },
        duration_ms=duration_ms,
        status=step_status,
        custom_audit_path=args.audit_file
    )

    if failures:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
