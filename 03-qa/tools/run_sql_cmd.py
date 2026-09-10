#!/usr/bin/env python3
"""
SQL Execution & Database Seeding Tool for Clean Room QA Testing.
Supports executing SQL queries, migrations, and seed scripts against SQLite
(and standard databases) with formatted output.
@implements REQ-TOOL-SQL
"""

import sys
import os
import json
import sqlite3
import argparse
from pathlib import Path
from typing import List, Dict, Any, Tuple


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
        # Check if query contains multiple statements
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

    # Header
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
    parser.add_argument("--db", "-d", required=True, help="Database file path (SQLite) or connection URI")
    parser.add_argument("--query", "-q", help="SQL statement(s) to execute")
    parser.add_argument("--file", "-f", help="Path to .sql file to execute (migrations/seed scripts)")
    parser.add_argument("--format", choices=["table", "json", "csv"], default="table", help="Output format for SELECT queries")
    parser.add_argument("--read-only", action="store_true", help="Open database in read-only mode")
    parser.add_argument("--expect-count", type=int, help="Assert that exactly N rows are returned")

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

    db_path = Path(args.db)

    try:
        columns, rows, rows_affected = execute_sqlite(
            db_path=db_path,
            query=sql_text,
            read_only=args.read_only
        )
    except Exception as e:
        print(f"[!] SQL Execution Error: {e}", file=sys.stderr)
        sys.exit(1)

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
            print(f"[!] Assertion failed: Expected {args.expect_count} rows, found {actual_count}.", file=sys.stderr)
            sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()
