#!/usr/bin/env python3
"""
Unit tests for jira_client.py
@verifies REQ-WORK-01
@verifies REQ-WORK-03
"""

import unittest
import sys
import json
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent.parent / "tools"
sys.path.insert(0, str(TOOLS_DIR))
import jira_client


class TestJiraClient(unittest.TestCase):
    def setUp(self):
        # Force dry-run/mock mode for test isolation
        self.client = jira_client.JiraClient(dry_run=True)

    # @verifies REQ-WORK-01
    def test_fetch_issue_mock(self):
        issue = self.client.fetch_issue("PROJ-999")
        self.assertEqual(issue["key"], "PROJ-999")
        self.assertTrue(len(issue["acceptance_criteria"]) > 0)
        self.assertTrue(issue["is_mock"])

    # @verifies REQ-WORK-03
    def test_post_comment_mock(self):
        res = self.client.post_comment("PROJ-999", "Execution plan ready.")
        self.assertEqual(res["status"], "COMMENT_POSTED_MOCK")
        self.assertTrue(res["is_mock"])

    # @verifies REQ-WORK-03
    def test_transition_issue_mock(self):
        res = self.client.transition_issue("PROJ-999", "In Progress")
        self.assertEqual(res["status"], "TRANSITIONED_MOCK")
        self.assertEqual(res["transitioned_to"], "In Progress")

    # @verifies REQ-WORK-03
    def test_create_subtasks_mock(self):
        tasks = [
            {"id": "TASK-01", "title": "Setup Schema"},
            {"id": "TASK-02", "title": "Build Service"}
        ]
        subtasks = self.client.create_subtasks("PROJ-999", tasks)
        self.assertEqual(len(subtasks), 2)
        self.assertEqual(subtasks[0]["parent_key"], "PROJ-999")
        self.assertEqual(subtasks[0]["status"], "CREATED_MOCK")
        self.assertTrue(subtasks[0]["is_mock"])

    # @verifies REQ-WORK-03
    def test_create_subtasks_failure_recorded_not_fabricated(self):
        import urllib.request
        client = jira_client.JiraClient(
            base_url="http://127.0.0.1:1", email="t@e.com", api_token="tok")
        self.assertFalse(client.dry_run)
        orig_urlopen = urllib.request.urlopen

        def boom(*a, **k):
            raise ConnectionError("refused")

        urllib.request.urlopen = boom
        try:
            res = client.create_subtasks(
                "PROJ-999", [{"id": "TASK-01", "title": "Setup Schema"}])
        finally:
            urllib.request.urlopen = orig_urlopen
        self.assertEqual(res[0]["status"], "FAILED")
        self.assertIsNone(res[0]["subtask_key"])
        self.assertFalse(res[0]["is_mock"])

    # @verifies REQ-WORK-03
    def test_render_plan_comment_uses_template(self):
        tasks = [
            {"id": "TASK-01", "title": "Setup Schema", "wave": 1,
             "dependencies": [], "component": "Infra",
             "qa_criteria": {"action": "check", "expected_outcome": "pass"}},
            {"id": "TASK-02", "title": "Build Service", "wave": 2,
             "dependencies": ["TASK-01"], "component": "App",
             "qa_criteria": {"action": "test", "expected_outcome": "pass"}},
        ]
        comment = jira_client.render_plan_comment(
            plan_id="PLAN-001", plan_title="Demo", plan_file="demo_plan.md",
            target_branch="feature/demo", commit_sha="abc123", tasks=tasks)
        self.assertIn("PLAN-001", comment)
        self.assertIn("TASK-01", comment)
        self.assertIn("TASK-02", comment)
        self.assertIn("2 scenarios", comment)
        self.assertNotIn("{{", comment)

    # @verifies REQ-WORK-03
    def test_post_json_extracts_jira_error_body(self):
        import urllib.request
        import urllib.error
        import io
        client = jira_client.JiraClient(
            base_url="http://127.0.0.1:1", email="t@e.com", api_token="tok")
        self.assertFalse(client.dry_run)
        orig_urlopen = urllib.request.urlopen

        error_json = json.dumps({
            "errorMessages": ["Issue type is invalid"],
            "errors": {"summary": "Field is required"}
        }).encode("utf-8")

        import email.message
        def fake_urlopen(*a, **k):
            fp = io.BytesIO(error_json)
            raise urllib.error.HTTPError(
                url="http://127.0.0.1:1/rest/api/2/issue",
                code=400,
                msg="Bad Request",
                hdrs=email.message.Message(),
                fp=fp
            )

        urllib.request.urlopen = fake_urlopen
        try:
            ok, err = client._post_json("http://127.0.0.1:1/rest/api/2/issue", {})
        finally:
            urllib.request.urlopen = orig_urlopen

        self.assertFalse(ok)
        self.assertIn("Issue type is invalid", err)
        self.assertIn("summary: Field is required", err)


if __name__ == "__main__":
    unittest.main()
