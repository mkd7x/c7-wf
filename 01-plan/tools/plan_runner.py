#!/usr/bin/env python3
"""
Planning Framework CLI Hub.
Provides end-to-end lifecycle management for 01-plan:
- Intake (Jira ticket extraction or adhoc/prompt parsing)
- Codebase context discovery
- Task DAG scheduling and cycle detection
- Plan & workflow linting
- Jira synchronization (comments, status transitions, subtasks)
- Deterministic plan packaging
- Git commitment and 02-exe handoff protocol

@implements REQ-PACK-01
@implements REQ-PACK-02
@implements REQ-HAND-01
@implements REQ-HAND-02
@implements REQ-HAND-03
"""

import os
import re
import sys
import json
import shutil
import subprocess
import argparse
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

SCRIPT_DIR = Path(__file__).resolve().parent
BASE_DIR = SCRIPT_DIR.parent
PLANS_DIR = BASE_DIR / "plans"
RUNS_DIR = BASE_DIR / "runs" / "latest"
TEMPLATES_DIR = BASE_DIR / "templates"

sys.path.insert(0, str(SCRIPT_DIR))
import context_discovery
import task_graph
import plan_validator
import jira_client


def run_intake(workflow: str, ticket: Optional[str] = None, title: Optional[str] = None,
               brief: Optional[str] = None, brief_file: Optional[str] = None) -> Dict[str, Any]:
    """
    Intake requirement from Jira or adhoc brief.
    @implements REQ-WORK-01
    @implements REQ-WORK-02
    """
    RUNS_DIR.mkdir(parents=True, exist_ok=True)

    if workflow == "jira":
        if not ticket:
            raise ValueError("Jira workflow requires --ticket (e.g. PROJ-1024)")
        client = jira_client.JiraClient()
        issue = client.fetch_issue(ticket)
        intake_data = {
            "workflow": "jira",
            "source_ref": ticket.upper(),
            "title": issue["summary"],
            "description": issue["description"],
            "acceptance_criteria": issue["acceptance_criteria"],
            "components": issue["components"],
            "timestamp": datetime.now().isoformat()
        }
    else:
        brief_text = brief or ""
        if brief_file and Path(brief_file).exists():
            brief_text += "\n" + Path(brief_file).read_text(encoding="utf-8", errors="replace")

        intake_data = {
            "workflow": "adhoc",
            "source_ref": "LOCAL_BRIEF",
            "title": title or "Ad-hoc Implementation Initiative",
            "description": brief_text.strip() or "Ad-hoc feature specification",
            "acceptance_criteria": [
                "Implement feature requested in brief",
                "Pass all existing and new unit/integration tests"
            ],
            "components": ["General"],
            "timestamp": datetime.now().isoformat()
        }

    out_file = RUNS_DIR / "intake.json"
    out_file.write_text(json.dumps(intake_data, indent=2), encoding="utf-8")
    return intake_data


