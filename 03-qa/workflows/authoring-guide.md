# Workflow Authoring Guide

## Overview
Every software project has unique architecture, configuration needs, data schemas, and API contracts. In `03-qa`, workflows are organized **per repository** under `workflows/<repo-name>/<workflow_name>.md`.

Workflows are designed as **agent-executable runbooks** with machine-readable metadata, live audit logging, step output retrieval, and structured assertions.

---

## Directory Organization Convention

```
workflows/
├── README.md                      # Directory catalog
├── authoring-guide.md             # This authoring manual
├── examples/                      # Reusable step definitions & patterns
│   ├── http-request-step.md       # JSON HTTP call schema & assertions
│   ├── sql-seed-step.md           # Database seeding & row count checks
│   ├── blob-storage-step.md       # Blob storage inspection & assertions
│   ├── health-polling-step.md     # Server launch & health readiness polling
│   └── workflow-template.md       # Scaffold template for new workflows
└── <repo-name>/                   # Concrete workflows for a specific repository
    ├── smoke-test.md
    ├── unit-test.md
    ├── integration-test.md
    └── regression-test.md
```

---

## Standard Workflow Specification

Every workflow must include three core structural components:

### 1. YAML Frontmatter Metadata
Workflows must declare prerequisites and timeouts at the top of the file:
```yaml
---
id: WF-TODO-001
name: aspire-orchestration-e2e
target: mkd7x/todo-api
prerequisites:
  docker: true
  dotnet: ">=10.0"
environment:
  ASPNETCORE_ENVIRONMENT: Development
timeout_seconds: 300
cleanup_on_failure: true
---
```

### 2. Mandatory Teardown Traps
To ensure background processes or containers do not linger if a step fails:
```bash
# Register shell cleanup trap
trap 'pkill -f TodoApi.AppHost 2>/dev/null; docker stop $(docker ps -q --filter "ancestor=mcr.microsoft.com/mssql/server:2022-latest") 2>/dev/null' EXIT INT TERM
```

### 3. Step IDs & Live Audit Logging
Every tool command must provide a unique `--step-id <name>`. This automatically logs the complete HTTP request/response or SQL output into `03-qa/runs/latest/audit.jsonl` and `execution_state.json`.

```bash
# Example Step 5:
python3 tools/send_http_req.py http://localhost:5105/api/todolists \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{"title": "Sprint Backlog", "colour": "#FF5722"}' \
  --step-id step-05-create-list \
  --expect-status 201 \
  --expect-json "id"
```

Subsequent steps can inspect previous step output without brittle shell variables:
```bash
# Retrieve output or specific field from a prior step:
python3 tools/qa_runner.py get-step-output --step step-05-create-list --query output.body.id
```

---

## Workflow Authoring Lifecycle for AI Agents

```
1. Discover Target Context ──> 2. Scaffold Workflow with Frontmatter & Steps
                                            │
                                            ▼
4. Execute with Audit Log  <── 3. Lint with qa_runner.py lint-workflow
```

### 1. Discover Project Context
Inspect the repository:
```bash
python3 tools/qa_runner.py discover --target target-repo
```

### 2. Author Workflow Runbook
Create `workflows/<repo-name>/<workflow_name>.md` following [examples/workflow-template.md](examples/workflow-template.md).

### 3. Lint the Workflow
Verify tool references, valid CLI options, and YAML frontmatter:
```bash
python3 tools/qa_runner.py lint-workflow --file workflows/<repo-name>/<workflow_name>.md
```

### 4. Execute and Generate Report
When all steps complete, compile the final report directly from the live audit log:
```bash
python3 tools/qa_runner.py report \
  --workflow <name> \
  --source <repo-name> \
  --status PASS \
  --notes "Full workflow verified via live audit log."
```
