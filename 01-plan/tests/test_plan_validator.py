#!/usr/bin/env python3
"""
Unit tests for plan_validator.py
@verifies REQ-PACK-01
@verifies REQ-PACK-03
@verifies REQ-WORK-04
"""

import unittest
import tempfile
import sys
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent.parent / "tools"
TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
WORKFLOWS_DIR = Path(__file__).resolve().parent.parent / "workflows"
sys.path.insert(0, str(TOOLS_DIR))
import plan_validator

VALID_PLAN = """# Execution Plan: Test

| Attribute | Value |
| :--- | :--- |
| **Plan ID** | `PLAN-001` |
| **Target Branch** | `main` |
| **Overall Status** | `READY FOR 02-EXE` |

## 1. Executive Summary
### In-Scope
- Everything
### Out-of-Scope
- Nothing

## 2. Discovered Codebase Context
Context details

## 3. Architectural Design & ADRs
ADR details

## 4. Work Breakdown Structure & Task DAG
### [TASK-01] First Task
- **Wave**: 1
- **Dependencies**: `[]`
- **Files to Touch**:
  - `file.py`
#### Definition of Done (DoD)
- [ ] Done
#### Verification Criteria (`03-qa`)
- **Action**: Test
- **Expected Outcome**: Pass

## 5. QA Verification Contract for `03-qa`
| `QA-01` | Test | Target | Result |

## 6. Handoff Checklist for `02-exe`
Checklist items
"""

INVALID_PLAN = """# Bad Plan
No metadata table, no tasks, no QA contract.
"""


class TestPlanValidator(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    # @verifies REQ-PACK-01
    # @verifies REQ-PACK-03
    def test_valid_plan(self):
        plan_file = self.root / "valid_plan.md"
        plan_file.write_text(VALID_PLAN, encoding="utf-8")
        is_valid, errors, _ = plan_validator.lint_plan(plan_file)
        self.assertTrue(is_valid, f"Errors: {errors}")

    # @verifies REQ-PACK-03
    def test_invalid_plan(self):
        plan_file = self.root / "invalid_plan.md"
        plan_file.write_text(INVALID_PLAN, encoding="utf-8")
        is_valid, errors, _ = plan_validator.lint_plan(plan_file)
        self.assertFalse(is_valid)
        self.assertTrue(len(errors) > 0)

    # @verifies REQ-WORK-04
    def test_valid_workflow(self):
        wf_file = WORKFLOWS_DIR / "ticketless-plan.md"
        is_valid, errors, _ = plan_validator.lint_workflow(wf_file)
        self.assertTrue(is_valid, f"Errors: {errors}")


if __name__ == "__main__":
    unittest.main()
