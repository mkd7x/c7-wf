---
id: WF-PLAN-HANDOFF-001
name: plan-commit-handoff
workflow_type: common
prerequisites:
  git: true
timeout_seconds: 300
cleanup_on_failure: false
---

# Workflow: Plan Commit & Exe Handoff Protocol

<!-- @implements REQ-HAND-01 -->
<!-- @implements REQ-HAND-02 -->
<!-- @verifies REQ-HAND-03 -->

## Purpose & Scope
This workflow specifies the exact git commitment and versioning protocol for finalizing an execution plan and gating its handoff to `02-exe`.

---

## Agent Runbook

### Step 1: Pre-Commit Validation
Ensure the plan document is complete and contains zero dependency cycles:
```bash
python3 tools/plan_runner.py lint-plan --file plans/<PLAN_FILE>.md --strict
python3 tools/plan_runner.py graph-tasks --file plans/<PLAN_FILE>.md
```

### Step 2: Commit Plan to Version Control
Commit the plan into `01-plan/plans/` and record the generated Git SHA directly into the markdown metadata table:
```bash
python3 tools/plan_runner.py commit-plan \
  --file plans/<PLAN_FILE>.md \
  --branch feature/<BRANCH_NAME> \
  --step-id step-02-commit-plan
```

### Step 3: Handoff Verification Gate
Confirm that `02-exe` can read the plan through its standard query interface:
```bash
python3 tools/plan_runner.py get-latest-plan --json
```
Verify that the output contains:
- `plan_file`: path to committed plan
- `commit_sha`: valid 40-character Git hash
- `status`: `READY FOR 02-EXE`
- `waves`: computed execution waves
