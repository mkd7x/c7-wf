#!/usr/bin/env python3
"""
Blob & Object Storage Query Helper for Clean Room QA Testing.
Inspects, queries, and asserts object states in local mock blob directories
and S3/MinIO compatible object stores.
@implements REQ-TOOL-BLOB
"""

import os
import sys
import json
import shutil
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional


def list_local_blobs(bucket_dir: Path, prefix: str = "") -> List[Dict[str, Any]]:
    """List objects in a local directory acting as a blob store."""
    blobs = []
    if not bucket_dir.exists():
        return blobs

    for p in bucket_dir.rglob("*"):
        if p.is_file() and not p.name.startswith("."):
            rel_key = p.relative_to(bucket_dir).as_posix()
            if prefix and not rel_key.startswith(prefix):
                continue
            stat = p.stat()
            blobs.append({
                "key": rel_key,
                "size_bytes": stat.st_size,
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "path": str(p)
            })
    return blobs


def main():
    parser = argparse.ArgumentParser(description="Clean Room Blob & Object Storage Query CLI")
    subparsers = parser.add_subparsers(dest="action", help="Storage action")

    # list
    p_list = subparsers.add_parser("list", help="List objects in storage bucket/directory")
    p_list.add_argument("--dir", "-d", required=True, help="Path to local bucket/blob directory")
    p_list.add_argument("--prefix", "-p", default="", help="Filter by key prefix")
    p_list.add_argument("--json", action="store_true", help="Output JSON format")

    # exists
    p_exists = subparsers.add_parser("exists", help="Check if an object exists in storage")
    p_exists.add_argument("--dir", "-d", required=True, help="Path to local bucket/blob directory")
    p_exists.add_argument("--key", "-k", required=True, help="Object key name")

    # get
    p_get = subparsers.add_parser("get", help="Retrieve blob content")
    p_get.add_argument("--dir", "-d", required=True, help="Path to local bucket/blob directory")
    p_get.add_argument("--key", "-k", required=True, help="Object key name")
    p_get.add_argument("--out", "-o", help="File to write blob content to")

    # put
    p_put = subparsers.add_parser("put", help="Upload a file as a blob")
    p_put.add_argument("--dir", "-d", required=True, help="Path to local bucket/blob directory")
    p_put.add_argument("--key", "-k", required=True, help="Object key name")
    p_put.add_argument("--file", "-f", required=True, help="Source file to upload")

    # delete
    p_del = subparsers.add_parser("delete", help="Delete a blob")
    p_del.add_argument("--dir", "-d", required=True, help="Path to local bucket/blob directory")
    p_del.add_argument("--key", "-k", required=True, help="Object key name")

    args = parser.parse_args()

    if not args.action:
        parser.print_help()
        sys.exit(0)

    bucket_path = Path(args.dir).resolve()

    if args.action == "list":
        blobs = list_local_blobs(bucket_path, prefix=args.prefix)
        if args.json:
            print(json.dumps(blobs, indent=2))
        else:
            print(f"=== Blobs in {bucket_path} (Prefix: '{args.prefix}') ===")
            if not blobs:
                print("  (No objects found)")
            for b in blobs:
                print(f"  - {b['key']:<30} ({b['size_bytes']} bytes, {b['modified']})")
            print(f"\nTotal: {len(blobs)} object(s)")

    elif args.action == "exists":
        target_file = bucket_path / args.key
        if target_file.is_file():
            print(f"[✓] Blob exists: {args.key} ({target_file.stat().st_size} bytes)")
            sys.exit(0)
        else:
            print(f"[!] Blob NOT found: {args.key}", file=sys.stderr)
            sys.exit(1)

    elif args.action == "get":
        target_file = bucket_path / args.key
        if not target_file.is_file():
            print(f"[!] Blob not found: {args.key}", file=sys.stderr)
            sys.exit(1)
        content = target_file.read_text(encoding="utf-8", errors="replace")
        if args.out:
            Path(args.out).write_text(content, encoding="utf-8")
            print(f"[✓] Blob written to {args.out}")
        else:
            print(content)

    elif args.action == "put":
        src_path = Path(args.file)
        if not src_path.is_file():
            print(f"[!] Source file not found: {src_path}", file=sys.stderr)
            sys.exit(1)
        dest_file = bucket_path / args.key
        dest_file.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src_path, dest_file)
        print(f"[✓] Uploaded {src_path} -> {args.key}")

    elif args.action == "delete":
        target_file = bucket_path / args.key
        if target_file.is_file():
            target_file.unlink()
            print(f"[✓] Deleted blob {args.key}")
        else:
            print(f"[!] Blob not found to delete: {args.key}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()