def package_plan(title: str, workflow_mode: str, source_ref: str,
                 target_repo: str = "target-repo/",
                 target_branch: str = "main",
                 tasks: Optional[List[Dict[str, Any]]] = None,
                 qa_contract: Optional[List[Dict[str, str]]] = None) -> Path:
    """
    Package an execution plan into plans/ using PLAN_TEMPLATE.md.
    @implements REQ-PACK-01
    @implements REQ-PACK-02
    """
    PLANS_DIR.mkdir(parents=True, exist_ok=True)
    template_file = TEMPLATES_DIR / "PLAN_TEMPLATE.md"
    template_content = template_file.read_text(encoding="utf-8")

    now = datetime.now()
    timestamp_str = now.strftime("%Y%m%d_%H%M%S")
    clean_title = re.sub(r"[^A-Za-z0-9_-]+", "_", title.lower()).strip("_")
    slug = f"{source_ref.lower()}_{clean_title}" if source_ref != "LOCAL_BRIEF" else clean_title
    plan_filename = f"{timestamp_str}_{slug}_plan.md"
    plan_path = PLANS_DIR / plan_filename
    plan_id = f"PLAN-{timestamp_str}"

    # Load context if available
    context_file = RUNS_DIR / "context.json"
    context = {}
    if context_file.exists():
        try:
            context = json.loads(context_file.read_text(encoding="utf-8"))
        except Exception:
            pass

    # Load intake if available
    intake_file = RUNS_DIR / "intake.json"
    intake = {}
    if intake_file.exists():
        try:
            intake = json.loads(intake_file.read_text(encoding="utf-8"))
        except Exception:
            pass

    # Default tasks if not provided
    if not tasks:
        prefix = source_ref if source_ref != "LOCAL_BRIEF" else "TASK"
        tasks = [
            {
                "id": f"{prefix}-01",
                "title": f"Initial Setup & Core Domain Models for {title}",
                "wave": 1,
                "dependencies": [],
                "component": "Domain",
                "files": ["src/Domain/Model.cs"],
                "dod": ["Model implemented with validations", "Unit tests added"],
                "qa_criteria": {"action": "Run domain unit tests", "expected_outcome": "100% Pass"}
            },
            {
                "id": f"{prefix}-02",
                "title": f"Service Implementation & Endpoint for {title}",
                "wave": 2,
                "dependencies": [f"{prefix}-01"],
                "component": "Application / API",
                "files": ["src/Application/Service.cs", "src/API/Controller.cs"],
                "dod": ["Endpoint wired to service", "Integration tests passing"],
                "qa_criteria": {"action": "HTTP GET /api/resource", "expected_outcome": "Status 200 OK"}
            }
        ]

    # Reject invalid task graphs before packaging (fail loudly, never emit partial waves)
    dag_valid, dag_errors, _ = task_graph.validate_dag(tasks)
    if not dag_valid:
        raise ValueError(f"Cannot package plan: invalid task DAG: {'; '.join(dag_errors)}")

    # Compute execution waves
    waves = task_graph.compute_execution_waves(tasks)
    waves_summary = task_graph.generate_waves_markdown(waves)
    wave_positions = {t["id"]: idx + 1 for idx, wave in enumerate(waves) for t in wave}

    # Render task specifications
    task_specs = []
    for t in tasks:
        wave_num = wave_positions.get(t["id"], t.get("wave", 1))
        t["wave"] = wave_num
        files_str = "\n".join([f"  - `{f}`" for f in t.get("files", [])])
        dod_str = "\n".join([f"- [ ] {d}" for d in t.get("dod", [])])
        qa_action = t.get("qa_criteria", {}).get("action", "Verification check")
        qa_expect = t.get("qa_criteria", {}).get("expected_outcome", "Pass")
        spec = f"""### [{t['id']}] {t['title']}
- **Wave**: {wave_num}
- **Dependencies**: `{json.dumps(t.get('dependencies', []))}`
- **Component / Layer**: {t.get('component', 'General')}
- **Files to Touch**:
{files_str}

#### Description
Implementation for {t['title']}.

#### Definition of Done (DoD)
{dod_str}

#### Verification Criteria (`03-qa`)
- **Action**: {qa_action}
- **Expected Outcome**: {qa_expect}
"""
        task_specs.append(spec)

    # QA Contract Table
    qa_rows = []
    for idx, t in enumerate(tasks, 1):
        qa_action = t.get("qa_criteria", {}).get("action", f"Verify step {idx}")
        qa_expect = t.get("qa_criteria", {}).get("expected_outcome", "Pass")
        qa_rows.append(f"| `QA-VERIFY-{idx:02d}` | Functional | `{t['id']}` | {qa_action} -> {qa_expect} |")

    # In-scope & out-of-scope items
    acs = intake.get("acceptance_criteria", ["Complete feature requirements"])
    in_scope = "\n".join([f"- {ac}" for ac in acs])
    out_scope = "- Infrastructure architecture refactoring outside current service\n- Unrelated third-party integrations"

    # Replacements
    content = template_content
    content = content.replace("{{PLAN_TITLE}}", title)
    content = content.replace("{{PLAN_ID}}", plan_id)
    content = content.replace("{{WORKFLOW_MODE}}", workflow_mode.upper())
    content = content.replace("{{SOURCE_REF}}", source_ref)
    content = content.replace("{{TARGET_REPO}}", target_repo)
    content = content.replace("{{TARGET_BRANCH}}", target_branch)
    content = content.replace("{{TIMESTAMP}}", now.strftime("%Y-%m-%d %H:%M:%S"))
    content = content.replace("{{COMMIT_SHA}}", "UNCOMMITTED")
    content = content.replace("{{STATUS_BADGE}}", "🟡 DRAFT")
    content = content.replace("{{OVERALL_STATUS}}", "DRAFT")
    content = content.replace("{{OBJECTIVE_DESCRIPTION}}", intake.get("description", f"Deliver {title}."))
    content = content.replace("{{IN_SCOPE_ITEMS}}", in_scope)
    content = content.replace("{{OUT_OF_SCOPE_ITEMS}}", out_scope)
    content = content.replace("{{DETECTED_STACK}}", context.get("language", "Generic"))
    content = content.replace("{{DETECTED_FRAMEWORKS}}", ", ".join(context.get("frameworks", [])) or "None detected")
    content = content.replace("{{ARCHITECTURAL_PATTERNS}}", "Clean Architecture / Layered Service")
    content = content.replace("{{RELEVANT_DIRECTORIES}}", "\n".join([f"- `{d}`" for d in context.get("architecture_layers", ["src/"])[:5]]))
    content = content.replace("{{ARCHITECTURAL_DECISIONS}}", "Follow standard repository patterns and adhere to dependency inversion.")
    content = content.replace("{{COMPONENT_BOUNDARIES}}", "Domain layer possesses zero external dependencies. Application coordinates use cases.")
    content = content.replace("{{DATA_MODELS_SECTION}}", "Database entities mapped via ORM migrations.")
    content = content.replace("{{EXECUTION_WAVES_SUMMARY}}", waves_summary)
    content = content.replace("{{TASK_SPECIFICATIONS}}", "\n---\n\n".join(task_specs))
    content = content.replace("{{QA_CONTRACT_TABLE}}", "\n".join(qa_rows))
    content = content.replace("{{HANDOFF_STATUS}}", "PENDING COMMIT")

    plan_path.write_text(content, encoding="utf-8")
    return plan_path


