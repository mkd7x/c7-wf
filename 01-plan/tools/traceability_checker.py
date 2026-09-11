#!/usr/bin/env python3
"""
Spec-Code Traceability Checker for 01-plan.
Validates bidirectional traceability between functional specifications (spec/SPEC-PLAN-*.md)
and implementation code (tools/*.py, workflows/*.md, templates/*.md, tests/*.py).

@implements REQ-PACK-01
@implements REQ-HAND-04
"""

import os
import re
import sys
import json
import argparse
from pathlib import Path
from typing import Dict, List, Any, Optional, Set

PLAN_DIR = Path(__file__).resolve().parent.parent
SPEC_DIR = PLAN_DIR / "spec"
TOOLS_DIR = PLAN_DIR / "tools"
WORKFLOWS_DIR = PLAN_DIR / "workflows"
TEMPLATES_DIR = PLAN_DIR / "templates"
TESTS_DIR = PLAN_DIR / "tests"


def parse_spec_requirements(spec_dir: Path) -> Dict[str, Dict[str, Any]]:
    """Scan all SPEC-PLAN-*.md files and extract defined REQ IDs."""
    requirements = {}
    if not spec_dir.exists():
        return requirements

    req_pattern = re.compile(r"\|\s*\*\*(REQ-[A-Z0-9_-]+)\*\*\s*\|\s*([^|]+)\|\s*([^|]+)\|")

    for spec_file in sorted(spec_dir.glob("SPEC-PLAN-*.md")):
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

    candidate_files = []
    for s_dir in search_dirs:
        if s_dir.exists():
            candidate_files.extend(list(s_dir.rglob("*")))

    # Include root documents
    for root_doc in ["AGENTS.md", "README.md"]:
        p = PLAN_DIR / root_doc
        if p.exists():
            candidate_files.append(p)

    for file_path in candidate_files:
        if not file_path.is_file() or file_path.suffix.lower() in [".pyc", ".png", ".jpg"]:
            continue
        if ".git" in file_path.parts or "runs" in file_path.parts:
            continue

        try:
            content = file_path.read_text(encoding="utf-8", errors="replace")
            rel_path = str(file_path.relative_to(PLAN_DIR))

            for line_no, line in enumerate(content.splitlines(), 1):
                # @implements
                for match in impl_pattern.finditer(line):
                    req_id = match.group(1)
                    if req_id in requirements:
                        requirements[req_id]["implemented_by"].append({
                            "file": rel_path,
                            "line": line_no,
                            "tag": "@implements"
                        })

                # @verifies
                for match in verify_pattern.finditer(line):
                    req_id = match.group(1)
                    if req_id in requirements:
                        requirements[req_id]["verified_by"].append({
                            "file": rel_path,
                            "line": line_no,
                            "tag": "@verifies"
                        })
        except Exception:
            pass


def generate_matrix_markdown(requirements: Dict[str, Dict[str, Any]]) -> str:
    """Generate Markdown for TRACEABILITY_MATRIX.md."""
    total_reqs = len(requirements)
    impl_count = sum(1 for r in requirements.values() if r["implemented_by"])
    verify_count = sum(1 for r in requirements.values() if r["verified_by"])
    full_count = sum(1 for r in requirements.values() if r["implemented_by"] and r["verified_by"])

    pct = (full_count / total_reqs * 100) if total_reqs > 0 else 0

    lines = [
        "# Requirements Traceability Matrix (RTM) - 01-plan",
        "",
        "## Summary Metrics",
        "",
        "| Metric | Count | Percentage |",
        "| :--- | :--- | :--- |",
        f"| **Total Specifications** | {len(set(r['spec_file'] for r in requirements.values()))} Specs | 100% |",
        f"| **Total Functional Requirements** | {total_reqs} Requirements | 100% |",
        f"| **Implemented in Code & Runbooks** (`@implements`) | {impl_count} / {total_reqs} | {(impl_count/total_reqs*100):.0f}% |",
        f"| **Verified by Tests & Runbooks** (`@verifies`) | {verify_count} / {total_reqs} | {(verify_count/total_reqs*100):.0f}% |",
        f"| **Overall Complete Traceability** | **{full_count} / {total_reqs}** | **{pct:.0f}%** |",
        "",
        "> Verified coverage is machine-checked: `python3 tools/traceability_checker.py --strict`",
        "> (read-only check; pass `--update-matrix` to regenerate this file)",
        "",
        "---",
        "",
        "## Traceability Matrix Table",
        "",
        "| Req ID | Requirement Title | Spec File | Implementation | Verification Artifact | Status |",
        "| :--- | :--- | :--- | :--- | :--- | :--- |"
    ]

    for req_id, r in sorted(requirements.items()):
        impl_str = ", ".join([f"`{i['file']}:{i['line']}`" for i in r["implemented_by"][:2]]) or "*None*"
        ver_str = ", ".join([f"`{v['file']}:{v['line']}`" for v in r["verified_by"][:2]]) or "*None*"
        status = "🟢 VERIFIED" if (r["implemented_by"] and r["verified_by"]) else "🔴 GAP"
        lines.append(f"| **{req_id}** | {r['title']} | [{r['spec_file']}]({r['spec_file']}) | {impl_str} | {ver_str} | {status} |")

    lines.append("")
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Traceability Checker for 01-plan")
    parser.add_argument("--strict", action="store_true", help="Exit 1 if any gaps exist")
    parser.add_argument("--update-matrix", action="store_true", default=False,
                        help="Regenerate TRACEABILITY_MATRIX.md (check is read-only by default)")
    parser.add_argument("--json", action="store_true", help="Output JSON report")
    return parser


def main(argv: Optional[List[str]] = None):
    parser = build_parser()
    args = parser.parse_args(argv)

    reqs = parse_spec_requirements(SPEC_DIR)
    scan_code_annotations(reqs, [TOOLS_DIR, WORKFLOWS_DIR, TEMPLATES_DIR, TESTS_DIR])

    total = len(reqs)
    impl_missing = [r_id for r_id, r in reqs.items() if not r["implemented_by"]]
    ver_missing = [r_id for r_id, r in reqs.items() if not r["verified_by"]]
    gaps = sorted(list(set(impl_missing + ver_missing)))

    if args.update_matrix:
        matrix_file = SPEC_DIR / "TRACEABILITY_MATRIX.md"
        matrix_file.write_text(generate_matrix_markdown(reqs), encoding="utf-8")
        print(f"[✓] Traceability matrix updated: {matrix_file}")

    if args.json:
        report = {
            "total": total,
            "implemented": total - len(impl_missing),
            "verified": total - len(ver_missing),
            "gaps": gaps,
            "requirements": reqs
        }
        print(json.dumps(report, indent=2))
        sys.exit(0 if not gaps or not args.strict else 1)

    print(f"=== Spec-Code Traceability Checker (01-plan) ===")
    print(f"Total Requirements: {total}")
    print(f"Implemented:        {total - len(impl_missing)} / {total}")
    print(f"Verified:           {total - len(ver_missing)} / {total}")

    if gaps:
        print(f"\n[!] Traceability Gaps Found ({len(gaps)} requirements):", file=sys.stderr)
        for g in gaps:
            missing_parts = []
            if g in impl_missing:
                missing_parts.append("missing @implements")
            if g in ver_missing:
                missing_parts.append("missing @verifies")
            print(f"    - {g}: {', '.join(missing_parts)}", file=sys.stderr)
        if args.strict:
            sys.exit(1)
    else:
        print("\n[✓] 100% Spec-Code Traceability achieved! All requirements implemented and verified.")
        sys.exit(0)


if __name__ == "__main__":
    main()
