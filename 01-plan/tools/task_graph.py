#!/usr/bin/env python3
"""
Task DAG & Graph Scheduling Engine.
Parses task definitions from Markdown plans, validates dependencies,
detects circular references, and computes topological execution waves.

@implements REQ-TASK-01
@implements REQ-TASK-02
@implements REQ-TASK-03
@implements REQ-TASK-04
"""

import os
import re
import sys
import json
import argparse
from pathlib import Path
from typing import Dict, List, Any, Tuple, Set, Optional


def parse_tasks_from_markdown(content: str) -> List[Dict[str, Any]]:
    """
    Parse task blocks from markdown content.
    Expects headers like: ### [TASK-01] Title or ### [KEY-123] Title
    @implements REQ-TASK-01
    @implements REQ-TASK-02
    """
    tasks = []
    task_header_re = re.compile(r"^###\s+\[([A-Za-z0-9_-]+)\]\s+(.+)$", re.MULTILINE)
    matches = list(task_header_re.finditer(content))

    for i, match in enumerate(matches):
        task_id = match.group(1).strip()
        title = match.group(2).strip()
        start_pos = match.end()
        end_pos = matches[i + 1].start() if i + 1 < len(matches) else len(content)
        block = content[start_pos:end_pos]

        # Extract dependencies
        deps = []
        dep_match = re.search(r"-\s*(?:\*\*)?(?:Dependencies|depends_on)(?:\*\*)?:\s*`?\[(.*?)\]`?", block, re.IGNORECASE)
        if dep_match:
            raw_deps = dep_match.group(1).strip()
            if raw_deps:
                deps = [d.strip().strip("'\"") for d in raw_deps.split(",") if d.strip()]

        # Extract Wave
        wave = None
        wave_match = re.search(r"-\s*(?:\*\*)?Wave(?:\*\*)?:\s*(\d+)", block, re.IGNORECASE)
        if wave_match:
            try:
                wave = int(wave_match.group(1))
            except ValueError:
                pass

        # Extract Component / Layer
        component = "General"
        comp_match = re.search(r"-\s*(?:\*\*)?Component\s*(?:/\s*Layer)?(?:\*\*)?:\s*(.+)$", block, re.IGNORECASE | re.MULTILINE)
        if comp_match:
            component = comp_match.group(1).strip()

        # Extract Files to Touch
        files = []
        files_section = re.search(r"-\s*(?:\*\*)?Files to Touch(?:\*\*)?:\s*\n((?:\s*-\s*.+\n?)+)", block, re.IGNORECASE)
        if files_section:
            for line in files_section.group(1).splitlines():
                clean_f = re.sub(r"^\s*-\s*`?([^`\n]+)`?.*$", r"\1", line).strip()
                if clean_f and not clean_f.startswith("{{"):
                    files.append(clean_f)

        # Extract Definition of Done (DoD)
        dod = []
        dod_section = re.search(r"####\s+Definition of Done\s*(?:\(DoD\))?\s*\n((?:\s*-\s*\[[ xX]\].+\n?)+)", block, re.IGNORECASE)
        if dod_section:
            for line in dod_section.group(1).splitlines():
                clean_item = re.sub(r"^\s*-\s*\[[ xX]\]\s*", "", line).strip()
                if clean_item and not clean_item.startswith("{{"):
                    dod.append(clean_item)

        # Extract QA Verification Criteria
        qa_criteria = {}
        qa_section = re.search(r"####\s+Verification Criteria.*?\n((?:-\s*.+\n?)+)", block, re.IGNORECASE)
        if qa_section:
            action_m = re.search(r"-\s*\*\*Action\*\*:\s*(.+)", qa_section.group(1))
            outcome_m = re.search(r"-\s*\*\*Expected Outcome\*\*:\s*(.+)", qa_section.group(1))
            if action_m:
                qa_criteria["action"] = action_m.group(1).strip()
            if outcome_m:
                qa_criteria["expected_outcome"] = outcome_m.group(1).strip()

        tasks.append({
            "id": task_id,
            "title": title,
            "wave": wave,
            "dependencies": deps,
            "component": component,
            "files": files,
            "dod": dod,
            "qa_criteria": qa_criteria
        })

    return tasks


