#!/usr/bin/env python3
"""
Clean Room QA Runner CLI.
Provides full lifecycle management for clean room testing:
- Workspace setup and target repo isolation
- Automated test discovery
- Test step execution with timeout and log capture
- Standardized QA report generation for 04-review handoff
"""

import os
import sys
import shutil
import subprocess
import argparse
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

# Import discovery engine
SCRIPT_DIR = Path(__file__).resolve().parent
BASE_DIR = SCRIPT_DIR.parent
DEFAULT_TARGET = BASE_DIR / "target-repo"
DEFAULT_REPORTS = BASE_DIR / "reports"
DEFAULT_TEMPLATE = BASE_DIR / "templates" / "REPORT_TEMPLATE.md"

sys.path.insert(0, str(SCRIPT_DIR))
import test_discovery


def clean_directory_contents(target_path: Path, preserve_gitkeep: bool = True):
    """
    Remove all files and subdirectories inside target_path.
    @implements REQ-ISO-01
    """
    if not target_path.exists():
        target_path.mkdir(parents=True, exist_ok=True)
        if preserve_gitkeep:
            (target_path / ".gitkeep").touch()
        return

    for item in target_path.iterdir():
        if preserve_gitkeep and item.name == ".gitkeep":
            continue
        try:
            if item.is_dir() and not item.is_symlink():
                shutil.rmtree(item)
            else:
                item.unlink()
        except Exception as e:
            print(f"[WARN] Failed to remove {item}: {e}")

    if preserve_gitkeep and not (target_path / ".gitkeep").exists():
        (target_path / ".gitkeep").touch()


def setup_cleanroom(source: str, target: Path = DEFAULT_TARGET, branch: Optional[str] = None) -> bool:
    """
    Clone or copy source into clean target directory.
    @implements REQ-ISO-02
    """
    print(f"[*] Setting up clean-room in: {target}")

    source_path = Path(source).expanduser().resolve() if Path(source).expanduser().exists() else None

    if source_path and source_path.is_dir():
        clean_directory_contents(target, preserve_gitkeep=True)
        print(f"[*] Copying from local source: {source_path}")
        # Copy directory tree excluding .git to ensure clean state
        for item in source_path.iterdir():
            if item.name in [".git", "node_modules", ".venv", "__pycache__", "target-repo"]:
                continue
            dest = target / item.name
            if item.is_dir():
                shutil.copytree(item, dest, dirs_exist_ok=True)
            else:
                shutil.copy2(item, dest)
        return True
    else:
        # Treat as Git URL: destination must be completely empty or non-existent
        clean_directory_contents(target, preserve_gitkeep=False)
        print(f"[*] Cloning remote git repository: {source}")
        cmd = ["git", "clone", "--depth", "1"]
        if branch:
            cmd.extend(["--branch", branch])
        cmd.extend([source, str(target)])
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, check=True)
            print("[✓] Git clone successful.")
            return True
        except subprocess.CalledProcessError as e:
            print(f"[!] Git clone failed: {e.stderr}")
            return False


def execute_step(cmd: str, cwd: Path, timeout: int = 180) -> Dict[str, Any]:
    """
    Execute a single test command inside cwd, capturing timing, output, and exit code.
    @implements REQ-ISO-04
    @implements REQ-WORK-05
    @implements REQ-REP-02
    """
    start_time = time.time()
    print(f"\n[>] Executing: {cmd}")
    print(f"    Directory: {cwd}")

    try:
        proc = subprocess.run(
            cmd,
            cwd=cwd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        duration = round(time.time() - start_time, 2)
        status = "PASS" if proc.returncode == 0 else "FAIL"
        print(f"[{status}] (Exit code: {proc.returncode}, Duration: {duration}s)")

        return {
            "command": cmd,
            "exit_code": proc.returncode,
            "status": status,
            "duration": duration,
            "stdout": proc.stdout,
            "stderr": proc.stderr
        }
    except subprocess.TimeoutExpired as e:
        duration = round(time.time() - start_time, 2)
        print(f"[TIMEOUT] Command exceeded {timeout}s")
        return {
            "command": cmd,
            "exit_code": -1,
            "status": "TIMEOUT",
            "duration": duration,
            "stdout": e.stdout or "",
            "stderr": f"Command timed out after {timeout} seconds."
        }
    except Exception as e:
        duration = round(time.time() - start_time, 2)
        print(f"[ERROR] Execution failed: {e}")
        return {
            "command": cmd,
            "exit_code": -1,
            "status": "ERROR",
            "duration": duration,
            "stdout": "",
            "stderr": str(e)
        }


def get_commit_ref(target: Path) -> str:
    """Extract commit hash or reference if target is a git repo."""
    git_dir = target / ".git"
    if git_dir.exists():
        try:
            res = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=target, capture_output=True, text=True)
            if res.returncode == 0:
                return res.stdout.strip()
        except Exception:
            pass
    return "N/A (clean export)"