def commit_plan_to_git(plan_file: Path, branch: Optional[str] = None, push: bool = False,
                       skip_validation: bool = False) -> Dict[str, Any]:
    """
    Commit the execution plan to Git and inject commit provenance into the header.
    The plan is validated (strict schema lint + DAG validation) BEFORE any file
    mutation or git operation. Invalid plans raise ValueError and are never
    marked READY FOR 02-EXE (per SPEC-PLAN-005 AC3).
    @implements REQ-HAND-01
    @implements REQ-HAND-02
    """
    plan_file = Path(plan_file).resolve()
    if not plan_file.exists():
        raise FileNotFoundError(f"Plan file not found: {plan_file}")

    if not skip_validation:
        valid, errors, _ = plan_validator.lint_plan(plan_file, strict=True)
        if not valid:
            raise ValueError(
                f"Cannot commit plan: validation failed with {len(errors)} error(s): "
                + "; ".join(errors)
            )

    content = plan_file.read_text(encoding="utf-8")

    # Update status to READY FOR 02-EXE
    content = re.sub(r"\|\s*\*\*Overall Status\*\*\s*\|.*$", "| **Overall Status** | **🟢 READY** (`READY FOR 02-EXE`) |", content, flags=re.MULTILINE)
    content = re.sub(r"\*\*Handoff Gate Status\*\*:\s*`.*?`", "**Handoff Gate Status**: `READY FOR 02-EXE`", content)
    if branch:
        content = re.sub(r"\|\s*\*\*Target Branch\*\*\s*\|.*$", f"| **Target Branch** | `{branch}` |", content, flags=re.MULTILINE)

    plan_file.write_text(content, encoding="utf-8")

    # Execute Git staging and commit
    try:
        rel_path = str(plan_file.relative_to(BASE_DIR.parent))
    except ValueError:
        rel_path = str(plan_file)

    # Git add
    subprocess.run(["git", "add", str(plan_file)], cwd=str(BASE_DIR.parent), check=True)

    # Commit message
    plan_name = plan_file.stem
    commit_msg = f"feat(plan): add execution plan {plan_name}"
    commit_res = subprocess.run(["git", "commit", "-m", commit_msg], cwd=str(BASE_DIR.parent),
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    # Get commit SHA
    sha_proc = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(BASE_DIR.parent),
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    commit_sha = sha_proc.stdout.strip() if sha_proc.returncode == 0 else "LOCAL_MOCK_SHA_" + datetime.now().strftime("%Y%m%d%H%M%S")

    # Update plan content with real commit SHA
    content = re.sub(r"\|\s*\*\*Git Commit SHA\*\*\s*\|.*$", f"| **Git Commit SHA** | `{commit_sha}` |", content, flags=re.MULTILINE)
    plan_file.write_text(content, encoding="utf-8")

    # Amend commit if git commit succeeded
    if commit_res.returncode == 0:
        subprocess.run(["git", "add", str(plan_file)], cwd=str(BASE_DIR.parent), check=True)
        subprocess.run(["git", "commit", "--amend", "--no-edit"], cwd=str(BASE_DIR.parent), check=True)
        sha_proc = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(BASE_DIR.parent), stdout=subprocess.PIPE, text=True)
        commit_sha = sha_proc.stdout.strip()

    if push:
        try:
            subprocess.run(["git", "push"], cwd=str(BASE_DIR.parent), check=True)
        except Exception as e:
            print(f"[WARN] Git push skipped/failed: {e}")

    result = {
        "plan_file": str(plan_file),
        "commit_sha": commit_sha,
        "branch": branch or "current",
        "status": "READY FOR 02-EXE"
    }

    # Save to runs/latest/latest_plan.json
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    (RUNS_DIR / "latest_plan.json").write_text(json.dumps(result, indent=2), encoding="utf-8")

    return result


