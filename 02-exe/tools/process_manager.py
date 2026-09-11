#!/usr/bin/env python3
"""
Process Manager & Supervisor for 02-exe.
Handles launching background dev servers, health readiness polling (HTTP/TCP),
process state tracking, and generating/executing shell cleanup traps.

@implements REQ-WORK-03
@implements REQ-DEV-02
"""

import os
import sys
import time
import socket
import urllib.request
import urllib.error
import subprocess
import signal
import argparse
from pathlib import Path
from typing import Optional, Dict, Any

RUNS_DIR = Path(__file__).resolve().parent.parent / "runs" / "latest"

# Keep Popen handles alive so detached children are not GC'd while running
# (avoids "subprocess still running" ResourceWarnings and zombie reaps).
_PROCESSES: Dict[str, "subprocess.Popen[bytes]"] = {}


def is_port_open(host: str, port: int, timeout: float = 1.0) -> bool:
    """Check if a TCP port is responding."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except (socket.timeout, ConnectionRefusedError, OSError):
        return False


def poll_http_url(url: str, expected_status: int = 200, timeout_seconds: float = 30.0, interval: float = 1.0) -> bool:
    """Poll an HTTP health endpoint until it returns expected status or times out."""
    start_time = time.time()
    while time.time() - start_time < timeout_seconds:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "02-exe-ProcessManager/1.0"})
            with urllib.request.urlopen(req, timeout=2.0) as resp:
                if resp.status == expected_status:
                    return True
        except (urllib.error.HTTPError, urllib.error.URLError, socket.timeout, ConnectionRefusedError):
            pass
        time.sleep(interval)
    return False


def start_background_process(
    cmd: str,
    name: str = "dev-server",
    cwd: Optional[Path] = None,
    log_file: Optional[Path] = None
) -> Dict[str, Any]:
    """
    Launch command in background detached, redirecting stdout/stderr to a log file.
    Saves pid file in runs/latest/<name>.pid.

    Any previously tracked process under the same *name* is stopped first so
    a stale pid file can never orphan a running server.
    """
    stop_process(name)
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    out_log = log_file or (RUNS_DIR / f"{name}.log")
    pid_file = RUNS_DIR / f"{name}.pid"

    with open(out_log, "w", encoding="utf-8") as log_handle:
        proc = subprocess.Popen(
            cmd,
            shell=True,
            cwd=cwd,
            stdout=log_handle,
            stderr=subprocess.STDOUT,
            preexec_fn=os.setsid if hasattr(os, "setsid") else None
        )

    # Retain the handle (keyed by name) so the child is not garbage-collected
    # while running and can be reaped deterministically in stop_process.
    _PROCESSES[name] = proc
    pid_file.write_text(str(proc.pid), encoding="utf-8")
    return {
        "name": name,
        "pid": proc.pid,
        "log_file": str(out_log),
        "pid_file": str(pid_file),
        "status": "STARTED"
    }


def _reap(name: str, pid: int) -> None:
    """Reap a tracked child handle (if ours) without blocking."""
    proc = _PROCESSES.pop(name, None)
    if proc is not None and proc.pid == pid:
        try:
            proc.wait(timeout=0)
        except Exception:
            pass
    else:
        try:
            os.waitpid(pid, os.WNOHANG)
        except Exception:
            pass


def _process_alive(pid: int) -> bool:
    """Return True if a process with *pid* still exists (portable)."""
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False
    return True


def stop_process(name: str = "dev-server", sigkill_after_seconds: float = 2.0) -> bool:
    """Stop a background process previously registered via name or PID file.

    Sends SIGTERM to the process group (or PID on platforms without
    process groups), polls briefly for exit, then escalates to SIGKILL so
    shell-spawned grandchildren (`shell=True`) cannot linger.
    """
    pid_file = RUNS_DIR / f"{name}.pid"
    if not pid_file.exists():
        return False

    try:
        pid = int(pid_file.read_text(encoding="utf-8").strip())
    except (ValueError, OSError):
        try:
            pid_file.unlink()
        except OSError:
            pass
        return False

    def _signal_group(sig: int) -> None:
        if hasattr(os, "killpg"):
            try:
                os.killpg(os.getpgid(pid), sig)
                return
            except (ProcessLookupError, PermissionError, OSError):
                pass
        try:
            os.kill(pid, sig)
        except (ProcessLookupError, PermissionError, OSError):
            pass

    try:
        if not _process_alive(pid):
            _reap(name, pid)
            try:
                if pid_file.exists():
                    try:
                        if int(pid_file.read_text(encoding="utf-8").strip()) == pid:
                            pid_file.unlink()
                    except (ValueError, OSError):
                        pass
            except OSError:
                pass
            return True
        _signal_group(signal.SIGTERM)
        deadline = time.time() + max(sigkill_after_seconds, 0.2)
        while time.time() < deadline:
            if not _process_alive(pid):
                break
            time.sleep(0.1)
        else:
            # Escalate: SIGTERM was not enough (e.g. shell children).
            _signal_group(signal.SIGKILL)
            kill_deadline = time.time() + 2.0
            while time.time() < kill_deadline:
                if not _process_alive(pid):
                    break
                time.sleep(0.1)
        try:
            os.waitpid(pid, os.WNOHANG)
        except Exception:
            pass
        _reap(name, pid)
        if _process_alive(pid):
            # Could not terminate; keep the pid file so the leak is visible.
            return False
        try:
            if pid_file.exists():
                # Guard against a racing start() that reused this name.
                try:
                    if int(pid_file.read_text(encoding="utf-8").strip()) == pid:
                        pid_file.unlink()
                except (ValueError, OSError):
                    pass
        except OSError:
            pass
        return True
    finally:
        _reap(name, pid)


def generate_shell_trap(process_names: Optional[list] = None, docker_filters: Optional[list] = None) -> str:
    """
    Generate a robust bash/zsh cleanup trap command.
    """
    procs = process_names or ["dev-server"]
    kill_cmds = [f"python3 tools/process_manager.py stop --name {p} 2>/dev/null" for p in procs]

    docker_cmds = []
    if docker_filters:
        for flt in docker_filters:
            docker_cmds.append(f"docker stop $(docker ps -q --filter '{flt}') 2>/dev/null")

    all_cmds = " ; ".join(kill_cmds + docker_cmds)
    return f"trap '{all_cmds}' EXIT INT TERM"


def main():
    parser = argparse.ArgumentParser(description="02-exe Process Manager")
    subparsers = parser.add_subparsers(dest="action", required=True)

    # start
    start_p = subparsers.add_parser("start", help="Start background dev service")
    start_p.add_argument("--cmd", required=True, help="Command to execute")
    start_p.add_argument("--name", default="dev-server", help="Process name")
    start_p.add_argument("--cwd", default="workspace", help="Working directory")

    # stop
    stop_p = subparsers.add_parser("stop", help="Stop background service")
    stop_p.add_argument("--name", default="dev-server", help="Process name")

    # wait-ready
    wait_p = subparsers.add_parser("wait-ready", help="Poll readiness")
    wait_p.add_argument("--url", help="HTTP readiness URL")
    wait_p.add_argument("--tcp", type=int, help="TCP port number")
    wait_p.add_argument("--host", default="127.0.0.1", help="Host for TCP check")
    wait_p.add_argument("--timeout", type=float, default=30.0, help="Timeout in seconds")
    wait_p.add_argument("--expect-status", type=int, default=200, help="Expected HTTP status")

    # generate-trap
    trap_p = subparsers.add_parser("generate-trap", help="Generate shell cleanup trap")
    trap_p.add_argument("--name", default="dev-server", help="Process name")

    args = parser.parse_args()

    if args.action == "start":
        res = start_background_process(args.cmd, name=args.name, cwd=Path(args.cwd).resolve())
        print(f"[✓] Started '{args.name}' (PID {res['pid']}). Logs: {res['log_file']}")
        sys.exit(0)

    elif args.action == "stop":
        ok = stop_process(args.name)
        if ok:
            print(f"[✓] Stopped '{args.name}'.")
        else:
            print(f"[*] No running process found for '{args.name}'.")
        sys.exit(0)

    elif args.action == "wait-ready":
        if args.url:
            print(f"[*] Polling HTTP URL {args.url} (timeout {args.timeout}s)...")
            ok = poll_http_url(args.url, expected_status=args.expect_status, timeout_seconds=args.timeout)
        elif args.tcp:
            print(f"[*] Polling TCP port {args.host}:{args.tcp} (timeout {args.timeout}s)...")
            start = time.time()
            ok = False
            while time.time() - start < args.timeout:
                if is_port_open(args.host, args.tcp):
                    ok = True
                    break
                time.sleep(0.5)
        else:
            print("[!] Must specify either --url or --tcp", file=sys.stderr)
            sys.exit(1)

        if ok:
            print(f"[✓] Service is READY and responsive.")
            sys.exit(0)
        else:
            print(f"[!] Timed out waiting for service readiness.", file=sys.stderr)
            sys.exit(1)

    elif args.action == "generate-trap":
        trap_cmd = generate_shell_trap([args.name])
        print(trap_cmd)
        sys.exit(0)


if __name__ == "__main__":
    main()
