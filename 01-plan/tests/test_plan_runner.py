#!/usr/bin/env python3
"""
Unit tests for plan_runner.py
@verifies REQ-WORK-01
@verifies REQ-WORK-02
@verifies REQ-PACK-01
@verifies REQ-PACK-02
@verifies REQ-ARCH-03
@verifies REQ-HAND-01
@verifies REQ-HAND-02
@verifies REQ-HAND-03
"""

import unittest
import tempfile
import sys
import json
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent.parent / "tools"
sys.path.insert(0, str(TOOLS_DIR))
import plan_runner


class TestPlanRunner(unittest.TestCase):
    def setUp(self):
        self.created_plans = []

    def tearDown(self):
        for p in self.created_plans:
            if p.exists():
                try:
                    p.unlink()
                except Exception:
                    pass
    # @verifies REQ-WORK-01
    def test_jira_intake(self):
        res = plan_runner.run_intake("jira", ticket="PROJ-500")
        self.assertEqual(res["source_ref"], "PROJ-500")
        self.assertEqual(res["workflow"], "jira")
        self.assertTrue(len(res["acceptance_criteria"]) > 0)

    # @verifies REQ-WORK-02
    def test_adhoc_intake(self):
        res = plan_runner.run_intake("adhoc", title="Test Adhoc", brief="Local feature work")
        self.assertEqual(res["source_ref"], "LOCAL_BRIEF")
        self.assertEqual(res["workflow"], "adhoc")
        self.assertEqual(res["title"], "Test Adhoc")

    # @verifies REQ-PACK-01
    # @verifies REQ-PACK-02
    # @verifies REQ-ARCH-03
    def test_package_plan(self):
        plan_path = plan_runner.package_plan(
            title="Unit Test Feature",
            workflow_mode="adhoc",
            source_ref="LOCAL_BRIEF",
            target_repo="test-repo/",
            target_branch="feature/unit-test"
        )
        self.created_plans.append(plan_path)
        self.assertTrue(plan_path.exists())
        content = plan_path.read_text(encoding="utf-8")
        self.assertIn("Execution Plan: Unit Test Feature", content)
        self.assertIn("feature/unit-test", content)
        self.assertIn("QA Verification Contract", content)

    # @verifies REQ-HAND-03
    def test_get_latest_plan(self):
        plan_path = plan_runner.package_plan(
            title="Active Test Plan",
            workflow_mode="adhoc",
            source_ref="LOCAL_BRIEF",
            target_repo="test-repo/",
            target_branch="feature/active-test"
        )
        self.created_plans.append(plan_path)
        # Freshly packaged plans are DRAFT: default query must refuse handoff
        latest = plan_runner.get_latest_plan(require_ready=False)
        self.assertIn("plan_file", latest)
        self.assertIn("target_branch", latest)
        self.assertTrue(latest["task_count"] > 0)

    # @verifies REQ-HAND-03
    def test_get_latest_plan_refuses_draft(self):
        plan_path = plan_runner.package_plan(
            title="Draft Refusal Plan",
            workflow_mode="adhoc",
            source_ref="LOCAL_BRIEF",
            target_repo="test-repo/",
            target_branch="feature/draft-refusal"
        )
        self.created_plans.append(plan_path)
        # Direct readiness check is hermetic (no dependence on other files in plans/)
        payload, reasons = plan_runner._plan_readiness(plan_path)
        self.assertTrue(any("READY FOR 02-EXE" in r for r in reasons))
        self.assertTrue(any("commit SHA" in r for r in reasons))
        res = plan_runner.get_latest_plan()
        self.assertEqual(res.get("status"), "PLAN_NOT_READY")
        self.assertTrue(res.get("reasons"))

    # @verifies REQ-PACK-03
    # @verifies REQ-HAND-01
    def test_commit_plan_refuses_invalid_plan(self):
        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp) / "bad_plan.md"
            bad.write_text("# Bad Plan\nNo metadata, no tasks.\n", encoding="utf-8")
            with self.assertRaises(ValueError) as ctx:
                plan_runner.commit_plan_to_git(bad)
            self.assertIn("validation failed", str(ctx.exception).lower())

    # @verifies REQ-TASK-03
    def test_package_plan_rejects_invalid_dag(self):
        tasks = [
            {"id": "DUP", "title": "a", "wave": 1, "dependencies": [],
             "component": "x", "files": ["a.py"], "dod": ["done"],
             "qa_criteria": {"action": "check", "expected_outcome": "pass"}},
            {"id": "DUP", "title": "b", "wave": 1, "dependencies": [],
             "component": "x", "files": ["b.py"], "dod": ["done"],
             "qa_criteria": {"action": "check", "expected_outcome": "pass"}},
        ]
        with self.assertRaises(ValueError) as ctx:
            plan_runner.package_plan(
                title="Dup Dag Plan",
                workflow_mode="adhoc",
                source_ref="LOCAL_BRIEF",
                tasks=tasks,
            )
        self.assertIn("duplicate", str(ctx.exception).lower())

    # @verifies REQ-HAND-03
    def test_get_latest_plan_ticket_not_found(self):
        res = plan_runner.get_latest_plan(ticket="NON_EXISTENT_PROJ_99999")
        self.assertEqual(res.get("status"), "TICKET_NOT_FOUND")
        self.assertEqual(res.get("ticket"), "NON_EXISTENT_PROJ_99999")

    # @verifies REQ-TASK-04
    # @verifies REQ-PACK-01
    def test_package_plan_auto_syncs_waves(self):
        tasks = [
            {"id": "TASK-01", "title": "Base Step", "wave": 1, "dependencies": [],
             "component": "Core", "files": ["base.py"], "dod": ["done"],
             "qa_criteria": {"action": "check", "expected_outcome": "pass"}},
            {"id": "TASK-02", "title": "Dependent Step", "wave": 1, "dependencies": ["TASK-01"],
             "component": "Core", "files": ["dep.py"], "dod": ["done"],
             "qa_criteria": {"action": "check", "expected_outcome": "pass"}},
        ]
        plan_path = plan_runner.package_plan(
            title="Auto Wave Sync Plan",
            workflow_mode="adhoc",
            source_ref="LOCAL_BRIEF",
            tasks=tasks
        )
        self.created_plans.append(plan_path)
        content = plan_path.read_text(encoding="utf-8")
        # TASK-02 should have been auto-synced to Wave 2 despite declared wave 1
        self.assertRegex(content, r"### \[TASK-02\].*?\n-\s*\*\*Wave\*\*:\s*2")


if __name__ == "__main__":
    unittest.main()