def _plan_readiness(plan_path: Path) -> Tuple[Dict[str, Any], List[str]]:
    """Return (plan payload, blocking reasons). Empty reasons means READY for 02-exe."""
    reasons: List[str] = []
    content = plan_path.read_text(encoding="utf-8", errors="replace")
    tasks = task_graph.parse_tasks_from_markdown(content)
    try:
        waves = task_graph.compute_execution_waves(tasks)
    except ValueError as e:
        waves = []
        reasons.append(str(e))

    # Extract commit SHA and branch from header
    sha_match = re.search(r"\|\s*\*\*Git Commit SHA\*\*\s*\|\s*`?([A-Za-z0-9_-]+)`?\s*\|", content)
    branch_match = re.search(r"\|\s*\*\*Target Branch\*\*\s*\|\s*`?([^`|\n]+)`?\s*\|", content)
    status_match = re.search(r"\|\s*\*\*Overall Status\*\*\s*\|\s*(.+)\|", content)

    commit_sha = sha_match.group(1).strip() if sha_match else "UNKNOWN"
    overall_status = status_match.group(1).strip() if status_match else "UNKNOWN"

    if "READY FOR 02-EXE" not in overall_status:
        reasons.append(
            f"Plan status is '{overall_status}', not 'READY FOR 02-EXE'. "
            "Commit the plan via 'commit-plan' before handoff to 02-exe."
        )
    if not re.fullmatch(r"[0-9a-f]{40}", commit_sha):
        reasons.append(
            f"Plan has no valid 40-character Git commit SHA (found '{commit_sha}')."
        )

    payload = {
        "plan_file": str(plan_path),
        "commit_sha": commit_sha,
        "target_branch": branch_match.group(1).strip() if branch_match else "main",
        "overall_status": overall_status,
        "task_count": len(tasks),
        "waves_count": len(waves),
        "tasks": tasks,
        "waves": [[t["id"] for t in w] for w in waves],
    }
    return payload, reasons


