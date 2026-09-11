---
id: WF-PLAN-ADHOC-001
name: ticketless-planning
workflow_type: adhoc
prerequisites:
  git: true
timeout_seconds: 600
cleanup_on_failure: false
---

# Workflow: Ticketless / Autonomous Planning Runbook

<!-- @implements REQ-WORK-02 -->
<!-- @verifies REQ-WORK-02 -->
<!-- @verifies REQ-HAND-01 -->
<!-- @verifies REQ-HAND-02 -->

## Purpose & Scope
Autonomous planning for ad-hoc features, local refactorings, user prompts, or research spikes without external Jira ticketing dependencies.

---

## Agent Runbook

### Step 1: Intake Natural Language Brief / Spec
- **Action**: Ingest natural language prompt or local specification file.
- **Tool**: `tools/plan_runner.py`
- **CLI Command**:
```bash
python3 tools/plan_runner.py intake \
  --workflow adhoc \
  --title "sqlite-wal-migration" \
  --brief "Enable WAL mode and configure connection pooling for SQLite" \
  --step-id step-01-adhoc-intake
```
*Verify: Ephemeral session initialized with `SCOPE-01` identifier.*

### Step 2: Discover Target Codebase Context
- **Action**: Scan target repository for frameworks, existing models, endpoints, and ADRs.
- **Tool**: `tools/context_discovery.py`
- **CLI Command**:
```bash
python3 tools/plan_runner.py discover \
  --source target-repo/ \
  --step-id step-02-discover-context
```

### Step 3: Author Technical Spec & Architecture (ADR)
- **Action**: Formulate technical decisions and trade-offs using `templates/ADR_TEMPLATE.md`.

### Step 4: Decompose Tasks (`TASK-01`, `TASK-02`) & QA Contracts
- **Action**: Break down change into sequenced, atomic tasks with dependency arrays and test criteria.

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

### Step 6: Commit Plan to Git & Gate Handoff for `02-exe`
- **Action**: Stage plan file, record provenance, create Git commit, and verify handoff state.
- **Tool**: `tools/plan_runner.py`
- **CLI Command**:
```bash
python3 tools/plan_runner.py commit-plan \
  --file plans/latest_plan.md \
  --branch feature/sqlite-wal \
  --push \
  --step-id step-06-commit-plan
```
*Verify: Plan Commit SHA printed and recorded for `02-exe` intake.*
