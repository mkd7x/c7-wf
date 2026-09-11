#!/usr/bin/env python3
"""
Plan & Workflow Schema Validator.
Enforces architectural consistency, task DAG validity, and completeness
across markdown execution plans and workflow runbooks.

@implements REQ-PACK-01
@implements REQ-PACK-03
@implements REQ-WORK-04
"""

import os
import re
import sys
import argparse
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional

# Import task graph parser
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
import task_graph


REQUIRED_PLAN_SECTIONS = [
    r"##\s+1\.\s+Executive Summary",
    r"##\s+2\.\s+Discovered Codebase Context",
    r"##\s+3\.\s+Architectural Design",
    r"##\s+4\.\s+Work Breakdown Structure",
    r"##\s+5\.\s+QA Verification Contract",
    r"##\s+6\.\s+Handoff Checklist"
]


def lint_plan(plan_path: Path, strict: bool = False) -> Tuple[bool, List[str], List[str]]:
    """
    Validate execution plan against standardized markdown schema.
    @implements REQ-PACK-01
    @implements REQ-PACK-03
    """
    errors = []
    warnings = []

    if not plan_path.exists():
        return False, [f"Plan file not found: {plan_path}"], []

    content = plan_path.read_text(encoding="utf-8", errors="replace")

    # 1. Check Metadata table
    if not re.search(r"\|\s*\*\*Plan ID\*\*\s*\|", content, re.IGNORECASE):
        errors.append("Missing mandatory 'Plan ID' in metadata table.")
    if not re.search(r"\|\s*\*\*Target Branch\*\*\s*\|", content, re.IGNORECASE):
        errors.append("Missing mandatory 'Target Branch' in metadata table.")
    if not re.search(r"\|\s*\*\*Overall Status\*\*\s*\|", content, re.IGNORECASE):
        errors.append("Missing mandatory 'Overall Status' in metadata table.")

    # 2. Check Required Sections
    for sec_pattern in REQUIRED_PLAN_SECTIONS:
        if not re.search(sec_pattern, content, re.IGNORECASE):
            errors.append(f"Missing required section matching pattern: '{sec_pattern}'")

    # 3. Check Scope Boundaries
    if "In-Scope" not in content or "Out-of-Scope" not in content:
        warnings.append("Plan should explicitly state 'In-Scope' and 'Out-of-Scope' boundaries.")

    # 4. Parse and Validate Tasks
    tasks = task_graph.parse_tasks_from_markdown(content)
    if not tasks:
        errors.append("No valid tasks found under Work Breakdown Structure (expected '### [TASK-XX] ...').")
    else:
        # Check task completeness
        for t in tasks:
            tid = t["id"]
            if not t["files"]:
                warnings.append(f"Task '{tid}' has no explicit 'Files to Touch' specified.")
            if not t["dod"]:
                warnings.append(f"Task '{tid}' has no explicit 'Definition of Done' checklist.")

        # Validate DAG dependencies & cycles
        dag_valid, dag_errors, dag_warnings = task_graph.validate_dag(tasks)
        errors.extend(dag_errors)
        warnings.extend(dag_warnings)

    # 5. Check QA Verification Contract
    if "QA Verification Contract" in content:
        contract_rows = re.findall(r"^\|\s*[A-Za-z0-9_-]+\s*\|.*\|.*\|.*\|", content, re.MULTILINE)
        # Exclude table header row
        contract_rows = [r for r in contract_rows if "Verification ID" not in r and "---" not in r]
        if not contract_rows and not any(t.get("qa_criteria") for t in tasks):
            warnings.append("No explicit QA verification assertions found for 03-qa.")

    # In strict mode, warnings become errors
    if strict and warnings:
        errors.extend([f"[STRICT] {w}" for w in warnings])
        warnings = []

    is_valid = len(errors) == 0
    return is_valid, errors, warnings


def lint_workflow(wf_path: Path, strict: bool = False) -> Tuple[bool, List[str], List[str]]:
    """
    Validate workflow runbook schema.
    @implements REQ-WORK-04
    """
    errors = []
    warnings = []

    if not wf_path.exists():
        return False, [f"Workflow file not found: {wf_path}"], []

    content = wf_path.read_text(encoding="utf-8", errors="replace")

    # 1. Frontmatter check
    if not content.startswith("---"):
        errors.append("Missing opening YAML frontmatter ('---').")
    else:
        fm_end = content.find("---", 3)
        if fm_end == -1:
            errors.append("Unclosed YAML frontmatter.")
        else:
            fm_text = content[3:fm_end]
            if "id:" not in fm_text:
                errors.append("YAML frontmatter missing mandatory 'id' field.")
            if "name:" not in fm_text:
                errors.append("YAML frontmatter missing mandatory 'name' field.")
            if "workflow_type:" not in fm_text:
                warnings.append("YAML frontmatter missing 'workflow_type' field.")

    # 2. Numbered steps check
    steps = re.findall(r"###\s+Step\s+(\d+):\s+(.+)", content)
    if len(steps) < 2:
        errors.append(f"Workflow must contain at least 2 numbered steps (found {len(steps)}).")

    # 3. Check for --step-id convention in CLI commands
    step_id_calls = re.findall(r"--step-id\s+([A-Za-z0-9_-]+)", content)
    if not step_id_calls:
        warnings.append("Workflow does not contain commands with '--step-id' tracking.")

    if strict and warnings:
        errors.extend([f"[STRICT] {w}" for w in warnings])
        warnings = []

    is_valid = len(errors) == 0
    return is_valid, errors, warnings


def main():
    parser = argparse.ArgumentParser(description="Plan & Workflow Schema Validator")
    subparsers = parser.add_subparsers(dest="command", required=True)

    plan_parser = subparsers.add_parser("lint-plan", help="Lint an execution plan document")
    plan_parser.add_argument("--file", required=True, help="Path to markdown plan")
    plan_parser.add_argument("--strict", action="store_true", help="Treat warnings as errors")

    wf_parser = subparsers.add_parser("lint-workflow", help="Lint a workflow runbook")
    wf_parser.add_argument("--file", required=True, help="Path to workflow runbook")
    wf_parser.add_argument("--strict", action="store_true", help="Treat warnings as errors")

    args = parser.parse_args()

    if args.command == "lint-plan":
        valid, errors, warnings = lint_plan(Path(args.file), strict=args.strict)
        print(f"=== Plan Linter: {Path(args.file).name} ===")
        for w in warnings:
            print(f"[WARN] {w}")
        if not valid:
            print(f"[!] Plan Validation FAILED ({len(errors)} errors):", file=sys.stderr)
            for err in errors:
                print(f"    - {err}", file=sys.stderr)
            sys.exit(1)
        print("[✓] Plan schema is VALID.")
        sys.exit(0)

    elif args.command == "lint-workflow":
        valid, errors, warnings = lint_workflow(Path(args.file), strict=args.strict)
        print(f"=== Workflow Linter: {Path(args.file).name} ===")
        for w in warnings:
            print(f"[WARN] {w}")
        if not valid:
            print(f"[!] Workflow Validation FAILED ({len(errors)} errors):", file=sys.stderr)
            for err in errors:
                print(f"    - {err}", file=sys.stderr)
            sys.exit(1)
        print("[✓] Workflow runbook schema is VALID.")
        sys.exit(0)


if __name__ == "__main__":
    main()