def generate_report(
    workflow_name: str,
    project_name: str,
    project_source: str,
    target_dir: Path,
    steps: List[Dict[str, Any]],
    discovery_data: Dict[str, Any],
    reports_dir: Path = DEFAULT_REPORTS,
    template_path: Path = DEFAULT_TEMPLATE
) -> Path:
    """
    Generate standardized Markdown test report and save to reports_dir.
    @implements REQ-REP-01
    @implements REQ-REP-03
    @implements REQ-REP-04
    @implements REQ-HAND-01
    @implements REQ-HAND-02
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    time_slug = datetime.now().strftime("%Y%m%d_%H%M%S")
    commit_ref = get_commit_ref(target_dir)

    total_steps = len(steps)
    passed_steps = sum(1 for s in steps if s["status"] == "PASS")
    failed_steps = sum(1 for s in steps if s["status"] != "PASS")
    total_duration = round(sum(s.get("duration", 0) for s in steps), 2)

    overall_status = "PASS" if (total_steps > 0 and failed_steps == 0) else "FAIL"
    status_badge = "🟢 PASS" if overall_status == "PASS" else "🔴 FAIL"
    handoff_status = "READY FOR 04-REVIEW" if overall_status == "PASS" else "BLOCKED (QA Failed)"

    # Build step table rows
    table_rows = []
    step_details = []
    for idx, s in enumerate(steps, 1):
        table_rows.append(
            f"| {idx} | Step {idx} | `{s['command']}` | {s['duration']}s | {s['exit_code']} | **{s['status']}** |"
        )
        # Detail section
        detail = [
            f"#### Step {idx}: `{s['command']}`",
            f"- **Status**: {s['status']}",
            f"- **Duration**: {s['duration']}s",
            f"- **Exit Code**: {s['exit_code']}",
        ]
        if s.get("stdout"):
            detail.append(f"**Output (stdout)**:\n```\n{s['stdout'].strip()}\n```")
        if s.get("stderr"):
            detail.append(f"**Error Output (stderr)**:\n```\n{s['stderr'].strip()}\n```")
        step_details.append("\n".join(detail))

    # Discovered docs list
    docs = discovery_data.get("docs_found", [])
    docs_formatted = "\n".join(f"- `{d}`" for d in docs) if docs else "- None found"

    # Recommended commands
    rec = discovery_data.get("recommended_commands", {})
    recs_formatted = "\n".join(f"- **{k.capitalize()}**: `{v}`" for k, v in rec.items() if v and k != "all") or "- None"

    # Defect analysis
    if overall_status == "FAIL":
        defects = []
        for idx, s in enumerate(steps, 1):
            if s["status"] != "PASS":
                defects.append(f"### Failure in Step {idx}: `{s['command']}`")
                defects.append(f"Exit code {s['exit_code']}. Error snippet:\n```\n{s.get('stderr') or s.get('stdout')}\n```")
                defects.append("Suggested Resolution: Check dependencies, configuration, or inspect test assertions.")
        defect_analysis = "\n\n".join(defects)
    else:
        defect_analysis = "No defects identified during this execution."

    # Load template or fallback
    if template_path.exists():
        template = template_path.read_text(encoding="utf-8")
    else:
        template = "# QA Clean Room Report\nStatus: {{OVERALL_STATUS}}\n{{STEP_TABLE_ROWS}}"

    content = template.replace("{{PROJECT_NAME}}", project_name)
    content = content.replace("{{PROJECT_SOURCE}}", project_source)
    content = content.replace("{{COMMIT_REF}}", commit_ref)
    content = content.replace("{{WORKFLOW_NAME}}", workflow_name.upper())
    content = content.replace("{{TIMESTAMP}}", timestamp)
    content = content.replace("{{OPERATOR}}", "Clean Room QA Runner (Automated Agent)")
    content = content.replace("{{STATUS_BADGE}}", status_badge)
    content = content.replace("{{OVERALL_STATUS}}", overall_status)
    content = content.replace("{{EXECUTIVE_VERDICT}}", f"Workflow `{workflow_name}` finished with status {overall_status}.")
    content = content.replace("{{TOTAL_STEPS}}", str(total_steps))
    content = content.replace("{{PASSED_STEPS}}", str(passed_steps))
    content = content.replace("{{FAILED_STEPS}}", str(failed_steps))
    content = content.replace("{{TOTAL_DURATION}}", str(total_duration))
    content = content.replace("{{EXECUTIVE_NOTES}}", "Automated clean-room verification completed.")
    content = content.replace("{{DISCOVERED_DOCS}}", docs_formatted)
    content = content.replace("{{DETECTED_FRAMEWORK}}", ", ".join(discovery_data.get("detected_frameworks", ["Unknown"])))
    content = content.replace("{{RECOMMENDED_COMMANDS}}", recs_formatted)
    content = content.replace("{{STEP_TABLE_ROWS}}", "\n".join(table_rows))
    content = content.replace("{{STEP_DETAILS}}", "\n\n".join(step_details))
    content = content.replace("{{DEFECT_ANALYSIS}}", defect_analysis)
    content = content.replace("{{HANDOFF_STATUS}}", handoff_status)

    reports_dir.mkdir(parents=True, exist_ok=True)
    report_filename = f"{time_slug}_{workflow_name.lower()}_{overall_status.lower()}.md"
    report_file = reports_dir / report_filename
    report_file.write_text(content, encoding="utf-8")

    print(f"\n[✓] Report generated: {report_file}")
    return report_file


def main():
    parser = argparse.ArgumentParser(description="Clean Room QA Runner CLI")
    subparsers = parser.add_subparsers(dest="action", help="Available subcommands")

    # setup-cleanroom
    p_setup = subparsers.add_parser("setup-cleanroom", help="Set up clean room target repository")
    p_setup.add_argument("--source", "-s", required=True, help="Git URL or local project path")
    p_setup.add_argument("--branch", "-b", help="Branch name (if git)")
    p_setup.add_argument("--target", "-t", default=str(DEFAULT_TARGET), help="Target clean directory")

    # discover
    p_disc = subparsers.add_parser("discover", help="Scan target repository for test instructions")
    p_disc.add_argument("--target", "-t", default=str(DEFAULT_TARGET), help="Target clean directory")
    p_disc.add_argument("--json", action="store_true", help="Output JSON")

    # exec
    p_exec = subparsers.add_parser("exec", help="Run command in clean room environment")
    p_exec.add_argument("--cmd", "-c", required=True, help="Command to execute")
    p_exec.add_argument("--target", "-t", default=str(DEFAULT_TARGET), help="Target clean directory")
    p_exec.add_argument("--timeout", type=int, default=180, help="Timeout in seconds")

    # report
    p_rep = subparsers.add_parser("report", help="Generate standardized Markdown test report")
    p_rep.add_argument("--workflow", "-w", required=True, help="Workflow name (e.g. smoke, unit, integration)")
    p_rep.add_argument("--status", choices=["PASS", "FAIL"], default="PASS", help="Overall status")
    p_rep.add_argument("--target", "-t", default=str(DEFAULT_TARGET), help="Target clean directory")
    p_rep.add_argument("--source", "-s", help="Source repository/path name")
    p_rep.add_argument("--notes", default="Verification completed.", help="Executive summary notes")
    p_rep.add_argument("--results-json", help="Path to JSON file containing step results")

    args = parser.parse_args()

    if not args.action:
        parser.print_help()
        sys.exit(0)

    if args.action == "setup-cleanroom":
        ok = setup_cleanroom(source=args.source, target=Path(args.target), branch=args.branch)
        sys.exit(0 if ok else 1)

    elif args.action == "discover":
        disc = test_discovery.discover_project_tests(args.target)
        if args.json:
            import json
            print(json.dumps(disc, indent=2))
        else:
            print(f"=== Clean Room Test Discovery ===")
            print(f"Target: {disc.get('target_dir')}")
            print(f"Frameworks: {', '.join(disc.get('detected_frameworks', []))}")
            print(f"Documentation: {', '.join(disc.get('docs_found', [])) or 'None'}")
            rec = disc.get("recommended_commands", {})
            for k, v in rec.items():
                if v and k != "all":
                    print(f"  {k.capitalize()}: {v}")

    elif args.action == "exec":
        res = execute_step(args.cmd, cwd=Path(args.target), timeout=args.timeout)
        sys.exit(res["exit_code"] if res["exit_code"] >= 0 else 1)

    elif args.action == "report":
        target_path = Path(args.target)
        disc = test_discovery.discover_project_tests(target_path)
        steps = []
        if args.results_json:
            try:
                with open(args.results_json, "r", encoding="utf-8") as f:
                    steps = json.load(f)
            except Exception as e:
                print(f"[!] Failed to load results JSON: {e}", file=sys.stderr)
        if not steps:
            steps = [{
                "command": f"Workflow {args.workflow}",
                "exit_code": 0 if args.status == "PASS" else 1,
                "status": args.status,
                "duration": 0.1,
                "stdout": args.notes,
                "stderr": ""
            }]
        rep_file = generate_report(
            workflow_name=args.workflow,
            project_name=args.source or target_path.name,
            project_source=args.source or str(target_path),
            target_dir=target_path,
            steps=steps,
            discovery_data=disc
        )
        print(f"[✓] Report created: {rep_file}")
        sys.exit(0)


if __name__ == "__main__":
    main()
