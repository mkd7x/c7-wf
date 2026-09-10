#!/usr/bin/env python3
"""
Spec-Code Traceability Checker.
Validates bidirectional traceability between functional specifications (spec/SPEC-QA-*.md)
and implementation code (tools/*.py, workflows/*.md).
"""

import os
import re
import sys
import json
import argparse
from pathlib import Path
from typing import Dict, List, Any, Set

QA_DIR = Path(__file__).resolve().parent.parent
SPEC_DIR = QA_DIR / "spec"
TOOLS_DIR = QA_DIR / "tools"
WORKFLOWS_DIR = QA_DIR / "workflows"


def parse_spec_requirements(spec_dir: Path) -> Dict[str, Dict[str, Any]]:
    """Scan all SPEC-QA-*.md files and extract defined REQ IDs."""
    requirements = {}
    if not spec_dir.exists():
        return requirements

    req_pattern = re.compile(r"\|\s*\*\*(REQ-[A-Z0-9_-]+)\*\*\s*\|\s*([^|]+)\|\s*([^|]+)\|")

    for spec_file in sorted(spec_dir.glob("SPEC-QA-*.md")):
        content = spec_file.read_text(encoding="utf-8", errors="replace")
        for match in req_pattern.finditer(content):
            req_id = match.group(1).strip()
            title = match.group(2).strip()
            desc = match.group(3).strip()
            requirements[req_id] = {
                "id": req_id,
                "title": title,
                "description": desc,
                "spec_file": spec_file.name,
                "implemented_by": [],
                "verified_by": []
            }
    return requirements


def scan_code_annotations(requirements: Dict[str, Dict[str, Any]], search_dirs: List[Path]):
    """Search for @implements and @verifies annotations in files."""
    impl_pattern = re.compile(r"@implements\s+(REQ-[A-Z0-9_-]+)")
    verify_pattern = re.compile(r"@verifies\s+(REQ-[A-Z0-9_-]+)")

    # Also map known static configurations like .gitignore for REQ-ISO-03
    gitignore_path = QA_DIR / ".gitignore"
    if gitignore_path.is_file():
        content = gitignore_path.read_text(encoding="utf-8", errors="replace")
        if "target-repo" in content and "REQ-ISO-03" in requirements:
            requirements["REQ-ISO-03"]["implemented_by"].append({
                "file": ".gitignore",
                "line": 5,
                "tag": "@implements"
            })

    candidate_files = []
    for s_dir in search_dirs:
        if s_dir.exists():
            candidate_files.extend(list(s_dir.rglob("*")))

    # Include root documents like AGENTS.md
    for root_doc in ["AGENTS.md", "README.md"]:
        p = QA_DIR / root_doc
        if p.is_file():
            candidate_files.append(p)

    for file_path in candidate_files:
        if not file_path.is_file() or file_path.name.startswith("."):
            continue
        # Skip spec files to avoid self-referencing
        if SPEC_DIR in file_path.parents or file_path.parent == SPEC_DIR:
            continue
        if file_path.suffix not in [".py", ".md", ".sh", ".json"]:
            continue

        try:
            lines = file_path.read_text(encoding="utf-8", errors="replace").splitlines()
        except Exception:
            continue

        rel_file = file_path.relative_to(QA_DIR).as_posix()

        for line_idx, line in enumerate(lines, 1):
            # Search @implements
            for match in impl_pattern.finditer(line):
                req_id = match.group(1)
                if req_id in requirements:
                    requirements[req_id]["implemented_by"].append({
                        "file": rel_file,
                        "line": line_idx,
                        "tag": "@implements"
                    })
            # Search @verifies
            for match in verify_pattern.finditer(line):
                req_id = match.group(1)
                if req_id in requirements:
                    requirements[req_id]["verified_by"].append({
                        "file": rel_file,
                        "line": line_idx,
                        "tag": "@verifies"
                    })


def generate_traceability_report(requirements: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """Calculate coverage statistics and summarize findings.

    Implementation coverage (@implements) and verification coverage
    (@verifies) are tracked separately: a requirement counts as verified
    only with an explicit @verifies annotation (QAF-010).
    """
    total = len(requirements)
    implemented_count = sum(1 for r in requirements.values() if r["implemented_by"])
    verified_count = sum(1 for r in requirements.values() if r["verified_by"])

    impl_rate = round((implemented_count / total * 100), 1) if total > 0 else 0.0
    verify_rate = round((verified_count / total * 100), 1) if total > 0 else 0.0
    if total > 0 and implemented_count == total and verified_count == total:
        overall_status = "COMPLETE"
    else:
        overall_status = "INCOMPLETE"

    unimplemented = [r_id for r_id, r in requirements.items() if not r["implemented_by"]]
    unverified = [r_id for r_id, r in requirements.items() if not r["verified_by"]]

    return {
        "total_requirements": total,
        "implemented_count": implemented_count,
        "verified_count": verified_count,
        "coverage_percentage": impl_rate,
        "verified_percentage": verify_rate,
        "status": overall_status,
        "unimplemented": unimplemented,
        "unverified": unverified,
        "requirements": requirements
    }


def main():
    parser = argparse.ArgumentParser(description="Spec-Code Traceability Checker")
    parser.add_argument("--strict", action="store_true", help="Exit with non-zero code if coverage < 100%%")
    parser.add_argument("--json", action="store_true", help="Output raw JSON")
    args = parser.parse_args()

    requirements = parse_spec_requirements(SPEC_DIR)
    scan_code_annotations(requirements, [TOOLS_DIR, WORKFLOWS_DIR])
    report = generate_traceability_report(requirements)

    if args.json:
        print(json.dumps(report, indent=2))
        sys.exit(0 if report["status"] == "COMPLETE" else (1 if args.strict else 0))

    print("=" * 65)
    print("      SPEC-CODE REQUIREMENTS TRACEABILITY MATRIX (RTM)      ")
    print("=" * 65)
    print(f"Total Defined Requirements: {report['total_requirements']}")
    print(f"Implemented in Code:        {report['implemented_count']} / {report['total_requirements']} ({report['coverage_percentage']}%)")
    print(f"Verified (@verifies):       {report['verified_count']} / {report['total_requirements']} ({report['verified_percentage']}%)")
    print(f"Overall Status:             [{report['status']}]")
    print("-" * 65)

    print(f"{'Req ID':<14} {'Spec File':<24} {'Impl':<8} {'Verif':<8} {'Implementation'}")
    print("-" * 65)

    for req_id, data in sorted(requirements.items()):
        impl = "PASS" if data["implemented_by"] else "MISSING"
        ver = "PASS" if data["verified_by"] else "MISSING"
        impls = ", ".join(f"{i['file']}:{i['line']}" for i in data["implemented_by"]) or "None"
        print(f"{req_id:<14} {data['spec_file']:<24} {impl:<8} {ver:<8} {impls}")

    print("=" * 65)

    failed = False
    if report["unimplemented"]:
        print(f"\n[!] Missing implementation for: {', '.join(report['unimplemented'])}")
        failed = True
    if report["unverified"]:
        print(f"[!] Missing @verifies annotation for: {', '.join(report['unverified'])}")
        failed = True
    if failed:
        if args.strict:
            sys.exit(1)
    else:
        print("\n[✓] 100% Spec-Code Traceability Achieved (implemented + verified).")
        sys.exit(0)


if __name__ == "__main__":
    main()
