# Workflow: Unit Test for `sample-project`

<!-- @implements REQ-WORK-02 -->
<!-- @verifies REQ-WORK-02 -->

## Purpose & Scope
Runs unit tests and verifies assertion results for `sample-project`.

---

## Agent Runbook

### Step 1: Initialize Cleanroom
```bash
python3 tools/qa_runner.py setup-cleanroom --source tests/fixtures/sample-project
```

### Step 2: Run Unit Tests
```bash
python3 tools/qa_runner.py exec --cmd "python3 test_sample.py"
```

### Step 3: Compile Report
```bash
python3 tools/qa_runner.py report \
  --workflow unit \
  --source sample-project \
  --status PASS \
  --notes "All sample unit tests passed."
```
