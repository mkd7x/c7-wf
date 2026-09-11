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
        latest = plan_runner.get_latest_plan()
        self.assertIn("plan_file", latest)
        self.assertIn("target_branch", latest)
        self.assertTrue(latest["task_count"] > 0)


if __name__ == "__main__":
    unittest.main()
