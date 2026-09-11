---
id: WF-PLAN-JIRA-001
name: jira-driven-planning
workflow_type: jira
prerequisites:
  git: true
timeout_seconds: 600
cleanup_on_failure: false
---

# Workflow: Jira-Driven Planning Runbook

<!-- @implements REQ-WORK-01 -->
<!-- @verifies REQ-WORK-01 -->
<!-- @verifies REQ-WORK-03 -->
<!-- @verifies REQ-HAND-01 -->
<!-- @verifies REQ-HAND-02 -->

## Purpose & Scope
Intake an active Jira issue, inspect the target repository, formulate architectural decisions, decompose tasks into a dependency DAG, sync status and subtasks back to Jira, and commit the plan to Git for `02-exe`.

---

## Agent Runbook

### Step 1: Intake Jira Ticket & Initialize Session
- **Action**: Fetch ticket summary, acceptance criteria, components, and description.
- **Tool**: `tools/plan_runner.py`
- **CLI Command**:
```bash
python3 tools/plan_runner.py intake \
  --workflow jira \
  --ticket PROJ-1024 \
  --step-id step-01-jira-intake
```
*Verify: Ticket details saved into `01-plan/runs/latest/intake.json`.*

### Step 2: Discover Target Codebase Context
- **Action**: Scan target repo for frameworks, existing models, endpoints, and ADRs.
- **Tool**: `tools/context_discovery.py`
- **CLI Command**:
```bash
python3 tools/plan_runner.py discover \
  --source target-repo/ \
  --step-id step-02-discover-context
```
*Verify: Discovered stack and directories populated in `01-plan/runs/latest/context.json`.*

### Step 3: Author Architectural Design & ADR
- **Action**: Formulate architectural decisions and data models based on Jira acceptance criteria.
- **Tool**: `templates/ADR_TEMPLATE.md`
- **Verification**: Ensure positive/negative consequences and alternatives are captured.

### Step 4: Decompose Tasks & Define QA Contracts
- **Action**: Break down implementation into atomic tasks tagged `[PROJ-1024-T1]`, `[PROJ-1024-T2]`.
- **Tool**: `templates/TASK_TEMPLATE.md`
- **Verification**: Each task must declare `depends_on: [...]`, files to touch, DoD, and verification criteria for `03-qa`.

### Step 5: Validate Task DAG & Lint Plan Schema
- **Action**: Machine-verify that dependencies have zero cycles and the plan conforms to schema.
- **Tool**: `tools/plan_runner.py`
- **CLI Commands**:
```bash
python3 tools/plan_runner.py graph-tasks \
  --file plans/latest_plan.md \
  --step-id step-05-graph-tasks

python3 tools/plan_runner.py lint-plan \
  --file plans/latest_plan.md \
  --strict \
  --step-id step-05-lint-plan
```

### Step 6: Sync Back to Jira
- **Action**: Post plan summary comment, transition Jira issue, and create child subtasks.
- **Tool**: `tools/plan_runner.py`
- **CLI Command**:
```bash
python3 tools/plan_runner.py sync-jira \
  --ticket PROJ-1024 \
  --file plans/latest_plan.md \
  --transition "In Progress" \
  --create-subtasks \
  --step-id step-06-sync-jira
```

### Step 7: Commit Plan to Git & Gate Handoff for `02-exe`
- **Action**: Stage plan file, record provenance, create Git commit, and verify handoff state.
- **Tool**: `tools/plan_runner.py`
- **CLI Command**:
```bash
python3 tools/plan_runner.py commit-plan \
  --file plans/latest_plan.md \
  --branch feature/PROJ-1024 \
  --push \
  --step-id step-07-commit-plan
```
*Verify: Git Commit SHA is embedded into plan metadata and status is `READY FOR 02-EXE`.*
