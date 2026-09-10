#!/usr/bin/env python3
"""
Clean Room QA Runner CLI.
Provides full lifecycle management for clean room testing:
- Workspace setup and target repo isolation
- Automated test discovery
- Test step execution with timeout and log capture
- Live audit log inspection and step output retrieval
- Workflow markdown runbook linter
- Standardized QA report generation for 04-review handoff
"""

import os
import re
import signal
import sys
import json
import shutil
import subprocess
import argparse
import tempfile
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

# Import discovery & audit engines
SCRIPT_DIR = Path(__file__).resolve().parent
BASE_DIR = SCRIPT_DIR.parent
DEFAULT_TARGET = BASE_DIR / "target-repo"
DEFAULT_REPORTS = BASE_DIR / "reports"
DEFAULT_TEMPLATE = BASE_DIR / "templates" / "REPORT_TEMPLATE.md"

sys.path.insert(0, str(SCRIPT_DIR))
import test_discovery
import audit_logger


GITKEEP_CONTENT = "# Keep target-repo directory structure tracked in git\n"
MAX_AUDIT_OUTPUT_CHARS = 4000


def _kill_process_tree(proc: "subprocess.Popen") -> None:
    """Terminate a spawned process group; best-effort on Windows."""
    try:
        if os.name == "posix":
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        else:
            proc.kill()
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass


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

    if preserve_gitkeep:
        gitkeep = target_path / ".gitkeep"
        if not gitkeep.exists() or not gitkeep.read_text(encoding="utf-8", errors="replace"):
            gitkeep.write_text(GITKEEP_CONTENT, encoding="utf-8")


def _materialize_cleanroom(source_path: Path, staging: Path) -> None:
    """Copy a local source tree into a staging directory, excluding caches."""
    for item in source_path.iterdir():
        if item.name in [".git", "node_modules", ".venv", "__pycache__", "target-repo"]:
            continue
        dest = staging / item.name
        if item.is_dir():
            if item.is_symlink():
                continue
            shutil.copytree(item, dest, dirs_exist_ok=True)
        else:
            shutil.copy2(item, dest)


def _swap_into_target(staging: Path, target: Path, preserve_gitkeep: bool = True) -> None:
    """Atomically replace target contents with a verified staging directory."""
    if not staging.exists():
        raise RuntimeError(f"Staging directory {staging} does not exist.")
    if target.exists():
        backup = target.parent / f"{target.name}.bak.{os.getpid()}"
        if backup.exists():
            shutil.rmtree(backup)
        os.replace(target, backup)
        try:
            os.replace(staging, target)
        except Exception:
            # Best-effort rollback; the backup keeps the previous sandbox.
            if target.exists():
                shutil.rmtree(target, ignore_errors=True)
            os.replace(backup, target)
            raise
        shutil.rmtree(backup, ignore_errors=True)
    else:
        os.replace(staging, target)
    if preserve_gitkeep:
        gitkeep = target / ".gitkeep"
        if not gitkeep.exists() or not gitkeep.read_text(encoding="utf-8", errors="replace"):
            gitkeep.write_text(GITKEEP_CONTENT, encoding="utf-8")


