# Workflow: Smoke Test for `sample-project`

<!-- @implements REQ-WORK-01 -->
<!-- @verifies REQ-WORK-01 -->
<!-- @verifies REQ-TOOL-HTTP -->
<!-- @verifies REQ-HAND-03 -->

## Purpose & Scope
Fast sanity and smoke verification for the `sample-project` test fixture. Validates cleanroom setup, instruction parsing, and execution of core smoke tests.

---

## Agent Runbook

### Step 1: Initialize Cleanroom
```bash
python3 tools/qa_runner.py setup-cleanroom --source tests/fixtures/sample-project
```

### Step 2: Discover Test Instructions
```bash
python3 tools/qa_runner.py discover --target target-repo
```
*Verify that `TESTING.md` was discovered.*

### Step 3: Execute Smoke Test
- **Action**: Test Execution
- **Tool**: `tools/qa_runner.py exec`
- **CLI Command**:
```bash
python3 tools/qa_runner.py exec --cmd "python3 test_sample.py"
```

### Step 4: Compile Report
```bash
python3 tools/qa_runner.py report \
  --workflow smoke \
  --source sample-project \
  --status PASS \
  --notes "Smoke test executed cleanly in target-repo."
```
