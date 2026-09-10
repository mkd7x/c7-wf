#!/usr/bin/env python3
"""
Service Readiness & Health Polling Tool for Clean Room QA Testing.
Polls an HTTP endpoint or TCP port until the service becomes ready before
executing test workflows.
@implements REQ-TOOL-WAIT
"""

import sys
import time
import socket
import argparse
import urllib.request
import urllib.error


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


def wait_for_http(url: str, expected_status: int, timeout: int, interval: float) -> bool:
    """Poll HTTP endpoint until expected status code is returned or timeout."""
    start_time = time.time()
    print(f"[*] Polling {url} for status {expected_status} (Timeout: {timeout}s)...")
    while time.time() - start_time < timeout:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "QA-HealthCheck/1.0"})
            with urllib.request.urlopen(req, timeout=interval) as resp:
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

    args = parser.parse_args()

    if not args.url and not args.tcp:
        print("[!] Specify either --url or --tcp to wait for.", file=sys.stderr)
        sys.exit(1)

    if args.tcp:
        if ":" not in args.tcp:
            print("[!] TCP format must be host:port (e.g. 127.0.0.1:8080)", file=sys.stderr)
            sys.exit(1)
        host, port_s = args.tcp.split(":", 1)
        ok = wait_for_tcp(host, int(port_s), timeout=args.timeout, interval=args.interval)
        sys.exit(0 if ok else 1)

    if args.url:
        ok = wait_for_http(args.url, expected_status=args.expect_status, timeout=args.timeout, interval=args.interval)
        sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