def validate_dag(tasks: List[Dict[str, Any]]) -> Tuple[bool, List[str], List[str]]:
    """
    Validate DAG constraints:
    - No duplicate task IDs
    - All declared dependencies exist
    - No self-dependencies
    - No circular dependency cycles
    @implements REQ-TASK-03
    """
    errors = []
    warnings = []
    task_map = {t["id"]: t for t in tasks}

    if not tasks:
        warnings.append("No tasks found in document.")
        return True, errors, warnings

    # Check for duplicate task IDs
    seen: Set[str] = set()
    duplicates: Set[str] = set()
    for t in tasks:
        tid = t["id"]
        if tid in seen:
            duplicates.add(tid)
        seen.add(tid)
    for dup in sorted(duplicates):
        errors.append(f"Duplicate task ID detected: '{dup}' (task IDs must be unique).")

    # Check for non-existent dependencies and self-loops
    adj: Dict[str, List[str]] = {t["id"]: [] for t in tasks}
    for t in tasks:
        tid = t["id"]
        for dep in t["dependencies"]:
            if dep == tid:
                errors.append(f"Task '{tid}' cannot depend on itself.")
            elif dep not in task_map:
                errors.append(f"Task '{tid}' references non-existent dependency '{dep}'.")
            else:
                adj[tid].append(dep)

    # Detect cycles using DFS (3-color algorithm: 0=unvisited, 1=visiting, 2=visited)
    color: Dict[str, int] = {t["id"]: 0 for t in tasks}
    parent: Dict[str, Optional[str]] = {t["id"]: None for t in tasks}
    cycles: List[List[str]] = []

    def dfs(node: str, path: List[str]):
        color[node] = 1
        path.append(node)
        for neighbor in adj.get(node, []):
            if color[neighbor] == 1:
                # Found cycle
                cycle_start = path.index(neighbor)
                cycle_path = path[cycle_start:] + [neighbor]
                cycles.append(cycle_path)
            elif color[neighbor] == 0:
                parent[neighbor] = node
                dfs(neighbor, path)
        path.pop()
        color[node] = 2

    for tid in tasks:
        if color[tid["id"]] == 0:
            dfs(tid["id"], [])

    for c in cycles:
        cycle_str = " -> ".join(c)
        errors.append(f"Circular dependency detected: {cycle_str}")

    # Warn when a declared Wave contradicts the topological position.
    # Declared waves are informational; computed waves govern execution.
    if not errors:
        try:
            _waves = compute_execution_waves(tasks)
            position = {t["id"]: idx + 1 for idx, wave in enumerate(_waves) for t in wave}
            for t in tasks:
                declared = t.get("wave")
                if declared is not None and declared != position.get(t["id"]):
                    warnings.append(
                        f"Task '{t['id']}' declares Wave {declared} but topological "
                        f"order places it in Wave {position.get(t['id'])}."
                    )
        except ValueError:
            pass

    is_valid = len(errors) == 0
    return is_valid, errors, warnings