def get_latest_plan(ticket: Optional[str] = None, require_ready: bool = True) -> Dict[str, Any]:
    """
    Machine query interface for 02-exe to pull the active committed plan.
    By default only plans with status READY FOR 02-EXE and a valid 40-char
    Git SHA are returned; otherwise a PLAN_NOT_READY payload is returned and
    02-exe must refuse to start. Pass require_ready=False for inspection only.
    @implements REQ-HAND-03
    """
    plans = sorted(PLANS_DIR.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True)
    if ticket:
        ticket_lower = ticket.lower()
        matched = [p for p in plans if ticket_lower in p.name.lower()]
        if not matched:
            return {"status": "TICKET_NOT_FOUND", "ticket": ticket}
        candidates = matched
    else:
        if not plans:
            return {"status": "NO_PLANS_FOUND"}
        candidates = plans

    for plan_path in candidates:
        payload, reasons = _plan_readiness(plan_path)
        if not reasons:
            return payload
        if not require_ready:
            return {**payload, "status": "PLAN_NOT_READY", "reasons": reasons}

    # No READY plan among candidates: report the newest one's blockers
    payload, reasons = _plan_readiness(candidates[0])
    return {**payload, "status": "PLAN_NOT_READY", "reasons": reasons}


def main():
    parser = argparse.ArgumentParser(description="Planning Framework CLI Hub")
    subparsers = parser.add_subparsers(dest="action", required=True)

    # intake
    intake_p = subparsers.add_parser("intake", help="Intake requirement from Jira or prompt")
    intake_p.add_argument("--workflow", choices=["jira", "adhoc"], required=True)
    intake_p.add_argument("--ticket", help="Jira ticket key")
    intake_p.add_argument("--title", help="Initiative title")
    intake_p.add_argument("--brief", help="Natural language brief text")
    intake_p.add_argument("--file", help="Path to brief markdown file")
    intake_p.add_argument("--step-id", help="Audit step identifier")

    # discover
    disc_p = subparsers.add_parser("discover", help="Scan target codebase context")
    disc_p.add_argument("--source", default="target-repo/", help="Target repo path")
    disc_p.add_argument("--step-id", help="Audit step identifier")
    disc_p.add_argument("--json", action="store_true", help="Print json output")

    # lint-plan
    lp_p = subparsers.add_parser("lint-plan", help="Lint execution plan against schema")
    lp_p.add_argument("--file", required=True, help="Path to plan file")
    lp_p.add_argument("--strict", action="store_true", help="Enforce strict validation")
    lp_p.add_argument("--step-id", help="Audit step identifier")

    # graph-tasks
    gt_p = subparsers.add_parser("graph-tasks", help="Validate task DAG and compute waves")
    gt_p.add_argument("--file", required=True, help="Path to plan file")
    gt_p.add_argument("--format-waves", action="store_true", help="Print formatted markdown waves")
    gt_p.add_argument("--step-id", help="Audit step identifier")

    # sync-jira
    sync_p = subparsers.add_parser("sync-jira", help="Sync plan to Jira")
    sync_p.add_argument("--ticket", required=True, help="Jira ticket key")
    sync_p.add_argument("--file", required=True, help="Path to plan file")
    sync_p.add_argument("--transition", default="In Progress", help="Target status transition")
    sync_p.add_argument("--create-subtasks", action="store_true", help="Create child subtasks in Jira")
    sync_p.add_argument("--dry-run", action="store_true", help="Force dry-run/mock mode")
    sync_p.add_argument("--step-id", help="Audit step identifier")

    # package
    pkg_p = subparsers.add_parser("package", help="Assemble execution plan into plans/")
    pkg_p.add_argument("--title", required=True, help="Feature title")
    pkg_p.add_argument("--workflow", choices=["jira", "adhoc"], default="adhoc")
    pkg_p.add_argument("--ticket", help="Source ticket key if jira")
    pkg_p.add_argument("--branch", default="main", help="Target git branch")
    pkg_p.add_argument("--target", default="target-repo/", help="Target repo directory")
    pkg_p.add_argument("--step-id", help="Audit step identifier")

    # commit-plan
    cp_p = subparsers.add_parser("commit-plan", help="Commit plan to Git and inject provenance")
    cp_p.add_argument("--file", required=True, help="Path to plan file")
    cp_p.add_argument("--branch", help="Target git branch name")
    cp_p.add_argument("--push", action="store_true", help="Push commit to git remote")
    cp_p.add_argument("--skip-validation", action="store_true",
                      help="Skip pre-commit validation (NOT recommended; for recovery only)")
    cp_p.add_argument("--step-id", help="Audit step identifier")

    # get-latest-plan
    gl_p = subparsers.add_parser("get-latest-plan", help="Retrieve active plan for 02-exe")
    gl_p.add_argument("--ticket", help="Filter by Jira ticket")
    gl_p.add_argument("--json", action="store_true", help="Print json output")
    gl_p.add_argument("--allow-not-ready", action="store_true",
                      help="Return newest plan even if not READY (inspection only; 02-exe must not execute it)")

    # lint-workflow
    lw_p = subparsers.add_parser("lint-workflow", help="Lint a workflow runbook")
    lw_p.add_argument("--file", required=True, help="Path to workflow file")
    lw_p.add_argument("--strict", action="store_true", help="Enforce strict validation")

    args = parser.parse_args()

    if args.action == "intake":
        res = run_intake(args.workflow, ticket=args.ticket, title=args.title,
                         brief=args.brief, brief_file=args.file)
        print(f"[✓] Intake completed ({args.workflow}): {res['title']}")
        print(f"    Saved to: {RUNS_DIR / 'intake.json'}")

    elif args.action == "discover":
        res = context_discovery.discover_codebase(Path(args.source))
        if args.json:
            print(json.dumps(res, indent=2))
        else:
            print(f"[✓] Context discovery completed for {args.source}")
            print(f"    Language: {res['language']}, Frameworks: {', '.join(res['frameworks']) or 'None'}")

    elif args.action == "lint-plan":
        valid, errors, warnings = plan_validator.lint_plan(Path(args.file), strict=args.strict)
        for w in warnings:
            print(f"[WARN] {w}")
        if not valid:
            print(f"[!] Plan Validation FAILED ({len(errors)} errors):", file=sys.stderr)
            for err in errors:
                print(f"    - {err}", file=sys.stderr)
            sys.exit(1)
        print(f"[✓] Plan is VALID: {args.file}")

    elif args.action == "graph-tasks":
        content = Path(args.file).read_text(encoding="utf-8", errors="replace")
        tasks = task_graph.parse_tasks_from_markdown(content)
        valid, errors, warnings = task_graph.validate_dag(tasks)
        if not valid:
            print(f"[!] DAG Validation FAILED:", file=sys.stderr)
            for err in errors:
                print(f"    - {err}", file=sys.stderr)
            sys.exit(1)
        waves = task_graph.compute_execution_waves(tasks)
        print(f"[✓] Task DAG VALID ({len(tasks)} tasks across {len(waves)} waves).")
        if args.format_waves:
            print("\n" + task_graph.generate_waves_markdown(waves))

    elif args.action == "sync-jira":
        plan_path = Path(args.file)
        if not plan_path.exists():
            print(f"[!] Plan file not found: {plan_path}", file=sys.stderr)
            sys.exit(1)
        client = jira_client.JiraClient(dry_run=args.dry_run)
        plan_content = plan_path.read_text(encoding="utf-8", errors="replace")
        tasks = task_graph.parse_tasks_from_markdown(plan_content)

        # Extract plan metadata for the templated comment
        plan_id_m = re.search(r"\|\s*\*\*Plan ID\*\*\s*\|\s*`?([^`|\n]+)`?\s*\|", plan_content)
        title_m = re.search(r"^#\s+Execution Plan:\s*(.+)$", plan_content, re.MULTILINE)
        branch_m = re.search(r"\|\s*\*\*Target Branch\*\*\s*\|\s*`?([^`|\n]+)`?\s*\|", plan_content)
        sha_m = re.search(r"\|\s*\*\*Git Commit SHA\*\*\s*\|\s*`?([A-Za-z0-9_-]+)`?\s*\|", plan_content)
        comment = jira_client.render_plan_comment(
            plan_id=plan_id_m.group(1).strip() if plan_id_m else "PLAN-UNKNOWN",
            plan_title=title_m.group(1).strip() if title_m else plan_path.stem,
            plan_file=plan_path.name,
            target_branch=branch_m.group(1).strip() if branch_m else "main",
            commit_sha=sha_m.group(1).strip() if sha_m else "UNCOMMITTED",
            tasks=tasks,
        )
        client.post_comment(args.ticket, comment)

        # Transition
        if args.transition:
            client.transition_issue(args.ticket, args.transition)

        # Create subtasks if requested
        if args.create_subtasks:
            client.create_subtasks(args.ticket, tasks)

        print(f"[✓] Jira sync completed for {args.ticket}.")

    elif args.action == "package":
        ref = args.ticket if args.workflow == "jira" and args.ticket else "LOCAL_BRIEF"
        plan_p = package_plan(args.title, args.workflow, ref,
                              target_repo=args.target, target_branch=args.branch)
        print(f"[✓] Execution Plan packaged: {plan_p}")

    elif args.action == "commit-plan":
        try:
            res = commit_plan_to_git(Path(args.file), branch=args.branch, push=args.push,
                                     skip_validation=args.skip_validation)
        except ValueError as e:
            print(f"[!] {e}", file=sys.stderr)
            sys.exit(1)
        print(f"[✓] Plan committed to Git:")
        print(f"    Commit SHA: {res['commit_sha']}")
        print(f"    Status:     {res['status']}")

    elif args.action == "get-latest-plan":
        res = get_latest_plan(ticket=args.ticket, require_ready=not args.allow_not_ready)
        if res.get("status") in ("PLAN_NOT_READY", "NO_PLANS_FOUND", "TICKET_NOT_FOUND"):
            if res.get("status") == "NO_PLANS_FOUND":
                print("[!] No plans found in plans/. Package a plan first.", file=sys.stderr)
            elif res.get("status") == "TICKET_NOT_FOUND":
                print(f"[!] No plan found matching ticket '{args.ticket}'.", file=sys.stderr)
            else:
                print("[!] No READY plan available for 02-exe:", file=sys.stderr)
                for reason in res.get("reasons", []):
                    print(f"    - {reason}", file=sys.stderr)
            if args.json:
                print(json.dumps(res, indent=2))
            sys.exit(2)
        if args.json:
            print(json.dumps(res, indent=2))
        else:
            print(f"=== Active Execution Plan ===")
            print(f"File:       {res.get('plan_file')}")
            print(f"Commit SHA: {res.get('commit_sha')}")
            print(f"Branch:     {res.get('target_branch')}")
            print(f"Status:     {res.get('overall_status')}")
            print(f"Tasks:      {res.get('task_count')} tasks ({res.get('waves_count')} waves)")

    elif args.action == "lint-workflow":
        valid, errors, warnings = plan_validator.lint_workflow(Path(args.file), strict=args.strict)
        for w in warnings:
            print(f"[WARN] {w}")
        if not valid:
            print(f"[!] Workflow Validation FAILED:", file=sys.stderr)
            for err in errors:
                print(f"    - {err}", file=sys.stderr)
            sys.exit(1)
        print(f"[✓] Workflow runbook is VALID: {args.file}")


if __name__ == "__main__":
    main()