def setup_cleanroom(source: str, target: Path = DEFAULT_TARGET, branch: Optional[str] = None) -> bool:
    """
    Clone or copy source into clean target directory.
    @implements REQ-ISO-02
    """
    print(f"[*] Setting up clean-room in: {target}")

    source_path = Path(source).expanduser().resolve() if Path(source).expanduser().exists() else None

    if source_path and source_path.is_dir():
        print(f"[*] Copying from local source: {source_path}")
        staging = target.parent / f"{target.name}.staging.{os.getpid()}"
        if staging.exists():
            shutil.rmtree(staging)
        staging.mkdir(parents=True, exist_ok=True)
        try:
            _materialize_cleanroom(source_path, staging)
            _swap_into_target(staging, target, preserve_gitkeep=True)
        finally:
            shutil.rmtree(staging, ignore_errors=True)
        return True
    else:
        print(f"[*] Cloning remote git repository: {source}")
        # Clone to a staging directory first so a failed clone never wipes
        # the existing sandbox (QAF-014).
        staging = target.parent / f"{target.name}.staging.{os.getpid()}"
        if staging.exists():
            shutil.rmtree(staging)
        cmd = ["git", "clone", "--depth", "1"]
        if branch:
            cmd.extend(["--branch", branch])
        cmd.extend([source, str(staging)])
        try:
            subprocess.run(cmd, capture_output=True, text=True, check=True)
            print("[✓] Git clone successful.")
            _swap_into_target(staging, target, preserve_gitkeep=True)
            return True
        except subprocess.CalledProcessError as e:
            print(f"[!] Git clone failed: {e.stderr}")
            shutil.rmtree(staging, ignore_errors=True)
            return False


