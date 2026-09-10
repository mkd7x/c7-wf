#!/usr/bin/env python3
"""
Service Readiness & Health Polling Tool for Clean Room QA Testing.
Polls an HTTP endpoint or TCP port until the service becomes ready before
executing test workflows, with structured audit logging.
@implements REQ-TOOL-WAIT
"""

import sys
import ssl
import time
import socket
import argparse
import urllib.request
import urllib.error
from pathlib import Path
from typing import Optional

# Import audit logger
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
import audit_logger


def wait_for_tcp(host: str, port: int, timeout: int, interval: float) -> bool:
    """Poll TCP socket until connection succeeds or timeout is reached."""
    start_time = time.time()
    print(f"[*] Waiting for TCP {host}:{port} (Timeout: {timeout}s)...")
    while time.time() - start_time < timeout:
        try:
            with socket.create_connection((host, port), timeout=interval):
                elapsed = round(time.time() - start_time, 2)
                print(f"[✓] TCP {host}:{port} is reachable after {elapsed}s.")
                return True
        except (socket.timeout, ConnectionRefusedError, OSError):
            time.sleep(interval)

    print(f"[!] Timeout reached waiting for TCP {host}:{port}.", file=sys.stderr)
    return False


def build_ssl_context(insecure: bool = False, ca_cert: Optional[str] = None) -> Optional["ssl.SSLContext"]:
    """Build a TLS context for health polling.

    Default verifies certificates; --insecure trusts self-signed dev certs
    (Aspire dashboard, local mkcert); --ca-cert pins a custom CA bundle.
    """
    if ca_cert:
        ctx = ssl.create_default_context(cafile=ca_cert)
        return ctx
    if insecure:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        return ctx
    return None


def wait_for_http(url: str, expected_status: int, timeout: int, interval: float,
                  insecure: bool = False, ca_cert: Optional[str] = None) -> bool:
    """Poll HTTP endpoint until expected status code is returned or timeout."""
    start_time = time.time()
    print(f"[*] Polling {url} for status {expected_status} (Timeout: {timeout}s)...")
    context = build_ssl_context(insecure=insecure, ca_cert=ca_cert)
    while time.time() - start_time < timeout:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "QA-HealthCheck/1.0"})
            open_kwargs: dict = {"timeout": interval}
            if context is not None:
                open_kwargs["context"] = context
            with urllib.request.urlopen(req, **open_kwargs) as resp:  # type: ignore[arg-type]
                if resp.status == expected_status:
                    elapsed = round(time.time() - start_time, 2)
                    print(f"[✓] Endpoint {url} is healthy (HTTP {resp.status}) after {elapsed}s.")
                    return True
        except urllib.error.HTTPError as e:
            if e.code == expected_status:
                elapsed = round(time.time() - start_time, 2)
                print(f"[✓] Endpoint {url} responded with expected HTTP {e.code} after {elapsed}s.")
                return True
            time.sleep(interval)
        except Exception:
            time.sleep(interval)

    print(f"[!] Timeout reached polling {url}.", file=sys.stderr)
    return False


def main():
    parser = argparse.ArgumentParser(description="Service Readiness Polling CLI")
    parser.add_argument("--url", "-u", help="HTTP(S) health URL to poll")
    parser.add_argument("--tcp", "-t", help="TCP target in host:port format")
    parser.add_argument("--expect-status", "-s", type=int, default=200, help="Expected HTTP status (default: 200)")
    parser.add_argument("--timeout", type=int, default=60, help="Maximum seconds to wait (default: 60)")
    parser.add_argument("--interval", type=float, default=1.0, help="Seconds between attempts (default: 1.0)")
    parser.add_argument("--insecure", action="store_true",
                        help="Skip TLS certificate verification (self-signed dev certs, e.g. Aspire dashboard)")
    parser.add_argument("--ca-cert", help="Path to a custom CA bundle for TLS verification")
    parser.add_argument("--step-id", help="Logical identifier for workflow step audit logging")
    parser.add_argument("--audit-file", help="Custom path to audit.jsonl log file")

    args = parser.parse_args()

    if not args.url and not args.tcp:
        print("[!] Specify either --url or --tcp to wait for.", file=sys.stderr)
        sys.exit(1)

    start_time = time.time()
    ok = False
    target_desc = ""

    if args.tcp:
        if ":" not in args.tcp:
            print("[!] TCP format must be host:port (e.g. 127.0.0.1:8080)", file=sys.stderr)
            sys.exit(1)
        host, port_s = args.tcp.split(":", 1)
        target_desc = f"tcp://{host}:{port_s}"
        ok = wait_for_tcp(host, int(port_s), timeout=args.timeout, interval=args.interval)

    elif args.url:
        target_desc = args.url
        if args.ca_cert and args.insecure:
            print("[!] --ca-cert and --insecure are mutually exclusive.", file=sys.stderr)
            sys.exit(1)
        ok = wait_for_http(args.url, expected_status=args.expect_status, timeout=args.timeout,
                           interval=args.interval, insecure=args.insecure, ca_cert=args.ca_cert)

    duration_ms = round((time.time() - start_time) * 1000, 2)
    step_status = "PASS" if ok else "FAIL"

    audit_logger.record_step(
        tool="wait_for_service",
        step_id=args.step_id,
        input_data={
            "target": target_desc,
            "expected_status": args.expect_status if args.url else None,
            "timeout": args.timeout,
            "insecure": args.insecure if args.url else None,
            "ca_cert": args.ca_cert if args.url else None,
        },
        output_data={
            "reachable": ok,
            "duration_ms": duration_ms
        },
        assertions={
            "expected_reachable": True,
            "passed": ok,
            "failures": [] if ok else [f"Failed to reach {target_desc} within {args.timeout}s"]
        },
        duration_ms=duration_ms,
        status=step_status,
        custom_audit_path=args.audit_file
    )

    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
