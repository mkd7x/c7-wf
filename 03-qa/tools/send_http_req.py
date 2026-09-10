#!/usr/bin/env python3
"""
HTTP Request Helper Tool for Clean Room QA Testing.
Sends HTTP requests, measures latency, and performs automated assertions
on status code, headers, and nested JSON response payloads with audit logging.
@implements REQ-TOOL-HTTP
"""

import sys
import os
import re
import json
import ssl
import time
import argparse
import urllib.request
import urllib.error
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

# Import audit logger
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
import audit_logger


class NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    """urllib handler that surfaces 3xx responses instead of following them."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def build_opener(no_redirect: bool = False, insecure: bool = False,
                 ca_cert: Optional[str] = None) -> "urllib.request.OpenerDirector":
    """Build a urlopen-compatible opener with redirect/TLS policy applied."""
    handlers: list = []
    if no_redirect:
        handlers.append(NoRedirectHandler())
    if ca_cert:
        handlers.append(urllib.request.HTTPSHandler(
            context=ssl.create_default_context(cafile=ca_cert)))
    elif insecure:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        handlers.append(urllib.request.HTTPSHandler(context=ctx))
    if not handlers:
        return urllib.request.build_opener()
    return urllib.request.build_opener(*handlers)


def send_request(
    url: str,
    method: str = "GET",
    headers: Optional[Dict[str, str]] = None,
    data: Optional[str] = None,
    timeout: int = 30,
    no_redirect: bool = False,
    insecure: bool = False,
    ca_cert: Optional[str] = None
) -> Dict[str, Any]:
    """Execute HTTP request and return timing, status, headers, and body."""
    method = method.upper()
    req_headers = headers or {}

    if "User-Agent" not in req_headers:
        req_headers["User-Agent"] = "QA-CleanRoom-Agent/1.0"

    encoded_data = None
    if data is not None:
        if isinstance(data, (dict, list)):
            encoded_data = json.dumps(data).encode("utf-8")
            if "Content-Type" not in req_headers:
                req_headers["Content-Type"] = "application/json"
        else:
            encoded_data = data.encode("utf-8")

    req = urllib.request.Request(
        url=url,
        data=encoded_data,
        headers=req_headers,
        method=method
    )

    start_time = time.time()
    opener = build_opener(no_redirect=no_redirect, insecure=insecure, ca_cert=ca_cert)
    try:
        with opener.open(req, timeout=timeout) as response:
            duration_ms = round((time.time() - start_time) * 1000, 2)
            status_code = response.status
            resp_headers = dict(response.headers)
            body_bytes = response.read()
            body_text = body_bytes.decode("utf-8", errors="replace")

            try:
                json_data = json.loads(body_text)
            except Exception:
                json_data = None

            return {
                "success": True,
                "status_code": status_code,
                "duration_ms": duration_ms,
                "headers": resp_headers,
                "body": body_text,
                "json": json_data,
                "error": None,
                "final_url": response.geturl(),
                "redirected": response.geturl() != url,
            }
    except urllib.error.HTTPError as e:
        duration_ms = round((time.time() - start_time) * 1000, 2)
        body_text = e.read().decode("utf-8", errors="replace")
        try:
            json_data = json.loads(body_text)
        except Exception:
            json_data = None
        location = None
        try:
            location = e.headers.get("Location")
        except Exception:
            location = None
        return {
            "success": False,
            "status_code": e.code,
            "duration_ms": duration_ms,
            "headers": dict(e.headers),
            "body": body_text,
            "json": json_data,
            "error": f"HTTPError: {e.reason}",
            "final_url": getattr(e, "url", url) or url,
            "redirected": False,
            "location": location,
        }
    except Exception as e:
        duration_ms = round((time.time() - start_time) * 1000, 2)
        return {
            "success": False,
            "status_code": 0,
            "duration_ms": duration_ms,
            "headers": {},
            "body": "",
            "json": None,
            "error": str(e),
            "final_url": url,
            "redirected": False,
        }


def resolve_json_path(data: Any, path: str) -> Tuple[bool, Any]:
    """
    Traverse nested JSON using dot and array index notation.
    Supports: 'items[0].title', 'items.length', 'data.user.id'.
    """
    tokens = []
    raw_parts = [p for p in path.split(".") if p]
    for part in raw_parts:
        matches = re.findall(r"([^\[]+)?\[(\d+)\]", part)
        if matches:
            for key, idx in matches:
                if key:
                    tokens.append(key)
                tokens.append(int(idx))
        else:
            tokens.append(part)

    curr = data
    for token in tokens:
        if curr is None:
            return False, None
        if isinstance(token, str) and token == "length":
            if isinstance(curr, (list, dict, str)):
                curr = len(curr)
                continue
            return False, None
        if isinstance(token, int):
            if isinstance(curr, list) and 0 <= token < len(curr):
                curr = curr[token]
            else:
                return False, None
        elif isinstance(curr, dict):
            if token in curr:
                curr = curr[token]
            else:
                return False, None
        else:
            return False, None
    return True, curr


def compare_values(actual: Any, op: str, expected_str: str) -> Tuple[bool, str]:
    """Compare actual value against expected_str using op (=, !=, >=, <=, >, <)."""
    expected_str = expected_str.strip()
    if isinstance(actual, bool):
        if expected_str.lower() in ("true", "false"):
            exp_bool = expected_str.lower() == "true"
            if op == "=":
                return actual == exp_bool, f"expected {exp_bool}"
            if op == "!=":
                return actual != exp_bool, f"expected not {exp_bool}"

    if isinstance(actual, (int, float)):
        try:
            exp_num = float(expected_str) if "." in expected_str else int(expected_str)
            if op == "=":
                return actual == exp_num, f"expected {exp_num}"
            if op == "!=":
                return actual != exp_num, f"expected not {exp_num}"
            if op == ">=":
                return actual >= exp_num, f"expected >= {exp_num}"
            if op == "<=":
                return actual <= exp_num, f"expected <= {exp_num}"
            if op == ">":
                return actual > exp_num, f"expected > {exp_num}"
            if op == "<":
                return actual < exp_num, f"expected < {exp_num}"
        except ValueError:
            pass

    actual_str = str(actual)
    if op == "=":
        return actual_str == expected_str, f"expected '{expected_str}'"
    if op == "!=":
        return actual_str != expected_str, f"expected not '{expected_str}'"
    return False, f"unsupported operator '{op}'"


def check_assertions(
    res: Dict[str, Any],
    expect_status: Optional[List[int]] = None,
    expect_contains: Optional[List[str]] = None,
    expect_json_exprs: Optional[List[str]] = None
) -> List[str]:
    """Evaluate assertions against HTTP response and return list of failure messages."""
    failures = []

    if expect_status:
        if res["status_code"] not in expect_status:
            failures.append(
                f"Expected status {expect_status}, but received {res['status_code']}."
            )

    if expect_contains:
        for needle in expect_contains:
            if needle.lower() not in res["body"].lower():
                failures.append(
                    f"Expected body to contain '{needle}', but string was not found."
                )

    if expect_json_exprs:
        if not res["json"]:
            failures.append("Expected valid JSON response for JSON assertion, but body was not JSON.")
        else:
            for expr in expect_json_exprs:
                expr = expr.strip()
                # Parse operator
                matched_op = None
                for op in (">=", "<=", "!=", "=", ">", "<"):
                    if op in expr:
                        matched_op = op
                        break

                if matched_op:
                    path, expected_val = expr.split(matched_op, 1)
                    path = path.strip()
                    found, actual_val = resolve_json_path(res["json"], path)
                    if not found:
                        failures.append(f"JSON path '{path}' not found in response.")
                    else:
                        matches, reason = compare_values(actual_val, matched_op, expected_val)
                        if not matches:
                            failures.append(f"JSON path '{path}' had value '{actual_val}', {reason}.")
                else:
                    # Existence check
                    found, _ = resolve_json_path(res["json"], expr)
                    if not found:
                        failures.append(f"JSON path '{expr}' not found in response.")

    return failures


def main():
    parser = argparse.ArgumentParser(description="Clean Room HTTP Request & Assertion CLI")
    parser.add_argument("url", help="Target URL (e.g. http://localhost:8000/api/users)")
    parser.add_argument("--method", "-X", default="GET", choices=["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD"], help="HTTP method")
    parser.add_argument("--header", "-H", action="append", help="Request header in 'Key: Value' format")
    parser.add_argument("--data", "-d", help="Request body string or JSON string")
    parser.add_argument("--data-file", "-f", help="File containing request body")
    parser.add_argument("--timeout", type=int, default=30, help="Timeout in seconds")
    parser.add_argument("--expect-status", "-s", help="Comma-separated expected status codes (e.g. '200,201')")
    parser.add_argument("--expect-contains", action="append", help="Assert that response body contains string")
    parser.add_argument("--expect-json", action="append", help="Assert JSON path (e.g. 'id=3', 'items[0].title=foo', 'items.length>=1')")
    parser.add_argument("--save", help="Save response body to specified file path")
    parser.add_argument("--no-redirect", action="store_true",
                        help="Do not follow HTTP redirects; assert the 3xx response directly")
    parser.add_argument("--insecure", action="store_true",
                        help="Skip TLS certificate verification (self-signed dev certs)")
    parser.add_argument("--ca-cert", help="Path to a custom CA bundle for TLS verification")
    parser.add_argument("--step-id", help="Logical identifier for workflow step audit logging (e.g. 'step-05-create-list')")
    parser.add_argument("--audit-file", help="Custom path to audit.jsonl log file")
    parser.add_argument("--verbose", "-v", action="store_true", help="Print request and response headers")

    args = parser.parse_args()

    # Parse headers
    headers = {}
    if args.header:
        for h in args.header:
            if ":" in h:
                k, v = h.split(":", 1)
                headers[k.strip()] = v.strip()

    # Parse body
    data = args.data
    if args.data_file:
        try:
            with open(args.data_file, "r", encoding="utf-8") as f:
                data = f.read()
        except Exception as e:
            print(f"[!] Error reading data-file: {e}", file=sys.stderr)
            sys.exit(1)

    expected_statuses = [int(s.strip()) for s in args.expect_status.split(",")] if args.expect_status else None

    if args.ca_cert and args.insecure:
        print("[!] --ca-cert and --insecure are mutually exclusive.", file=sys.stderr)
        sys.exit(1)

    # Execute request
    res = send_request(
        url=args.url,
        method=args.method,
        headers=headers,
        data=data,
        timeout=args.timeout,
        no_redirect=args.no_redirect,
        insecure=args.insecure,
        ca_cert=args.ca_cert
    )

    if args.verbose:
        print(f">>> {args.method} {args.url}")
        for k, v in headers.items():
            print(f">>> {k}: {v}")
        if data:
            print(f">>> Body: {data[:200]}...")
        print("---")
        print(f"<<< Status: {res['status_code']} ({res['duration_ms']}ms)")
        for k, v in res["headers"].items():
            print(f"<<< {k}: {v}")
        print("---")

    # Evaluate assertions
    failures = check_assertions(
        res=res,
        expect_status=expected_statuses,
        expect_contains=args.expect_contains,
        expect_json_exprs=args.expect_json
    )

    if args.save and res["body"]:
        try:
            with open(args.save, "w", encoding="utf-8") as f:
                f.write(res["body"])
            print(f"[✓] Saved response to {args.save}")
        except Exception as e:
            print(f"[!] Failed to save response to {args.save}: {e}")

    # Output body
    if res["body"]:
        if res["json"]:
            print(json.dumps(res["json"], indent=2))
        else:
            print(res["body"].strip())

    # Record to live audit log.
    # A non-2xx response is only a failure when it was unexpected (assertions failed) or when the
    # step declared no expectations at all. This keeps intentional 4xx/5xx regression checks PASS.
    assertions_provided = bool(expected_statuses or args.expect_contains or args.expect_json)
    step_status = "FAIL" if failures or (not assertions_provided and not res["success"]) else "PASS"
    audit_logger.record_step(
        tool="send_http_req",
        step_id=args.step_id,
        input_data={
            "url": args.url,
            "method": args.method,
            "headers": headers,
            "data": data,
            "no_redirect": args.no_redirect,
        },
        output_data={
            "status_code": res["status_code"],
            "duration_ms": res["duration_ms"],
            "headers": res["headers"],
            "body": res["json"] if res["json"] is not None else res["body"],
            "final_url": res.get("final_url"),
            "redirected": res.get("redirected", False),
            "location": res.get("location") or res["headers"].get("Location") or res["headers"].get("location"),
        },
        assertions={
            "expected_status": expected_statuses,
            "expected_contains": args.expect_contains,
            "expected_json": args.expect_json,
            "passed": len(failures) == 0,
            "failures": failures
        },
        duration_ms=res["duration_ms"],
        status=step_status,
        custom_audit_path=args.audit_file
    )

    if failures:
        print("\n[!] HTTP Assertions FAILED:", file=sys.stderr)
        for fail in failures:
            print(f"  - {fail}", file=sys.stderr)
        sys.exit(1)
    else:
        if args.expect_status or args.expect_contains or args.expect_json:
            print(f"\n[✓] All assertions passed ({res['status_code']} in {res['duration_ms']}ms)")
        sys.exit(0)


if __name__ == "__main__":
    main()