def execute_step(cmd: str, cwd: Path, timeout: int = 180, detach_background: bool = True,
                 step_id: Optional[str] = None, audit_file: Optional[str] = None) -> Dict[str, Any]:
    """
    Execute a single test command inside cwd, capturing timing, output, and exit code.
    @implements REQ-ISO-04
    @implements REQ-WORK-05
    @implements REQ-REP-02
    """
    start_time = time.time()
    print(f"\n[>] Executing: {cmd}")
    print(f"    Directory: {cwd}")

    display_cmd = cmd
    backgrounded = detach_background and cmd.rstrip().endswith("&")
    if backgrounded:
        print("[*] Backgrounded command detected: detaching with output to a log file.")
        print("    Hint: prefer an explicit redirect, e.g. '> /tmp/<svc>.log 2>&1 &'.")

    proc = None
    try:
        if os.name == "posix":
            if backgrounded:
                # Detach fully: new session + /dev/null stdio so the child
                # can never hold our pipes open. The direct shell exits at
                # once; we reap it and report the launch as PASS/FAIL.
                # Output capture is impossible for a detached process by
                # design — redirect to a log file when output is needed.
                bg = subprocess.run(
                    cmd,
                    cwd=cwd,
                    shell=True,
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=timeout,
                    start_new_session=True,
                )
                duration = round(time.time() - start_time, 2)
                res = {
                    "command": display_cmd,
                    "exit_code": bg.returncode,
                    "status": "PASS" if bg.returncode == 0 else "FAIL",
                    "duration": duration,
                    "stdout": "",
                    "stderr": "",
                    "detached": True,
                }
                print(f"[{res['status']}] (Exit code: {bg.returncode}, Duration: {duration}s, detached)")
                _audit_exec(res, step_id, audit_file)
                return res
            proc = subprocess.Popen(
                cmd,
                cwd=cwd,
                shell=True,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                start_new_session=True,
            )
            try:
                out, err = proc.communicate(timeout=timeout)
                rc = proc.returncode
            except subprocess.TimeoutExpired:
                _kill_process_tree(proc)
                out, err = proc.communicate()
                raise subprocess.TimeoutExpired(cmd, timeout, output=out, stderr=err)
            return _finish_exec(cmd, start_time, rc, out, err, step_id, audit_file)
        proc = subprocess.run(
            cmd,
            cwd=cwd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        return _finish_exec(cmd, start_time, proc.returncode, proc.stdout, proc.stderr,
                            step_id, audit_file)
    except subprocess.TimeoutExpired as e:
        if proc is not None and isinstance(proc, subprocess.Popen):
            _kill_process_tree(proc)
        duration = round(time.time() - start_time, 2)
        print(f"[TIMEOUT] Command exceeded {timeout}s (process group terminated)")
        res = {
            "command": display_cmd,
            "exit_code": -1,
            "status": "TIMEOUT",
            "duration": duration,
            "stdout": _truncate_audit_text(e.stdout if isinstance(e.stdout, str) else (e.stdout or "")),
            "stderr": f"Command timed out after {timeout} seconds."
        }
        _audit_exec(res, step_id, audit_file)
        return res
    except Exception as e:
        duration = round(time.time() - start_time, 2)
        print(f"[ERROR] Execution failed: {e}")
        res = {
            "command": display_cmd,
            "exit_code": -1,
            "status": "ERROR",
            "duration": duration,
            "stdout": "",
            "stderr": str(e)
        }
        _audit_exec(res, step_id, audit_file)
        return res


def _finish_exec(cmd: str, start_time: float, returncode: int, stdout: str, stderr: str,
                 step_id: Optional[str], audit_file: Optional[str]) -> Dict[str, Any]:
    duration = round(time.time() - start_time, 2)
    status = "PASS" if returncode == 0 else "FAIL"
    print(f"[{status}] (Exit code: {returncode}, Duration: {duration}s)")
    res = {
        "command": cmd,
        "exit_code": returncode,
        "status": status,
        "duration": duration,
        "stdout": stdout,
        "stderr": stderr
    }
    _audit_exec(res, step_id, audit_file)
    return res


def _truncate_audit_text(text: Any, limit: int = MAX_AUDIT_OUTPUT_CHARS) -> str:
    if not isinstance(text, str):
        text = str(text) if text else ""
    if len(text) > limit:
        return text[:limit] + f"\n... [truncated {len(text) - limit} chars]"
    return text


def _audit_exec(res: Dict[str, Any], step_id: Optional[str], audit_file: Optional[str]) -> None:
    """Record an exec step so shell commands appear in audit-driven reports."""
    if not step_id:
        return
    duration_ms = round(res.get("duration", 0) * 1000, 2)
    failures = [] if res.get("status") == "PASS" else [
        f"Command exited {res.get('exit_code')} ({res.get('status')}): {res.get('command')}"
    ]
    audit_logger.record_step(
        tool="qa_runner_exec",
        step_id=step_id,
        input_data={"command": res.get("command")},
        output_data={
            "exit_code": res.get("exit_code"),
            "stdout": _truncate_audit_text(res.get("stdout", "")),
            "stderr": _truncate_audit_text(res.get("stderr", "")),
            "detached": res.get("detached", False),
        },
        assertions={"passed": not failures, "failures": failures},
        duration_ms=duration_ms,
        status=res.get("status", "FAIL"),
        custom_audit_path=audit_file,
    )


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


TOOL_FLAG_ALLOWLIST = {
    "send_http_req.py": {"--method", "-X", "--header", "-H", "--data", "-d",
                         "--data-file", "-f", "--timeout", "--expect-status", "-s",
                         "--expect-contains", "--expect-json", "--save",
                         "--step-id", "--audit-file", "--verbose", "-v",
                         "--no-redirect", "--insecure", "--ca-cert"},
    "run_sql_cmd.py": {"--driver", "--db", "-d", "--container", "-c", "--engine",
                       "--database", "--user", "-u", "--password", "-p",
                       "--query", "-q", "--file", "-f", "--format",
                       "--read-only", "--expect-count", "--step-id", "--audit-file"},
    "wait_for_service.py": {"--url", "-u", "--tcp", "-t", "--expect-status", "-s",
                            "--timeout", "--interval", "--step-id", "--audit-file",
                            "--insecure", "--ca-cert"},
    "query_blob_storage.py": {"--dir", "-d", "--prefix", "-p", "--json",
                              "--key", "-k", "--out", "-o", "--file", "-f",
                              "--step-id", "--audit-file"},
    "qa_runner.py": {"--source", "-s", "--branch", "-b", "--target", "-t",
                     "--json", "--cmd", "-c", "--timeout", "--step", "--query",
                     "-q", "--audit-file", "--file", "-f", "--workflow", "-w",
                     "--status", "--notes", "--results-json", "--use-audit",
                     "--no-use-audit", "--step-id", "--strict"},
}

LINT_FENCE_RE = re.compile(r"```(\w+)?[ \t]*\n(.*?)\n```", re.DOTALL)
LINT_SHELL_FENCES = {"", "bash", "sh", "shell", "console", "text", "plaintext"}


def _extract_shell_blocks(content: str) -> List[str]:
    """Return fenced code blocks that may contain shell/tool invocations.

    Only untagged or shell-ish fences are inspected; ```json/.yaml/etc.
    blocks (schemas, payloads) are ignored (QAF-018).
    """
    blocks = []
    for lang, body in LINT_FENCE_RE.findall(content):
        if (lang or "").lower() in LINT_SHELL_FENCES:
            blocks.append(body)
    return blocks


def _lint_tool_flags(block: str) -> List[str]:
    """Flag unknown CLI options on lines that actually invoke our tools.

    Flag matching is line-scoped (not block-scoped): a bare `--filter`
    belonging to `docker`/`dotnet` on another line must not be attributed
    to qa_runner.py just because the block mentions it elsewhere. Flags
    inside the quoted payload of `exec --cmd "..."` belong to the inner
    command, not to qa_runner.py.
    """
    problems = []
    for line in block.splitlines():
        for tool_name, allowed in TOOL_FLAG_ALLOWLIST.items():
            if tool_name not in line:
                continue
            invocation = line.split("#", 1)[0]
            if tool_name == "qa_runner.py" and "--cmd" in invocation:
                # Only flags before --cmd (plus --cmd's own value boundary)
                # belong to qa_runner; the quoted shell payload is opaque.
                invocation = invocation.split("--cmd", 1)[0]
            for flag in sorted(set(re.findall(r"--[a-zA-Z][\w-]*", invocation))):
                if flag not in allowed:
                    problems.append(f"Unknown flag '{flag}' for {tool_name}.")
    return problems


def lint_workflow(workflow_path: Path, strict: bool = False) -> Tuple[bool, List[str], List[str]]:
    """
    Inspect a workflow markdown runbook and return (is_valid, errors, warnings).
    Checks:
    - Frontmatter existence and required attributes
    - Validity of tool invocation commands in code blocks
    - Existence of teardown / cleanup instructions
    """
    errors = []
    warnings = []

    if not workflow_path.is_file():
        return False, [f"Workflow file does not exist: {workflow_path}"], []

    content = workflow_path.read_text(encoding="utf-8")

    # 1. Check Frontmatter
    structural: List[str] = []
    has_frontmatter = content.startswith("---")
    if not has_frontmatter:
        structural.append("Missing YAML frontmatter metadata (required: id, name; recommended: prerequisites, timeout).")
    else:
        parts = content.split("---", 2)
        if len(parts) >= 3:
            fm_text = parts[1]
            if "id:" not in fm_text:
                structural.append("Frontmatter missing 'id' attribute.")
            if "name:" not in fm_text:
                structural.append("Frontmatter missing 'name' attribute.")
        else:
            structural.append("Malformed YAML frontmatter block.")

    # 2. Check Tool references in fenced code blocks
    tool_scripts = {
        "send_http_req.py": SCRIPT_DIR / "send_http_req.py",
        "run_sql_cmd.py": SCRIPT_DIR / "run_sql_cmd.py",
        "wait_for_service.py": SCRIPT_DIR / "wait_for_service.py",
        "query_blob_storage.py": SCRIPT_DIR / "query_blob_storage.py",
        "qa_runner.py": SCRIPT_DIR / "qa_runner.py",
    }

    found_tool_calls = 0
    step_id_calls = 0

    code_blocks = _extract_shell_blocks(content)
    flag_problems: List[str] = []
    for block in code_blocks:
        flag_problems.extend(_lint_tool_flags(block))
        for tool_name, tool_file in tool_scripts.items():
            if tool_name in block:
                found_tool_calls += 1
                if not tool_file.exists():
                    errors.append(f"Referenced tool script does not exist: {tool_file}")
                if "--step-id" in block:
                    step_id_calls += 1
    errors.extend(flag_problems)

    if found_tool_calls > 0 and step_id_calls == 0:
        structural.append("No tools in workflow use '--step-id'. Adding '--step-id' enables live audit logging.")

    # 3. Check for Teardown / Cleanup
    if "teardown" not in content.lower() and "cleanup" not in content.lower():
        structural.append("Workflow lacks an explicit Teardown/Cleanup section or shell trap.")

    if strict:
        errors.extend(structural)
    else:
        warnings.extend(structural)

    is_valid = len(errors) == 0
    return is_valid, errors, warnings


def describe_step(s: Dict[str, Any]) -> str:
    """Render a human-readable one-line command/tool description (QAF-016)."""
    if s.get("command"):
        return str(s["command"])
    tool = s.get("tool", "tool")
    data = s.get("input", {}) or {}
    for key in ("command", "target", "url", "project", "dir", "database"):
        val = data.get(key)
        if val:
            extra = ""
            if data.get("method"):
                extra = f"{data['method']} "
            elif data.get("action"):
                extra = f"{data['action']} "
            return f"{tool} ({extra}{val})".strip()
    return tool


def render_output_snippet(value: Any, limit: int = 500) -> str:
    """Render truncated output, appending '...' only when truncated (QAF-016)."""
    text = value if isinstance(value, str) else json.dumps(value, indent=2)
    if len(text) > limit:
        return text[:limit] + "..."
    return text


def generate_report(
    workflow_name: str,
    project_name: str,
    project_source: str,
    target_dir: Path,
    steps: List[Dict[str, Any]],
    discovery_data: Dict[str, Any],
    reports_dir: Path = DEFAULT_REPORTS,
    template_path: Path = DEFAULT_TEMPLATE,
    caller_status: Optional[str] = None,
    executive_notes: str = "Automated clean-room verification completed."
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
    passed_steps = sum(1 for s in steps if s.get("status") == "PASS")
    failed_steps = sum(1 for s in steps if s.get("status") != "PASS")
    total_duration = round(sum(s.get("duration", s.get("duration_ms", 0) / 1000.0) for s in steps), 2)

    # QAF-001: the agent's explicit verdict is authoritative. An audit PASS
    # can never override --status FAIL (e.g. failures in unaudited exec
    # steps); disagreement is surfaced in the defect analysis.
    audit_status = "PASS" if (total_steps > 0 and failed_steps == 0) else "FAIL"
    if caller_status == "FAIL":
        overall_status = "FAIL"
    elif caller_status == "PASS" and audit_status == "FAIL":
        overall_status = "FAIL"
    elif total_steps == 0:
        overall_status = caller_status or "FAIL"
    else:
        overall_status = audit_status
    status_badge = "🟢 PASS" if overall_status == "PASS" else "🔴 FAIL"
    handoff_status = "READY FOR 04-REVIEW" if overall_status == "PASS" else "BLOCKED (QA Failed)"
    verdict_mismatch = caller_status is not None and caller_status != audit_status

    table_rows = []
    step_details = []
    for idx, s in enumerate(steps, 1):
        step_title = s.get("step_id", f"Step {idx}")
        cmd_desc = describe_step(s)
        duration = s.get("duration", round(s.get("duration_ms", 0) / 1000.0, 2))
        exit_c = s.get("exit_code", 0 if s.get("status") == "PASS" else 1)
        st = s.get("status", "PASS")

        table_rows.append(
            f"| {idx} | {step_title} | `{cmd_desc}` | {duration}s | {exit_c} | **{st}** |"
        )

        detail = [
            f"#### Step {idx}: `{step_title}`",
            f"- **Status**: {st}",
            f"- **Duration**: {duration}s",
            f"- **Command / Tool**: `{cmd_desc}`",
        ]
        if s.get("output"):
            detail.append(f"**Output**:\n```json\n{render_output_snippet(s['output'])}\n```")
        elif s.get("stdout"):
            detail.append(f"**Output (stdout)**:\n```\n{render_output_snippet(s['stdout'].strip())}\n```")

        if s.get("assertions", {}).get("failures"):
            detail.append(f"**Assertion Failures**:\n" + "\n".join(f"- {f}" for f in s["assertions"]["failures"]))
        elif s.get("stderr"):
            detail.append(f"**Error Output (stderr)**:\n```\n{s['stderr'].strip()}\n```")

        step_details.append("\n".join(detail))

    docs = discovery_data.get("docs_found", [])
    docs_formatted = "\n".join(f"- `{d}`" for d in docs) if docs else "- None found"

    rec = discovery_data.get("recommended_commands", {})
    recs_formatted = "\n".join(f"- **{k.capitalize()}**: `{v}`" for k, v in rec.items() if v and k != "all") or "- None"

    if overall_status == "FAIL":
        defects = []
        if verdict_mismatch:
            defects.append("### Verdict disagreement: agent reported "
                           f"`{caller_status}` but audit-derived status is `{audit_status}`")
            defects.append("Details: the explicit `--status` verdict is treated as authoritative; "
                           "unaudited steps (e.g. `exec` without `--step-id`) may explain the gap.")
        for idx, s in enumerate(steps, 1):
            if s.get("status") != "PASS":
                defects.append(f"### Failure in {s.get('step_id', f'Step {idx}')}")
                defects.append(f"Details: {s.get('assertions', {}).get('failures') or s.get('stderr') or s.get('stdout')}")
        defect_analysis = "\n\n".join(defects)
    else:
        defect_analysis = "No defects identified during this execution."

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
    content = content.replace("{{EXECUTIVE_NOTES}}", executive_notes)
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
    p_exec.add_argument("--step-id", help="Logical identifier for audit logging (enables report visibility)")
    p_exec.add_argument("--audit-file", help="Custom path to audit.jsonl log file")
    p_exec.add_argument("--no-detach", action="store_true",
                        help="Disable background-command detachment (legacy capture behavior)")

    # get-step-output
    p_step = subparsers.add_parser("get-step-output", help="Retrieve structured output for a specific step")
    p_step.add_argument("--step", "-s", required=True, help="Step identifier (e.g. step-05-create-list)")
    p_step.add_argument("--query", "-q", help="Dot-notation path to extract (e.g. output.body.id)")
    p_step.add_argument("--audit-file", help="Path to audit.jsonl")

    # view-audit
    p_audit = subparsers.add_parser("view-audit", help="View current run audit trail")
    p_audit.add_argument("--json", action="store_true", help="Output as JSON array")
    p_audit.add_argument("--audit-file", help="Path to audit.jsonl")

    # clear-audit
    p_clear = subparsers.add_parser("clear-audit", help="Reset current audit log and execution state")
    p_clear.add_argument("--audit-file", help="Path to audit.jsonl")

    # lint-workflow
    p_lint = subparsers.add_parser("lint-workflow", help="Validate a workflow markdown runbook")
    p_lint.add_argument("--file", "-f", required=True, help="Path to workflow markdown file")
    p_lint.add_argument("--strict", action="store_true",
                        help="Treat structural findings (frontmatter, --step-id, teardown) as errors")

    # report
    p_rep = subparsers.add_parser("report", help="Generate standardized Markdown test report")
    p_rep.add_argument("--workflow", "-w", required=True, help="Workflow name (e.g. smoke, unit, integration)")
    p_rep.add_argument("--status", choices=["PASS", "FAIL"], default="PASS", help="Overall status")
    p_rep.add_argument("--target", "-t", default=str(DEFAULT_TARGET), help="Target clean directory")
    p_rep.add_argument("--source", "-s", help="Source repository/path name")
    p_rep.add_argument("--notes", default="Verification completed.", help="Executive summary notes")
    p_rep.add_argument("--results-json", help="Path to JSON file containing step results")
    p_rep.add_argument("--use-audit", action="store_true", default=True, help="Compile report directly from audit log (default: True)")
    p_rep.add_argument("--no-use-audit", action="store_true", help="Ignore the audit log; use --results-json or --status only")
    p_rep.add_argument("--audit-file", help="Custom audit.jsonl to compile the report from")
    p_rep.add_argument("--fresh-run", action="store_true",
                       help="Archive any prior audit steps before compiling (per-run isolation)")

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
        res = execute_step(args.cmd, cwd=Path(args.target), timeout=args.timeout,
                           detach_background=not args.no_detach,
                           step_id=args.step_id, audit_file=args.audit_file)
        sys.exit(res["exit_code"] if res["exit_code"] >= 0 else 1)

    elif args.action == "get-step-output":
        record = audit_logger.get_step_output(args.step, custom_audit_path=args.audit_file)
        if not record:
            print(f"[!] Step '{args.step}' not found in audit log.", file=sys.stderr)
            sys.exit(1)
        if args.query:
            from send_http_req import resolve_json_path
            found, val = resolve_json_path(record, args.query)
            if not found:
                print(f"[!] Path '{args.query}' not found in step '{args.step}'.", file=sys.stderr)
                sys.exit(1)
            if isinstance(val, (dict, list)):
                print(json.dumps(val, indent=2))
            else:
                print(val)
        else:
            print(json.dumps(record, indent=2))
        sys.exit(0)

    elif args.action == "view-audit":
        records = audit_logger.read_audit_log(custom_audit_path=args.audit_file)
        if args.json:
            print(json.dumps(records, indent=2))
        else:
            print(f"=== Clean Room Live Audit Trail ({len(records)} steps) ===")
            if not records:
                print("  (No audit steps recorded)")
            for idx, r in enumerate(records, 1):
                status_icon = "✓" if r["status"] == "PASS" else "✗"
                print(f"  {idx}. [{status_icon}] {r.get('step_id', 'unknown'):<25} ({r.get('tool')}, {r.get('duration_ms')}ms)")
        sys.exit(0)

    elif args.action == "clear-audit":
        audit_logger.clear_audit(custom_audit_path=args.audit_file)
        print("[✓] Audit log and execution state cleared.")
        sys.exit(0)

    elif args.action == "lint-workflow":
        valid, errors, warnings = lint_workflow(Path(args.file), strict=args.strict)
        print(f"=== Workflow Linter: {args.file} ===")
        if valid and not warnings:
            print("[✓] Workflow is valid with zero warnings.")
            sys.exit(0)
        for err in errors:
            print(f"[!] ERROR: {err}", file=sys.stderr)
        for warn in warnings:
            print(f"[WARN] {warn}")
        sys.exit(0 if valid else 1)

    elif args.action == "report":
        if args.fresh_run and not args.audit_file and not args.results_json:
            audit_logger.start_new_run(reason=f"report:{args.workflow}")
        target_path = Path(args.target)
        disc = test_discovery.discover_project_tests(target_path)
        steps = []

        use_audit = args.use_audit and not args.no_use_audit
        if args.results_json:
            try:
                with open(args.results_json, "r", encoding="utf-8") as f:
                    steps = json.load(f)
            except Exception as e:
                print(f"[!] Failed to load results JSON: {e}", file=sys.stderr)
        elif use_audit:
            audit_records = audit_logger.read_audit_log(custom_audit_path=args.audit_file)
            if audit_records:
                steps = audit_records

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
            discovery_data=disc,
            caller_status=args.status,
            executive_notes=args.notes,
        )
        print(f"[✓] Report created: {rep_file}")
        sys.exit(0)


if __name__ == "__main__":
    main()
