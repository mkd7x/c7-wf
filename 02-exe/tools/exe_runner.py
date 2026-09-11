#!/usr/bin/env python3
"""
Main CLI Orchestration Hub for 02-exe.
Coordinates intake from 01-plan, environment configuration, dev server supervision,
fast inner-loop test execution, atomic git commits, and handoff to 03-qa.

@implements REQ-DEV-01
@implements REQ-DEV-03
@implements REQ-WORK-02
@implements REQ-HAND-01
@implements REQ-HAND-02
"""

import os
import sys
import re
import json
import time
import shutil
import subprocess
import argparse
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

try:
    from tools import audit_logger, env_manager, dev_discovery, process_manager
except ImportError:
    import audit_logger
    import env_manager
    import dev_discovery
    import process_manager

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent / "workspace"
RUNS_DIR = Path(__file__).resolve().parent.parent / "runs" / "latest"


def find_git_repo_root(start: Path) -> Optional[Path]:
    """Walk up from *start* to locate the enclosing git repository root.

    Uses `git rev-parse --show-toplevel` first, falling back to a manual
    `.git` ancestor scan so workspaces nested several levels deep
    (e.g. `02-exe/workspace` inside `c7-wf/`) are detected.
    """
    candidate = start.resolve()
    search_from = candidate if candidate.is_dir() else candidate.parent
    if shutil.which("git"):
        try:
            res = subprocess.run(
                ["git", "rev-parse", "--show-toplevel"],
                cwd=search_from,
                capture_output=True,
                text=True,
            )
            if res.returncode == 0 and res.stdout.strip():
                return Path(res.stdout.strip())
        except Exception:
            pass
    for parent in [search_from, *search_from.parents]:
        if (parent / ".git").exists():
            return parent
    return None


def _parse_plan_tasks(content: str) -> List[Dict[str, Any]]:
    """Extract task DAG entries from 01-plan markdown.

    Parses `### [TASK-ID] Title` blocks with `- Wave:` and
    `- Dependencies:` metadata (the format emitted by 01-plan).
    """
    tasks: List[Dict[str, Any]] = []
    header_re = re.compile(r"^###\s+\[([A-Za-z0-9_-]+)\]\s+(.+)$", re.MULTILINE)
    matches = list(header_re.finditer(content))
    for i, match in enumerate(matches):
        task_id = match.group(1).strip()
        title = match.group(2).strip()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(content)
        block = content[match.end():end]

        deps: List[str] = []
        dep_match = re.search(
            r"-\s*(?:\*\*)?(?:Dependencies|depends_on)(?:\*\*)?:\s*`?\[(.*?)\]`?",
            block,
            re.IGNORECASE,
        )
        if dep_match and dep_match.group(1).strip():
            deps = [d.strip().strip("'\"") for d in dep_match.group(1).split(",") if d.strip()]

        wave: Optional[int] = None
        wave_match = re.search(r"-\s*(?:\*\*)?Wave(?:\*\*)?:\s*(\d+)", block, re.IGNORECASE)
        if wave_match:
            try:
                wave = int(wave_match.group(1))
            except ValueError:
                pass

        tasks.append({"id": task_id, "title": title, "wave": wave, "dependencies": deps})
    return tasks


def _group_tasks_into_waves(tasks: List[Dict[str, Any]]) -> List[List[str]]:
    """Group parsed tasks into ordered execution waves by wave number.

    Tasks without an explicit wave join the last wave (or form wave 1).
    """
    numbered = [t for t in tasks if isinstance(t.get("wave"), int)]
    unnumbered = [t for t in tasks if not isinstance(t.get("wave"), int)]
    waves: List[List[str]] = []
    for w in sorted({t["wave"] for t in numbered}):
        waves.append([t["id"] for t in numbered if t["wave"] == w])
    if unnumbered:
        if waves:
            waves[-1].extend(t["id"] for t in unnumbered)
        else:
            waves.append([t["id"] for t in unnumbered])
    return waves


