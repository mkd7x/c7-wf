---
id: WF-EXE-SAMPLE-TEST
name: sample-project-test-loop
target: sample-project
prerequisites:
  python: ">=3.10"
timeout_seconds: 60
---

# Fast Test Loop for Sample Project

<!-- @verifies REQ-DEV-03 -->

### Step 1: Execute Fast Inner-Loop Checks
Run fast linting and unit tests against modified code:
```bash
python3 tools/exe_runner.py test-loop --cmd "python3 -m unittest discover -s tests" --task-id TASK-01
```
