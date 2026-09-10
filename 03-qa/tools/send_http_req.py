#!/usr/bin/env python3
"""
HTTP Request Helper Tool for Clean Room QA Testing.
Sends HTTP requests, measures latency, and performs automated assertions
on status code, headers, and response payloads.
@implements REQ-TOOL-HTTP
"""

import sys
import json
import time
import argparse
import urllib.request
import urllib.error
from typing import Dict, List, Optional, Any


def send_request(
    url: str,
    method: str = "GET",
    headers: Optional[Dict[str, str]] = None,
    data: Optional[str] = None,
    timeout: int = 30
) -> Dict[str, Any]:
    """Execute HTTP request and return timing, status, headers, and body."""
    method = method.upper()
    req_headers = headers or {}

    # Default User-Agent if not provided
    if "User-Agent" not in req_headers:
        req_headers["User-Agent"] = "QA-CleanRoom-Agent/1.0"

    encoded_data = None
    if data is not None:
        if isinstance(data, dict) or isinstance(data, list):
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
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            duration_ms = round((time.time() - start_time) * 1000, 2)
            status_code = response.status
            resp_headers = dict(response.headers)
            body_bytes = response.read()
            body_text = body_bytes.decode("utf-8", errors="replace")

            # Try parsing JSON body
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
                "error": None
            }
    except urllib.error.HTTPError as e:
        duration_ms = round((time.time() - start_time) * 1000, 2)
        body_text = e.read().decode("utf-8", errors="replace")
        try:
            json_data = json.loads(body_text)
        except Exception:
            json_data = None
        return {
            "success": False,
            "status_code": e.code,
            "duration_ms": duration_ms,
            "headers": dict(e.headers),
            "body": body_text,
            "json": json_data,
            "error": f"HTTPError: {e.reason}"
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
            "error": str(e)
        }


def check_assertions(
    res: Dict[str, Any],
    expect_status: Optional[List[int]] = None,
    expect_contains: Optional[List[str]] = None,
    expect_json_keys: Optional[List[str]] = None
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
            if needle not in res["body"]:
                failures.append(
                    f"Expected body to contain '{needle}', but string was not found."
                )

    if expect_json_keys:
        if not res["json"]:
            failures.append("Expected valid JSON response for JSON key assertion, but body was not JSON.")
        else:
            for expr in expect_json_keys:
                if "=" in expr:
                    key, expected_val = expr.split("=", 1)
                    actual_raw = res["json"].get(key.strip())
                    actual_val = str(actual_raw)
                    expected_str = expected_val.strip()
                    if isinstance(actual_raw, bool):
                        matches = actual_val.lower() == expected_str.lower()
                    else:
                        matches = actual_val == expected_str
                    if not matches:
                        failures.append(
                            f"JSON key '{key}' had value '{actual_val}', expected '{expected_val}'."
                        )
                else:
                    if expr.strip() not in res["json"]:
                        failures.append(f"JSON key '{expr}' not found in response.")

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
    parser.add_argument("--expect-json", action="append", help="Assert JSON property (e.g. 'status=ok' or 'id')")
    parser.add_argument("--save", help="Save response body to specified file path")
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

    # Execute request
    res = send_request(
        url=args.url,
        method=args.method,
        headers=headers,
        data=data,
        timeout=args.timeout
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
        expect_json_keys=args.expect_json
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
