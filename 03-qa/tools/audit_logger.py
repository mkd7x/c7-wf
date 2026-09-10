#!/usr/bin/env python3
"""
Live Audit & Step Output Logger for Clean Room QA Testing.
Provides structured recording of every test step's input, execution, output,
timings, and assertion results into an append-only JSONL audit log and an
indexed execution state file.
"""

import os
import sys
import json
import time
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List

DEFAULT_RUNS_DIR = Path(__file__).resolve().parent.parent / "runs" / "latest"


def get_audit_file_path(custom_path: Optional[str] = None) -> Path:
    """Resolve target audit.jsonl file path from argument, env, or default."""
    if custom_path:
        p = Path(custom_path).expanduser().resolve()
        p.parent.mkdir(parents=True, exist_ok=True)
        return p
    env_path = os.environ.get("QA_AUDIT_LOG")
    if env_path:
        p = Path(env_path).expanduser().resolve()
        p.parent.mkdir(parents=True, exist_ok=True)
        return p
    DEFAULT_RUNS_DIR.mkdir(parents=True, exist_ok=True)
    return DEFAULT_RUNS_DIR / "audit.jsonl"


def get_state_file_path(audit_path: Path) -> Path:
    """Return path to the companion step-state JSON file."""
    return audit_path.parent / "execution_state.json"


def record_step(
    tool: str,
    step_id: Optional[str],
    input_data: Dict[str, Any],
    output_data: Dict[str, Any],
    assertions: Dict[str, Any],
    duration_ms: float,
    status: str = "PASS",
    custom_audit_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Append step record to audit.jsonl and update execution_state.json.
    """
    audit_file = get_audit_file_path(custom_audit_path)
    state_file = get_state_file_path(audit_file)

    now_iso = datetime.now(timezone.utc).isoformat()
    record = {
        "timestamp": now_iso,
        "step_id": step_id or f"step_{int(time.time() * 1000)}",
        "tool": tool,
        "status": status,
        "duration_ms": duration_ms,
        "input": input_data,
        "output": output_data,
        "assertions": assertions
    }

    # Append to audit.jsonl
    with open(audit_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")

    # Update execution_state.json if step_id provided
    if step_id:
        current_state = {}
        if state_file.exists():
            try:
                with open(state_file, "r", encoding="utf-8") as f:
                    current_state = json.load(f)
            except Exception:
                current_state = {}
        current_state[step_id] = record
        with open(state_file, "w", encoding="utf-8") as f:
            json.dump(current_state, f, indent=2)

    return record


def get_step_output(step_id: str, custom_audit_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Retrieve output record for a specific step_id from state file or audit log."""
    audit_file = get_audit_file_path(custom_audit_path)
    state_file = get_state_file_path(audit_file)

    if state_file.exists():
        try:
            with open(state_file, "r", encoding="utf-8") as f:
                state = json.load(f)
                if step_id in state:
                    return state[step_id]
        except Exception:
            pass

    # Fallback: scan audit.jsonl in reverse
    if audit_file.exists():
        with open(audit_file, "r", encoding="utf-8") as f:
            lines = f.readlines()
            for line in reversed(lines):
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                    if rec.get("step_id") == step_id:
                        return rec
                except Exception:
                    continue
    return None


def read_audit_log(custom_audit_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """Read all records from audit.jsonl."""
    audit_file = get_audit_file_path(custom_audit_path)
    records = []
    if audit_file.exists():
        with open(audit_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        records.append(json.loads(line))
                    except Exception:
                        pass
    return records


def clear_audit(custom_audit_path: Optional[str] = None) -> None:
    """Reset audit log and state file."""
    audit_file = get_audit_file_path(custom_audit_path)
    state_file = get_state_file_path(audit_file)
    if audit_file.exists():
        audit_file.unlink()
    if state_file.exists():
        state_file.unlink()
