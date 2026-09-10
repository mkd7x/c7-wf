#!/usr/bin/env python3
"""Regression tests for qa_runner verdicts, exec auditing, discovery, lint (QAF-001/003/004/005/006/013/016/018).

Run from 03-qa/:  python3 tests/test_qa_runner.py
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

QA_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(QA_DIR / "tools"))
import audit_logger  # noqa: E402
import test_discovery  # noqa: E402
from qa_runner import (  # noqa: E402
    describe_step,
    execute_step,
    generate_report,
    lint_workflow,
    render_output_snippet,
    setup_cleanroom,
)

failures = []


def check(name, cond, detail=""):
    print(f"[{'PASS' if cond else 'FAIL'}] {name}" + (f" — {detail}" if detail and not cond else ""))
    if not cond:
        failures.append(name)


def run_cli(*args, cwd=QA_DIR):
    return subprocess.run([sys.executable, "tools/qa_runner.py", *args],
                          capture_output=True, text=True, cwd=cwd)


# --- QAF-001: caller --status FAIL is authoritative over audit PASS ---
with tempfile.TemporaryDirectory() as tmp:
    audit = Path(tmp) / "audit.jsonl"
    run_cli("clear-audit", "--audit-file", str(audit))
    audit_logger.record_step(tool="demo", step_id="s1", input_data={}, output_data={},
                             assertions={}, duration_ms=10, status="PASS",
                             custom_audit_path=str(audit))
    steps = audit_logger.read_audit_log(custom_audit_path=str(audit))
    target = Path(tmp) / "target"
    target.mkdir()
    rep = generate_report("demo", "demo", "demo", target, steps,
                          {"docs_found": [], "detected_frameworks": ["Unknown"],
                           "recommended_commands": {}},
                          reports_dir=Path(tmp) / "reports", caller_status="FAIL",
                          executive_notes="agent says FAIL")
    text = rep.read_text()
    check("QAF-001 caller FAIL overrides audit PASS", "_fail.md" in rep.name and "FAIL" in text, rep.name)
    check("QAF-001 verdict disagreement surfaced", "Verdict disagreement" in text)

# --- QAF-006: exec --step-id is audited ---
with tempfile.TemporaryDirectory() as tmp:
    audit = Path(tmp) / "audit.jsonl"
    run_cli("clear-audit", "--audit-file", str(audit))
    target = Path(tmp) / "target"
    target.mkdir()
    r = run_cli("exec", "--cmd", "echo hello", "--target", str(target),
                "--step-id", "step-exec-01", "--audit-file", str(audit))
    recs = audit_logger.read_audit_log(custom_audit_path=str(audit))
    check("QAF-006 exec exits 0", r.returncode == 0, r.stderr[-300:])
    check("QAF-006 exec audited", any(x.get("step_id") == "step-exec-01" for x in recs), str(recs))
    # failing exec records FAIL
    r = run_cli("exec", "--cmd", "exit 3", "--target", str(target),
                "--step-id", "step-exec-02", "--audit-file", str(audit))
    recs = audit_logger.read_audit_log(custom_audit_path=str(audit))
    rec = next(x for x in recs if x.get("step_id") == "step-exec-02")
    check("QAF-006 failing exec audits FAIL", rec["status"] == "FAIL", str(rec["status"]))

# --- QAF-004: backgrounded exec returns promptly ---
with tempfile.TemporaryDirectory() as tmp:
    import time
    target = Path(tmp)
    start = time.time()
    res = execute_step("sleep 8 &", cwd=target, timeout=3)
    elapsed = time.time() - start
    check("QAF-004 background exec no hang", elapsed < 3 and res["status"] == "PASS",
          f"{elapsed:.1f}s {res}")

# --- QAF-013: clear-audit archives instead of mixing runs ---
with tempfile.TemporaryDirectory() as tmp:
    audit = Path(tmp) / "audit.jsonl"
    run_cli("clear-audit", "--audit-file", str(audit))
    audit_logger.record_step(tool="demo", step_id="s-old", input_data={}, output_data={},
                             assertions={}, duration_ms=1, status="PASS",
                             custom_audit_path=str(audit))
    run_cli("clear-audit", "--audit-file", str(audit))
    recs = audit_logger.read_audit_log(custom_audit_path=str(audit))
    check("QAF-013 custom audit cleared", recs == [], str(recs))

# --- QAF-003/017: dotnet detection + hygiene ---
with tempfile.TemporaryDirectory() as tmp:
    d = Path(tmp)
    (d / "README.md").write_text("```bash\n└── tests/\n└── TodoApi.Application.UnitTests/  # comment\n$ dotnet test  # real\nsome prose about python testing\n```\n")
    cmds = test_discovery.extract_markdown_commands(d / "README.md")
    check("QAF-017 tree art excluded", all("└" not in c for c in cmds), str(cmds))
    check("QAF-017 comments stripped", all("#" not in c for c in cmds), str(cmds))
    check("QAF-017 prose excluded", not any("prose" in c for c in cmds), str(cmds))
    check("QAF-017 dotnet kept", cmds == ["dotnet test"], str(cmds))

    (d / "README.md").unlink()
    (d / "TodoApi.slnx").write_text("<solution/>")
    (d / "tests").mkdir()
    (d / "tests" / "TodoApi.Application.UnitTests.csproj").write_text("<project/>")
    disc = test_discovery.discover_project_tests(d)
    check("QAF-003 dotnet detected", ".NET" in disc["detected_frameworks"],
          str(disc["detected_frameworks"]))
    check("QAF-003 dotnet unit cmd", disc["recommended_commands"]["unit"] == "dotnet test TodoApi.slnx",
          str(disc["recommended_commands"]))

# --- QAF-005/018: lint strict + fence hygiene ---
with tempfile.TemporaryDirectory() as tmp:
    bare = Path(tmp) / "bare.md"
    bare.write_text("# bare\n\njust prose\n")
    valid, errors, warnings = lint_workflow(bare)
    check("QAF-005 advisory by default", valid and warnings, f"{errors} {warnings}")
    valid_s, errors_s, _ = lint_workflow(bare, strict=True)
    check("QAF-005 strict fails bare runbook", not valid_s and errors_s, str(errors_s))

    tricky = Path(tmp) / "tricky.md"
    tricky.write_text('---\nid: X\nname: Y\n---\n\n```json\n{"tool": "send_http_req.py --step-id x"}\n```\n\nTeardown\n')
    valid, errors, warnings = lint_workflow(tricky)
    check("QAF-018 json fence ignored", valid and not errors, f"{errors} {warnings}")

    badflag = Path(tmp) / "badflag.md"
    badflag.write_text('---\nid: X\nname: Y\n---\n\n```bash\npython3 tools/send_http_req.py http://x --bogus-flag 1 --step-id s\n```\n\nTeardown\n')
    valid, errors, _ = lint_workflow(badflag)
    check("QAF-005 unknown flag flagged", not valid and any("bogus" in e for e in errors), str(errors))

# --- QAF-016: rendering ---
check("QAF-016 no ellipsis when short", render_output_snippet({"a": 1}) != "" and
      not render_output_snippet({"a": 1}).endswith("..."))
check("QAF-016 ellipsis when truncated", render_output_snippet("x" * 600).endswith("..."))
check("QAF-016 wait_for_service desc",
      describe_step({"tool": "wait_for_service", "input": {"target": "http://x/health"}}) ==
      "wait_for_service (http://x/health)",
      describe_step({"tool": "wait_for_service", "input": {"target": "http://x/health"}}))

# --- QAF-007/014: .gitkeep preserved + failed clone keeps sandbox ---
with tempfile.TemporaryDirectory() as tmp:
    src = Path(tmp) / "src"
    src.mkdir()
    (src / "a.txt").write_text("a")
    target = Path(tmp) / "target"
    target.mkdir()
    (target / ".gitkeep").write_text("# Keep target-repo directory structure tracked in git\n")
    (target / "old.txt").write_text("old")
    check("QAF-014 local copy ok", setup_cleanroom(str(src), target))
    check("QAF-007 .gitkeep content kept",
          (target / ".gitkeep").read_text().startswith("# Keep"),
          (target / ".gitkeep").read_text()[:50])
    check("QAF-014 old files replaced", not (target / "old.txt").exists() and (target / "a.txt").exists())
    (target / "keep.txt").write_text("keep")
    check("QAF-014 failed clone keeps sandbox",
          setup_cleanroom("https://invalid.invalid/nope.git", target) is False
          and (target / "keep.txt").exists() and (target / ".gitkeep").exists())

# --- SQL engine guard (QAF-011) ---
r = subprocess.run([sys.executable, "tools/run_sql_cmd.py", "--driver", "docker",
                    "--engine", "postgres", "--query", "SELECT 1"],
                   capture_output=True, text=True, cwd=QA_DIR)
check("QAF-011 postgres rejected at argparse",
      r.returncode != 0 and "invalid choice" in r.stderr, r.stderr[-300:])

# --- Blob CLI ordering + binary safety (QAF-012) ---
with tempfile.TemporaryDirectory() as tmp:
    d = Path(tmp) / "blobs"
    d.mkdir()
    (d / "a.txt").write_text("hello")
    r = subprocess.run([sys.executable, "tools/query_blob_storage.py", "list",
                        "--dir", str(d), "--step-id", "blob-01"],
                       capture_output=True, text=True, cwd=QA_DIR)
    check("QAF-012 post-subcommand --step-id works", r.returncode == 0, r.stderr[-300:])
    blob = Path(tmp) / "bin.dat"
    blob.write_bytes(bytes(range(256)))
    r = subprocess.run([sys.executable, "tools/query_blob_storage.py", "put",
                        "--dir", str(d), "--key", "b.bin", "--file", str(blob)],
                       capture_output=True, text=True, cwd=QA_DIR)
    out = Path(tmp) / "out.bin"
    r = subprocess.run([sys.executable, "tools/query_blob_storage.py", "get",
                        "--dir", str(d), "--key", "b.bin", "--out", str(out)],
                       capture_output=True, text=True, cwd=QA_DIR)
    check("QAF-012 binary round-trip exact",
          r.returncode == 0 and out.read_bytes() == blob.read_bytes())

print()
if failures:
    print(f"{len(failures)} check(s) FAILED: {failures}")
    sys.exit(1)
print("All qa_runner regression checks passed.")
