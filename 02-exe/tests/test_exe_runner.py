#!/usr/bin/env python3
"""
Unit tests for 02-exe exe_runner.py.
Validates plan intake, workflow linting, fast test loop, and handoff manifest generation.

@verifies REQ-DEV-01
@verifies REQ-DEV-03
@verifies REQ-WORK-02
@verifies REQ-HAND-01
@verifies REQ-HAND-02
"""

import sys
import unittest
import tempfile
import shutil
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent.parent / "tools"
sys.path.insert(0, str(TOOLS_DIR))

import exe_runner


class TestExeRunner(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.workspace = Path(self.temp_dir)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_workflow_linter(self):
        # @verifies REQ-WORK-02
        good_wf = self.workspace / "good.md"
        good_wf.write_text("""---
id: WF-001
name: test-wf
target: my-repo
---
# Runbook
trap 'cleanup' EXIT INT TERM
### Step 1: Run
""", encoding="utf-8")
        ok, errs, warns = exe_runner.lint_workflow_runbook(good_wf)
        self.assertTrue(ok)
        self.assertEqual(len(errs), 0)

        bad_wf = self.workspace / "bad.md"
        bad_wf.write_text("# Bad Runbook with no frontmatter\n", encoding="utf-8")
        ok_bad, errs_bad, _ = exe_runner.lint_workflow_runbook(bad_wf)
        self.assertFalse(ok_bad)
        self.assertIn("Missing YAML frontmatter", errs_bad[0])

    def test_test_loop_execution(self):
        # @verifies REQ-DEV-03
        ok, rec = exe_runner.execute_test_loop(cmd="echo 'fast test pass'", task_id="TASK-999")
        self.assertTrue(ok)
        self.assertEqual(rec["status"], "PASS")

    def test_handoff_manifest_packaging(self):
        # @verifies REQ-HAND-02
        manifest = exe_runner.generate_qa_handoff(
            branch="feature/test-branch",
            commit_sha="abcdef123456",
            notes="Ready for cleanroom test"
        )
        self.assertEqual(manifest["target_branch"], "feature/test-branch")
        self.assertEqual(manifest["commit_sha"], "abcdef123456")
        self.assertIn("qa_instructions", manifest)

    def test_intake_from_plan_file(self):
        # @verifies REQ-DEV-01
        plan_doc = self.workspace / "plan.md"
        plan_doc.write_text("# Plan\nBranch: `feature/demo`\nTask: TASK-01\n", encoding="utf-8")
        res = exe_runner.intake_plan_from_01_plan(plan_doc)
        self.assertEqual(res["target_branch"], "feature/demo")

    def test_audit_logging(self):
        # @verifies REQ-DEV-04
        import audit_logger
        rec = audit_logger.record_step(
            tool="test_tool",
            step_id="step-audit-test",
            input_data={"param": "val"},
            output_data={"result": "ok"},
            assertions={"ok": True},
            duration_ms=12.5,
            status="PASS"
        )
        self.assertEqual(rec["step_id"], "step-audit-test")
        saved = audit_logger.get_step_output("step-audit-test")
        self.assertIsNotNone(saved)
        self.assertEqual(saved["status"], "PASS")


if __name__ == "__main__":
    unittest.main()

