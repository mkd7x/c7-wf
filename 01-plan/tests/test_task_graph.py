#!/usr/bin/env python3
"""
Unit tests for task_graph.py
@verifies REQ-TASK-01
@verifies REQ-TASK-02
@verifies REQ-TASK-03
@verifies REQ-TASK-04
"""

import unittest
import sys
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent.parent / "tools"
sys.path.insert(0, str(TOOLS_DIR))
import task_graph

SAMPLE_PLAN_MARKDOWN = """
# Execution Plan: Sample

## 4. Work Breakdown Structure & Task DAG

### [TASK-01] Database Setup
- **Wave**: 1
- **Dependencies**: `[]`
- **Component / Layer**: Infrastructure
- **Files to Touch**:
  - `src/db/schema.sql`

#### Description
Setup database tables.

#### Definition of Done (DoD)
- [ ] Schema applied

#### Verification Criteria (`03-qa`)
- **Action**: Check schema
- **Expected Outcome**: Tables created

---

### [TASK-02] Business Service
- **Wave**: 2
- **Dependencies**: `[TASK-01]`
- **Component / Layer**: Application
- **Files to Touch**:
  - `src/service.py`

#### Description
Implement core service.

#### Definition of Done (DoD)
- [ ] Unit tests pass

#### Verification Criteria (`03-qa`)
- **Action**: Run unit tests
- **Expected Outcome**: 100% pass

---

### [TASK-03] API Controller
- **Wave**: 3
- **Dependencies**: `[TASK-02]`
- **Component / Layer**: API
- **Files to Touch**:
  - `src/controller.py`

#### Description
Expose HTTP route.

#### Definition of Done (DoD)
- [ ] Endpoint returns 200

#### Verification Criteria (`03-qa`)
- **Action**: HTTP GET
- **Expected Outcome**: Status 200
"""

CYCLIC_PLAN_MARKDOWN = """
### [TASK-A] Task A
- **Dependencies**: `[TASK-B]`
- **Files to Touch**:
  - `a.py`
#### Definition of Done (DoD)
- [ ] Done

### [TASK-B] Task B
- **Dependencies**: `[TASK-A]`
- **Files to Touch**:
  - `b.py`
#### Definition of Done (DoD)
- [ ] Done
"""


class TestTaskGraph(unittest.TestCase):
    # @verifies REQ-TASK-01
    # @verifies REQ-TASK-02
    def test_parse_tasks(self):
        tasks = task_graph.parse_tasks_from_markdown(SAMPLE_PLAN_MARKDOWN)
        self.assertEqual(len(tasks), 3)
        self.assertEqual(tasks[0]["id"], "TASK-01")
        self.assertEqual(tasks[0]["dependencies"], [])
        self.assertEqual(tasks[1]["dependencies"], ["TASK-01"])
        self.assertEqual(tasks[2]["dependencies"], ["TASK-02"])

    # @verifies REQ-TASK-03
    def test_valid_dag(self):
        tasks = task_graph.parse_tasks_from_markdown(SAMPLE_PLAN_MARKDOWN)
        is_valid, errors, _ = task_graph.validate_dag(tasks)
        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)

    # @verifies REQ-TASK-03
    def test_cycle_detection(self):
        tasks = task_graph.parse_tasks_from_markdown(CYCLIC_PLAN_MARKDOWN)
        is_valid, errors, _ = task_graph.validate_dag(tasks)
        self.assertFalse(is_valid)
        self.assertTrue(any("Circular dependency" in e for e in errors))

    # @verifies REQ-TASK-04
    def test_execution_waves(self):
        tasks = task_graph.parse_tasks_from_markdown(SAMPLE_PLAN_MARKDOWN)
        waves = task_graph.compute_execution_waves(tasks)
        self.assertEqual(len(waves), 3)
        self.assertEqual([t["id"] for t in waves[0]], ["TASK-01"])
        self.assertEqual([t["id"] for t in waves[1]], ["TASK-02"])
        self.assertEqual([t["id"] for t in waves[2]], ["TASK-03"])

    # @verifies REQ-TASK-03
    def test_duplicate_ids_rejected(self):
        tasks = [
            {"id": "TASK-01", "title": "A", "wave": 1, "dependencies": [],
             "component": "x", "files": [], "dod": [], "qa_criteria": {}},
            {"id": "TASK-01", "title": "B", "wave": 1, "dependencies": [],
             "component": "x", "files": [], "dod": [], "qa_criteria": {}},
        ]
        is_valid, errors, _ = task_graph.validate_dag(tasks)
        self.assertFalse(is_valid)
        self.assertTrue(any("Duplicate task ID" in e for e in errors))

    # @verifies REQ-TASK-03
    def test_compute_waves_rejects_duplicate_ids(self):
        tasks = [
            {"id": "T1", "title": "a", "wave": 1, "dependencies": [],
             "component": "x", "files": [], "dod": [], "qa_criteria": {}},
            {"id": "T1", "title": "b", "wave": 1, "dependencies": [],
             "component": "x", "files": [], "dod": [], "qa_criteria": {}},
        ]
        with self.assertRaises(ValueError):
            task_graph.compute_execution_waves(tasks)

    # @verifies REQ-TASK-03
    def test_compute_waves_rejects_missing_dependency(self):
        tasks = [
            {"id": "T1", "title": "a", "wave": 1, "dependencies": ["MISSING"],
             "component": "x", "files": [], "dod": [], "qa_criteria": {}},
        ]
        is_valid, errors, _ = task_graph.validate_dag(tasks)
        self.assertFalse(is_valid)
        with self.assertRaises(ValueError) as ctx:
            task_graph.compute_execution_waves(tasks)
        self.assertIn("non-existent dependencies", str(ctx.exception))

    # @verifies REQ-TASK-03
    def test_compute_waves_rejects_cycle(self):
        tasks = task_graph.parse_tasks_from_markdown(CYCLIC_PLAN_MARKDOWN)
        with self.assertRaises(ValueError) as ctx:
            task_graph.compute_execution_waves(tasks)
        self.assertIn("circular", str(ctx.exception).lower())

    # @verifies REQ-TASK-04
    def test_declared_wave_mismatch_warns(self):
        tasks = [
            {"id": "A", "title": "a", "wave": 5, "dependencies": [],
             "component": "x", "files": [], "dod": [], "qa_criteria": {}},
            {"id": "B", "title": "b", "wave": 1, "dependencies": ["A"],
             "component": "x", "files": [], "dod": [], "qa_criteria": {}},
        ]
        is_valid, _, warnings = task_graph.validate_dag(tasks)
        self.assertTrue(is_valid)
        self.assertTrue(any("Wave" in w for w in warnings))
        # Computed waves still govern execution order regardless of declared values
        waves = task_graph.compute_execution_waves(tasks)
        self.assertEqual([[t["id"] for t in w] for w in waves], [["A"], ["B"]])


if __name__ == "__main__":
    unittest.main()
