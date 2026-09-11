#!/usr/bin/env python3
"""
Unit tests for jira_client.py
@verifies REQ-WORK-01
@verifies REQ-WORK-03
"""

import unittest
import sys
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


if __name__ == "__main__":
    unittest.main()