def compute_execution_waves(tasks: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
    """
    Compute topological execution waves (layers where all dependencies are satisfied by previous waves).
    Wave 1 contains independent tasks.
    NOTE: The declared `Wave` field on each task is informational only and is
    ignored here; computed waves govern execution. Use validate_dag() to flag
    mismatches between declared and topological positions.
    Raises ValueError if task IDs are duplicated or if any task is unresolvable
    (missing dependency or dependency cycle) instead of silently returning
    partial/empty waves.
    @implements REQ-TASK-04
    """
    if not tasks:
        return []

    ids = [t["id"] for t in tasks]
    if len(set(ids)) != len(ids):
        seen: Set[str] = set()
        dups = sorted({tid for tid in ids if tid in seen or seen.add(tid)})
        raise ValueError(f"Cannot compute execution waves: duplicate task IDs {dups}.")

    task_map = {t["id"]: t for t in tasks}

    waves = []
    completed: Set[str] = set()
    remaining = set(task_map.keys())

    while remaining:
        # Find all tasks whose dependencies are fully completed (sorted for determinism)
        current_wave_ids = sorted(
            tid for tid in remaining
            if all(dep in completed for dep in task_map[tid]["dependencies"])
        )

        if not current_wave_ids:
            # Cycle or broken dependency prevented forward progress: fail loudly
            unresolved = sorted(remaining)
            missing = sorted({dep for tid in unresolved
                              for dep in task_map[tid]["dependencies"]
                              if dep not in task_map})
            if missing:
                raise ValueError(
                    f"Cannot compute execution waves: tasks {unresolved} reference "
                    f"non-existent dependencies {missing}."
                )
            raise ValueError(
                f"Cannot compute execution waves: circular or unresolvable "
                f"dependencies among tasks {unresolved}."
            )

        current_wave = [task_map[tid] for tid in current_wave_ids]
        waves.append(current_wave)
        for tid in current_wave_ids:
            completed.add(tid)
            remaining.remove(tid)

    return waves


def generate_waves_markdown(waves: List[List[Dict[str, Any]]]) -> str:
    """Generate Markdown summary table of computed execution waves."""
    lines = [
        "| Wave # | Task ID | Title | Component | Dependencies |",
        "| :--- | :--- | :--- | :--- | :--- |"
    ]
    for w_idx, wave in enumerate(waves, 1):
        for t in wave:
            deps_str = ", ".join(t["dependencies"]) if t["dependencies"] else "None (Independent)"
            lines.append(f"| Wave {w_idx} | `[{t['id']}]` | {t['title']} | {t['component']} | `{deps_str}` |")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Task DAG & Scheduling Engine")
    parser.add_argument("--file", required=True, help="Path to markdown plan file")
    parser.add_argument("--json", action="store_true", help="Output JSON results")
    parser.add_argument("--format-waves", action="store_true", help="Print formatted markdown waves")
    args = parser.parse_args()

    plan_path = Path(args.file)
    if not plan_path.exists():
        print(f"[!] File not found: {plan_path}", file=sys.stderr)
        sys.exit(1)

    content = plan_path.read_text(encoding="utf-8", errors="replace")
    tasks = parse_tasks_from_markdown(content)
    is_valid, errors, warnings = validate_dag(tasks)
    waves = []
    if is_valid:
        try:
            waves = compute_execution_waves(tasks)
        except ValueError as e:
            is_valid = False
            errors = [str(e)]

    if args.json:
        result = {
            "valid": is_valid,
            "task_count": len(tasks),
            "errors": errors,
            "warnings": warnings,
            "waves_count": len(waves),
            "tasks": tasks,
            "waves": [[t["id"] for t in w] for w in waves]
        }
        print(json.dumps(result, indent=2))
        sys.exit(0 if is_valid else 1)

    print(f"=== Task DAG Analysis: {plan_path.name} ===")
    print(f"Total Tasks Parsed: {len(tasks)}")
    for w in warnings:
        print(f"[WARN] {w}")
    if not is_valid:
        print(f"[!] DAG Validation FAILED ({len(errors)} errors):", file=sys.stderr)
        for err in errors:
            print(f"    - {err}", file=sys.stderr)
        sys.exit(1)

    print(f"[✓] DAG is VALID (zero cycles detected).")
    print(f"Computed Execution Waves: {len(waves)}")
    if args.format_waves:
        print("\n" + generate_waves_markdown(waves))
    else:
        for idx, w in enumerate(waves, 1):
            task_ids = ", ".join([f"[{t['id']}]" for t in w])
            print(f"  Wave {idx}: {task_ids}")

    sys.exit(0)


if __name__ == "__main__":
    main()
