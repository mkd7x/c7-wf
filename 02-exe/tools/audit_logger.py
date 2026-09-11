#!/usr/bin/env python3
"""
Live Audit & Step Output Logger for 02-exe.
Provides structured recording of task execution, dev steps, and inner-loop test outcomes
into an append-only JSONL audit log and an indexed execution state file, with built-in
in-memory secret redaction.

@implements REQ-ENV-04
@implements REQ-DEV-04
"""

import os
import sys
import json
import time
import shutil
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List, Set

RUNS_ROOT = Path(__file__).resolve().parent.parent / "runs"
DEFAULT_RUNS_DIR = RUNS_ROOT / "latest"

# Name of env var overriding the persistent redaction registry location
# (used by tests to isolate cross-process secret persistence).
REDACT_REGISTRY_ENV_VAR = "EXE_SECRET_REGISTRY_FILE"

# In-memory secret registry for log redaction
_SECRET_REGISTRY: Set[str] = set()

# mtime of the persisted registry file at last load; used to detect
# secrets registered by other processes without re-reading on every call.
_registry_mtime: Optional[float] = None


def _redact_registry_path() -> Path:
    """Resolve the persistent cross-process redaction registry file.

    The file holds plaintext secrets with 0600 permissions inside the
    gitignored runs/ directory (alongside .env-style local artifacts).
    """
    env_path = os.environ.get(REDACT_REGISTRY_ENV_VAR)
    if env_path:
        p = Path(env_path).expanduser()
        p.parent.mkdir(parents=True, exist_ok=True)
        return p
    DEFAULT_RUNS_DIR.mkdir(parents=True, exist_ok=True)
    return DEFAULT_RUNS_DIR / ".secret_registry.json"


def _load_persisted_secrets() -> None:
    """Merge secrets registered by other processes into the in-memory set."""
    global _registry_mtime
    path = _redact_registry_path()
    try:
        mtime = path.stat().st_mtime
    except OSError:
        return
    if _registry_mtime is not None and mtime <= _registry_mtime:
        return
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, list):
            for s in data:
                if isinstance(s, str) and len(s.strip()) >= 3:
                    _SECRET_REGISTRY.add(s.strip())
        _registry_mtime = mtime
    except Exception:
        pass


def _persist_secret(secret_value: str) -> None:
    """Append a secret to the 0600 registry file for cross-process masking."""
    global _registry_mtime
    secret = secret_value.strip()
    if len(secret) < 3 or len(secret) > 4096:
        return
    path = _redact_registry_path()
    try:
        existing: List[str] = []
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(data, list):
                    existing = [s for s in data if isinstance(s, str)]
            except Exception:
                existing = []
        if secret not in existing:
            existing.append(secret)
            existing = existing[-500:]  # cap registry size
            tmp = path.with_suffix(".tmp")
            tmp.write_text(json.dumps(existing), encoding="utf-8")
            os.chmod(tmp, 0o600)
            os.replace(tmp, path)
            try:
                os.chmod(path, 0o600)
            except OSError:
                pass
        _registry_mtime = path.stat().st_mtime
    except Exception:
        pass


def register_secret(secret_value: str) -> None:
    """Register a secret string for automatic redaction in logs and output."""
    if secret_value and len(secret_value.strip()) >= 3:
        _SECRET_REGISTRY.add(secret_value.strip())
        # Persist so later CLI processes mask this value too (REQ-ENV-04).
        _persist_secret(secret_value)


def register_secrets(secret_values: List[str]) -> None:
    """Register multiple secrets for automatic redaction."""
    for s in secret_values:
        register_secret(s)


def redact_text(text: str) -> str:
    """Mask all registered secrets within the given string."""
    _load_persisted_secrets()
    if not text or not _SECRET_REGISTRY:
        return text
    redacted = text
    # Longest secrets first so overlapping values mask correctly.
    for secret in sorted(_SECRET_REGISTRY, key=len, reverse=True):
        if secret in redacted:
            redacted = redacted.replace(secret, "***REDACTED***")
    return redacted


def redact_object(obj: Any) -> Any:
    """Recursively redact secrets from dictionary/list structures."""
    if isinstance(obj, str):
        return redact_text(obj)
    elif isinstance(obj, dict):
        return {k: redact_object(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [redact_object(elem) for elem in obj]
    return obj


def _utc_now():
    return datetime.now(timezone.utc)


def _new_run_id(now=None) -> str:
    ts = (now or _utc_now()).strftime("%Y%m%d_%H%M%S")
    return f"run-{ts}"


def get_audit_file_path(custom_path: Optional[str] = None) -> Path:
    """Resolve target audit.jsonl file path from argument, env, or default."""
    if custom_path:
        p = Path(custom_path).expanduser().resolve()
        p.parent.mkdir(parents=True, exist_ok=True)
        return p
    env_path = os.environ.get("EXE_AUDIT_LOG")
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
    Ensures in-memory secret masking is applied to all input and output fields.
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
        "input": redact_object(input_data),
        "output": redact_object(output_data),
        "assertions": redact_object(assertions)
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


def clear_secret_registry() -> None:
    """Clear the in-memory registry and the persisted cross-process file.

    Intended for tests and explicit resets (01-plan-style teardown).
    """
    global _registry_mtime
    _SECRET_REGISTRY.clear()
    path = _redact_registry_path()
    try:
        if path.exists():
            path.unlink()
    except OSError:
        pass
    _registry_mtime = None
