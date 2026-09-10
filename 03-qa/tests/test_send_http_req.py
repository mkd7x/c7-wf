#!/usr/bin/env python3
"""Regression tests for the send_http_req audit verdict (QAF-002).

Run from 03-qa/:  python3 tests/test_send_http_req.py
"""
import http.server
import json
import socketserver
import subprocess
import sys
import tempfile
import threading
from pathlib import Path

QA_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(QA_DIR / "tools"))
import audit_logger  # noqa: E402


class Handler(http.server.BaseHTTPRequestHandler):
    def _send(self, code, payload):
        body = json.dumps(payload).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/ok":
            self._send(200, {"status": "ok"})
        elif self.path == "/missing":
            self._send(404, {"status": 404, "title": "Resource Not Found"})
        elif self.path == "/boom":
            self._send(500, {"error": "boom"})
        elif self.path == "/redir":
            self.send_response(302)
            self.send_header("Location", "/ok")
            self.end_headers()
        else:
            self._send(404, {"error": "unknown"})

    def log_message(self, format, *args):  # noqa: A002 - stdlib signature
        pass


def run_tool(url, *extra, audit_file):
    cmd = [sys.executable, str(QA_DIR / "tools" / "send_http_req.py"), url,
           "--audit-file", str(audit_file), *extra]
    return subprocess.run(cmd, capture_output=True, text=True)


def audit_status(audit_file):
    records = audit_logger.read_audit_log(custom_audit_path=str(audit_file))
    assert records, "expected an audit record"
    return records[-1]


def check(name, cond, detail=""):
    print(f"[{'PASS' if cond else 'FAIL'}] {name}" + (f" — {detail}" if detail and not cond else ""))
    if not cond:
        state["failed"] += 1


state = {"failed": 0}

with tempfile.TemporaryDirectory() as tmp:
    audit = Path(tmp) / "audit.jsonl"
    with socketserver.TCPServer(("127.0.0.1", 0), Handler) as srv:
        port = srv.server_address[1]
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        base = f"http://127.0.0.1:{port}"

        # 1. Expected 4xx must be audit PASS + exit 0 (QAF-002 core case).
        r = run_tool(f"{base}/missing", "--expect-status", "404", audit_file=audit)
        rec = audit_status(audit)
        check("expected 404 exits 0", r.returncode == 0, r.stderr[-500:])
        check("expected 404 audits PASS", rec["status"] == "PASS", str(rec["status"]))

        # 2. Unexpected 4xx (no assertions) must still be audit FAIL.
        r = run_tool(f"{base}/missing", audit_file=audit)
        rec = audit_status(audit)
        check("undeclared 404 audits FAIL", rec["status"] == "FAIL", str(rec["status"]))

        # 3. Mismatched expectation must fail both exit and audit.
        r = run_tool(f"{base}/missing", "--expect-status", "200", audit_file=audit)
        rec = audit_status(audit)
        check("wrong expectation exits 1", r.returncode == 1, str(r.returncode))
        check("wrong expectation audits FAIL", rec["status"] == "FAIL", str(rec["status"]))

        # 4. Expected 5xx must be audit PASS + exit 0.
        r = run_tool(f"{base}/boom", "--expect-status", "500", audit_file=audit)
        rec = audit_status(audit)
        check("expected 500 exits 0", r.returncode == 0, r.stderr[-500:])
        check("expected 500 audits PASS", rec["status"] == "PASS", str(rec["status"]))

        # 5. Plain 200 stays PASS.
        r = run_tool(f"{base}/ok", "--expect-status", "200", audit_file=audit)
        rec = audit_status(audit)
        check("expected 200 exits 0", r.returncode == 0, r.stderr[-500:])
        check("expected 200 audits PASS", rec["status"] == "PASS", str(rec["status"]))

        # 6. --no-redirect surfaces the 3xx for assertion (QAF-009).
        r = run_tool(f"{base}/redir", "--expect-status", "302", "--no-redirect", audit_file=audit)
        rec = audit_status(audit)
        loc = rec["output"].get("location")
        check("no-redirect 302 exits 0", r.returncode == 0, r.stderr[-500:])
        check("no-redirect records Location", loc == "/ok", str(loc))

        # 7. Default follows redirects to 200 (documents preserved behavior).
        r = run_tool(f"{base}/redir", "--expect-status", "200", audit_file=audit)
        rec = audit_status(audit)
        check("follow-redirect 200 exits 0", r.returncode == 0, r.stderr[-500:])
        check("follow-redirect marks redirected", rec["output"].get("redirected") is True,
              str(rec["output"].get("redirected")))

        srv.shutdown()

if state["failed"]:
    print(f"\n{state['failed']} check(s) FAILED")
    sys.exit(1)
print("\nAll send_http_req regression checks passed.")