def intake_plan_from_01_plan(plan_file: Optional[Path] = None, ticket: Optional[str] = None) -> Dict[str, Any]:
    """
    Intake active plan from 01-plan or direct file.
    @implements REQ-DEV-01
    """
    if plan_file and plan_file.exists():
        content = plan_file.read_text(encoding="utf-8")
        # Extract title and branch (supports both 01-plan header formats)
        branch_match = re.search(r"\|\s*\*\*Target Branch\*\*\s*\|\s*`?([^`|\n]+)`?\s*\|", content)
        if not branch_match:
            branch_match = re.search(r"Branch:\s*`([^`]+)`", content)
        target_branch = branch_match.group(1).strip() if branch_match else "main"

        commit_match = re.search(r"\|\s*\*\*Git Commit SHA\*\*\s*\|\s*`?([A-Za-z0-9_-]+)`?\s*\|", content)
        tasks = _parse_plan_tasks(content)
        waves = _group_tasks_into_waves(tasks)
        return {
            "source": "file",
            "plan_file": str(plan_file),
            "target_branch": target_branch,
            "commit_sha": commit_match.group(1).strip() if commit_match else None,
            "task_count": len(tasks),
            "waves_count": len(waves),
            "tasks": tasks,
            "waves": waves,
            "raw_content": content[:1000]
        }

    plan_runner_script = Path(__file__).resolve().parent.parent.parent / "01-plan" / "tools" / "plan_runner.py"
    if plan_runner_script.exists():
        cmd = [sys.executable, str(plan_runner_script), "get-latest-plan", "--json"]
        if ticket:
            cmd.extend(["--ticket", ticket])
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, check=True)
            data = json.loads(res.stdout)
            RUNS_DIR.mkdir(parents=True, exist_ok=True)
            (RUNS_DIR / "intake_plan.json").write_text(json.dumps(data, indent=2), encoding="utf-8")
            return data
        except subprocess.CalledProcessError as e:
            # 01-plan exits 2 for PLAN_NOT_READY / NO_PLANS_FOUND /
            # TICKET_NOT_FOUND, but still prints the machine-readable
            # payload to stdout and the blocking reasons to stderr.
            # Preserve both instead of collapsing to the exit status.
            if e.stdout:
                try:
                    failure_payload = json.loads(e.stdout)
                except (json.JSONDecodeError, ValueError):
                    failure_payload = None
                if isinstance(failure_payload, dict):
                    result = dict(failure_payload)
                    details = [ln.strip() for ln in (e.stderr or "").splitlines() if ln.strip()]
                    if details:
                        result.setdefault("diagnostics", details)
                    return result
            return {
                "error": f"01-plan exited with status {e.returncode}: {(e.stderr or '').strip()[:2000]}",
            }
        except Exception as e:
            return {"error": f"Failed to query 01-plan: {e}"}

    return {"error": "No plan file provided and 01-plan not accessible"}


def run_setup_env(
    config: Optional[str] = None,
    template: str = ".env.example",
    output: str = ".env",
    workspace: str = "workspace",
) -> Tuple[bool, str]:
    """Resolve credentials from a JSON config and synthesize the .env file.

    Extracted from the `setup-env` CLI action for testability.
    @implements REQ-DEV-01
    """
    ws = Path(workspace).resolve()
    template_arg = Path(template)
    output_arg = Path(output)
    template_path = template_arg if template_arg.is_absolute() else ws / template_arg
    output_path = output_arg if output_arg.is_absolute() else ws / output_arg

    secrets_cfg: List[Dict[str, Any]] = []
    static_vars: Dict[str, str] = {}
    if config and Path(config).exists():
        data = json.loads(Path(config).read_text(encoding="utf-8"))
        secrets_cfg = data.get("secrets", [])
        static_vars = data.get("variables", {})

    resolved = env_manager.resolve_credentials(secrets_cfg)
    return env_manager.synthesize_env_file(
        template_path=template_path,
        output_path=output_path,
        resolved_secrets=resolved,
        static_vars=static_vars,
        workspace_dir=ws
    )


