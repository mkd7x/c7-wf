# Workflow Authoring Guide (`01-plan`)

## Overview
All planning runbooks in `01-plan` are structured as **machine-executable agent runbooks**. Each runbook must define clear prerequisites, explicit step sequences, CLI invocations with `--step-id`, and validation assertions.

---

## Required Workflow Structure

### 1. YAML Frontmatter
Every workflow file must begin with valid YAML frontmatter:
```yaml
---
id: WF-PLAN-JIRA-001
name: jira-driven-planning
workflow_type: jira # jira | adhoc
prerequisites:
  git: true
timeout_seconds: 600
cleanup_on_failure: false
---
```

### 2. Traceability Annotations
Workflows must declare the requirements they implement or verify:
```markdown
<!-- @implements REQ-WORK-01 -->
<!-- @verifies REQ-WORK-01 -->
```

### 3. Numbered Step Sequence
Each step must specify:
- **Action**: What the agent is doing
- **Tool**: The CLI utility or template involved
- **CLI Command**: Explicit command line with `--step-id <unique-step-id>`
- **Verification**: What output artifact or check confirms step success

---

## Linting Workflows

Before committing any new planning workflow, validate it using the linter:
```bash
python3 tools/plan_runner.py lint-workflow --file workflows/my-workflow.md
```
Strict verification:
```bash
python3 tools/plan_runner.py lint-workflow --file workflows/my-workflow.md --strict
```
