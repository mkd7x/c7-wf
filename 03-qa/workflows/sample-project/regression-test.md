# Workflow: Regression Test for `sample-project`

<!-- @implements REQ-WORK-04 -->
<!-- @verifies REQ-WORK-04 -->

## Purpose & Scope
Regression verification for `sample-project`, confirming bugfix stability and baseline behavior.

---

## Agent Runbook

### Step 1: Initialize Cleanroom
```bash
python3 tools/qa_runner.py setup-cleanroom --source tests/fixtures/sample-project
```

### Step 2: Run Baseline Suite
```bash
python3 tools/qa_runner.py exec --cmd "python3 test_sample.py"
```

### Step 3: Compile Report
```bash
python3 tools/qa_runner.py report \
  --workflow regression \
  --source sample-project \
  --status PASS \
  --notes "Regression verification clean; zero breaking changes."
```