def lint_workflow_runbook(workflow_file: Path, strict: bool = False) -> Tuple[bool, List[str], List[str]]:
    """
    Validate workflow markdown runbook frontmatter and structure.
    @implements REQ-WORK-02
    """
    errors = []
    warnings = []

    if not workflow_file.exists():
        return False, [f"Workflow file does not exist: {workflow_file}"], []

    required_fields = ["id:", "name:", "target:"]
    recommended_fields = ["prerequisites:", "timeout_seconds:", "environment:"]

    content = workflow_file.read_text(encoding="utf-8")

    # Check YAML frontmatter
    fm_match = re.search(r"^---\n(.*?)\n---", content, re.DOTALL)
    if not fm_match:
        errors.append("Missing YAML frontmatter block (--- ... ---) at start of file")
    else:
        fm_text = fm_match.group(1)
        for req_field in required_fields:
            if req_field not in fm_text:
                errors.append(f"Frontmatter missing required field '{req_field}'")
        for rec_field in recommended_fields:
            if rec_field not in fm_text:
                warnings.append(f"Frontmatter missing recommended field '{rec_field}'")

    # Check for teardown trap
    if "trap " not in content:
        warnings.append("Workflow does not appear to contain a process teardown trap ('trap ...')")

    # Check for step headings. Accept both "### Step N:" (canonical) and
    # "## Step N:" (used by the bundled WORKFLOW_TEMPLATE); the latter is a
    # style warning, not an error, so our own template lints clean.
    steps = re.findall(r"^###\s+Step\s+\d+:", content, re.MULTILINE)
    legacy_steps = re.findall(r"^##\s+Step\s+\d+:", content, re.MULTILINE)
    if not steps and not legacy_steps:
        warnings.append("No '### Step N:' headings found in workflow")
    elif legacy_steps and not steps:
        warnings.append("Workflow uses '## Step N:' headings; prefer '### Step N:'")

    is_valid = len(errors) == 0
    if strict and warnings:
        is_valid = False
        errors.extend(warnings)

    return is_valid, errors, warnings


def execute_test_loop(
    cmd: Optional[str] = None,
    task_id: Optional[str] = None,
    cwd: Optional[Path] = None,
    step_id: Optional[str] = None
) -> Tuple[bool, Dict[str, Any]]:
    """
    Execute fast verification check and record in live audit log.
    @implements REQ-DEV-03
    """
    work_dir = cwd or WORKSPACE_ROOT
    command_to_run = cmd

    # Auto-detect if no cmd passed
    if not command_to_run:
        disc = dev_discovery.discover_fast_test_and_lint(work_dir)
        candidates = disc["linters"] + disc["typecheckers"] + disc["fast_test_commands"]
        command_to_run = " && ".join(candidates[:2]) if candidates else "echo 'No fast tests configured'"

    start_time = time.time()
    res = subprocess.run(
        command_to_run,
        shell=True,
        cwd=work_dir,
        capture_output=True,
        text=True
    )
    duration_ms = round((time.time() - start_time) * 1000, 2)
    success = (res.returncode == 0)

    step_name = step_id or f"test-loop-{task_id or 'adhoc'}"
    audit_record = audit_logger.record_step(
        tool="test_loop",
        step_id=step_name,
        input_data={"command": command_to_run, "task_id": task_id, "cwd": str(work_dir)},
        output_data={"stdout": res.stdout[:2000], "stderr": res.stderr[:2000], "exit_code": res.returncode},
        assertions={"exit_code_zero": success},
        duration_ms=duration_ms,
        status="PASS" if success else "FAIL"
    )

    return success, audit_record


def execute_commit(
    task_id: str,
    message: str,
    cwd: Optional[Path] = None
) -> Tuple[bool, str]:
    """
    Stage all modified files and commit with a task-referenced message.
    @implements REQ-HAND-01
    """
    work_dir = cwd or WORKSPACE_ROOT
    if not work_dir.exists():
        return False, f"Workspace path does not exist: {work_dir}"
    if not work_dir.is_dir():
        return False, f"Workspace path is not a directory: {work_dir}"
    repo_root = find_git_repo_root(work_dir)
    if repo_root is None:
        return False, "Target workspace is not inside a git repository"

    # Format commit message
    formatted_msg = f"feat({task_id}): {message.strip()}"

    try:
        subprocess.run(["git", "add", "-A"], cwd=work_dir, check=True)
        # Check diff
        diff_res = subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=work_dir)
        if diff_res.returncode == 0:
            return True, "No changes to commit."

        res = subprocess.run(["git", "commit", "-m", formatted_msg], cwd=work_dir, capture_output=True, text=True, check=True)
        sha_res = subprocess.run(["git", "rev-parse", "HEAD"], cwd=work_dir, capture_output=True, text=True, check=True)
        commit_sha = sha_res.stdout.strip()
        return True, f"Committed {commit_sha[:8]}: {formatted_msg}"
    except subprocess.CalledProcessError as e:
        return False, f"Git commit failed: {e}"


def generate_qa_handoff(
    branch: Optional[str] = None,
    commit_sha: Optional[str] = None,
    notes: str = "Development implementation verified.",
    cwd: Optional[Path] = None
) -> Dict[str, Any]:
    """
    Package execution handoff manifest for 03-qa.
    @implements REQ-HAND-02
    """
    work_dir = cwd or WORKSPACE_ROOT
    resolved_sha = commit_sha
    resolved_branch = branch

    if not resolved_sha and shutil.which("git"):
        try:
            res = subprocess.run(["git", "rev-parse", "HEAD"], cwd=work_dir, capture_output=True, text=True)
            if res.returncode == 0:
                resolved_sha = res.stdout.strip()
        except Exception:
            resolved_sha = "unknown"

    if not resolved_branch and shutil.which("git"):
        try:
            res = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=work_dir, capture_output=True, text=True)
            if res.returncode == 0:
                resolved_branch = res.stdout.strip()
        except Exception:
            resolved_branch = "feature-dev"

    audit_records = audit_logger.read_audit_log()
    passed_steps = sum(1 for r in audit_records if r.get("status") == "PASS")
    failed_steps = sum(1 for r in audit_records if r.get("status") == "FAIL")

    # Derive touched files from git status when inside a repo so the 03-qa
    # cleanroom manifest names the scope of the change set.
    # Fall back to the latest commit's file list: per SOP, handoff runs
    # after commit (Step 7 -> Step 8), when the working tree is clean and
    # `git status --porcelain` is empty.
    touched_files: List[str] = []
    repo_root_for_diff = find_git_repo_root(work_dir)
    if repo_root_for_diff is not None:
        try:
            status_res = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=work_dir,
                capture_output=True,
                text=True,
            )
            if status_res.returncode == 0:
                for line in status_res.stdout.splitlines():
                    name = line[3:].strip().strip('"')
                    if name:
                        touched_files.append(name)
        except Exception:
            pass
        if not touched_files:
            # Scope to the handoff's commit when known; otherwise HEAD.
            target_rev = resolved_sha if resolved_sha and resolved_sha != "unknown" else "HEAD"
            try:
                diff_res = subprocess.run(
                    ["git", "diff-tree", "--no-commit-id", "--name-only", "-r", target_rev],
                    cwd=work_dir,
                    capture_output=True,
                    text=True,
                )
                if diff_res.returncode == 0:
                    for line in diff_res.stdout.splitlines():
                        name = line.strip()
                        if name:
                            touched_files.append(name)
            except Exception:
                pass

    if not audit_records:
        status = "NOT_VERIFIED"
    elif failed_steps > 0:
        status = "FAILURES_PRESENT"
    elif passed_steps > 0:
        status = "READY_FOR_QA"
    else:
        # Records exist but none passed (e.g. only SKIPPED/INFO):
        # nothing verified the change, so do not promote to READY_FOR_QA.
        status = "NOT_VERIFIED"

    manifest = {
        "handoff_timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "status": status,
        "commit_sha": resolved_sha or "unknown",
        "target_branch": resolved_branch or "main",
        "touched_files": touched_files,
        "audit_summary": {
            "total_steps": len(audit_records),
            "passed": passed_steps,
            "failed": failed_steps
        },
        "notes": notes,
        "qa_instructions": (
            f"Run 'python3 03-qa/tools/qa_runner.py setup-cleanroom"
            f" --source {resolved_sha or resolved_branch or 'main'}'"
        )
    }

    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    manifest_path = RUNS_DIR / "handoff_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    return manifest


def main():
    parser = argparse.ArgumentParser(description="02-exe Execution Runner")
    subparsers = parser.add_subparsers(dest="action", required=True)

    # intake
    intake_p = subparsers.add_parser("intake", help="Intake active plan from 01-plan")
    intake_p.add_argument("--plan-file", help="Path to local plan file")
    intake_p.add_argument("--ticket", help="Jira ticket ID")

    # setup-env
    setup_env_p = subparsers.add_parser("setup-env", help="Run credential fetch and env synthesis")
    setup_env_p.add_argument("--config", help="Env configuration JSON file")
    setup_env_p.add_argument("--template", default=".env.example", help="Template file name/path")
    setup_env_p.add_argument("--output", default=".env", help="Output file name/path")
    setup_env_p.add_argument("--workspace", default="workspace", help="Workspace path")
    setup_env_p.add_argument("--no-strict-gitignore", action="store_true", help="Skip gitignore check")

    # discover
    disc_p = subparsers.add_parser("discover", help="Discover repo dev tooling and scripts")
    disc_p.add_argument("--source", default="workspace", help="Target source path")
    disc_p.add_argument("--json", action="store_true", help="Output raw JSON")

    # start-dev
    start_dev_p = subparsers.add_parser("start-dev", help="Start background dev server")
    start_dev_p.add_argument("--cmd", required=True, help="Dev server startup command")
    start_dev_p.add_argument("--name", default="dev-server", help="Service name")
    start_dev_p.add_argument("--wait-url", help="HTTP readiness URL to poll")
    start_dev_p.add_argument("--wait-tcp", type=int, help="TCP port to poll")
    start_dev_p.add_argument("--timeout", type=float, default=30.0, help="Readiness timeout")

    # stop-dev
    stop_dev_p = subparsers.add_parser("stop-dev", help="Stop background dev server")
    stop_dev_p.add_argument("--name", default="dev-server", help="Service name")

    # test-loop
    test_loop_p = subparsers.add_parser("test-loop", help="Execute fast inner-loop verification")
    test_loop_p.add_argument("--cmd", help="Fast test/lint command to run")
    test_loop_p.add_argument("--task-id", help="Plan task ID being verified")
    test_loop_p.add_argument("--step-id", help="Audit step identifier")

    # lint-workflow
    lint_p = subparsers.add_parser("lint-workflow", help="Lint workflow runbook")
    lint_p.add_argument("--file", required=True, help="Workflow markdown path")
    lint_p.add_argument("--strict", action="store_true", help="Treat warnings as errors")

    # commit
    commit_p = subparsers.add_parser("commit", help="Commit task changes cleanly")
    commit_p.add_argument("--task-id", required=True, help="Associated plan task ID")
    commit_p.add_argument("--message", required=True, help="Commit message")

    # handoff
    handoff_p = subparsers.add_parser("handoff", help="Package handoff manifest for 03-qa")
    handoff_p.add_argument("--branch", help="Target git branch")
    handoff_p.add_argument("--commit", help="Git commit SHA")
    handoff_p.add_argument("--notes", default="Development verified.", help="Handoff notes")

    # clear-audit
    clear_p = subparsers.add_parser("clear-audit", help="Clear audit trail")

    args = parser.parse_args()

    if args.action == "intake":
        plan_p = Path(args.plan_file) if args.plan_file else None
        res = intake_plan_from_01_plan(plan_p, args.ticket)
        print(json.dumps(res, indent=2))

    elif args.action == "setup-env":
        try:
            ok, msg = run_setup_env(
                config=args.config,
                template=args.template,
                output=args.output,
                workspace=args.workspace,
            )
        except Exception as e:
            print(f"[!] Failed to parse config {args.config}: {e}", file=sys.stderr)
            sys.exit(1)
        print(f"[{'✓' if ok else '!'}] {msg}")
        sys.exit(0 if ok else 1)

    elif args.action == "discover":
        src = Path(args.source).resolve()
        res = dev_discovery.run_discovery(src)
        if args.json:
            print(json.dumps(res, indent=2))
        else:
            print(f"[✓] Discovery complete for {src.name}: {res['runtime']['runtime']}")

    elif args.action == "start-dev":
        res = process_manager.start_background_process(args.cmd, name=args.name, cwd=WORKSPACE_ROOT)
        print(f"[✓] Dev service '{args.name}' started (PID {res['pid']})")
        if args.wait_url:
            print(f"[*] Waiting for {args.wait_url}...")
            ok = process_manager.poll_http_url(args.wait_url, timeout_seconds=args.timeout)
            if ok:
                print("[✓] Dev server is READY.")
            else:
                print("[!] Readiness check timed out!", file=sys.stderr)
                sys.exit(1)
        elif args.wait_tcp:
            print(f"[*] Waiting for port {args.wait_tcp}...")
            start = time.time()
            ok = False
            while time.time() - start < args.timeout:
                if process_manager.is_port_open("127.0.0.1", args.wait_tcp):
                    ok = True
                    break
                time.sleep(0.5)
            if ok:
                print(f"[✓] Port {args.wait_tcp} is OPEN.")
            else:
                print(f"[!] TCP check timed out!", file=sys.stderr)
                sys.exit(1)

    elif args.action == "stop-dev":
        ok = process_manager.stop_process(args.name)
        print(f"[{'✓' if ok else '*'}] Stopped '{args.name}'.")

    elif args.action == "test-loop":
        ok, rec = execute_test_loop(cmd=args.cmd, task_id=args.task_id, step_id=args.step_id)
        if ok:
            print(f"[✓] Fast test loop PASSED ({rec['duration_ms']}ms)")
            sys.exit(0)
        else:
            print(f"[!] Fast test loop FAILED ({rec['duration_ms']}ms)", file=sys.stderr)
            sys.exit(1)

    elif args.action == "lint-workflow":
        ok, errs, warns = lint_workflow_runbook(Path(args.file), strict=args.strict)
        for w in warns:
            print(f"[WARN] {w}")
        if ok:
            print(f"[✓] Workflow runbook is VALID: {args.file}")
            sys.exit(0)
        else:
            print(f"[!] Workflow validation FAILED:", file=sys.stderr)
            for err in errs:
                print(f"    - {err}", file=sys.stderr)
            sys.exit(1)

    elif args.action == "commit":
        ok, msg = execute_commit(task_id=args.task_id, message=args.message)
        if ok:
            print(f"[✓] {msg}")
            sys.exit(0)
        else:
            print(f"[!] {msg}", file=sys.stderr)
            sys.exit(1)

    elif args.action == "handoff":
        manifest = generate_qa_handoff(branch=args.branch, commit_sha=args.commit, notes=args.notes)
        print(f"[✓] Handoff manifest generated: {RUNS_DIR / 'handoff_manifest.json'}")
        print(f"    Status:     {manifest['status']}")
        print(f"    Branch:     {manifest['target_branch']}")
        print(f"    Commit SHA: {manifest['commit_sha']}")

    elif args.action == "clear-audit":
        audit_logger.clear_audit()
        print("[✓] Audit log reset.")


if __name__ == "__main__":
    main()
