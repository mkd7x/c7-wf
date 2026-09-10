# Workflow Authoring Guide

## Overview
Every software project has unique architecture, configuration needs, data schemas, and API contracts. In `03-qa`, workflows are organized **per repository** under `workflows/<repo-name>/<workflow_name>.md`.

This guide provides instructions for AI agents and developers on how to author tailored, reproducible workflows for any project.

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

## Workflow Authoring Lifecycle for AI Agents

When an agent is tasked with testing a repository `<repo-name>` that lacks a pre-existing workflow:

```
1. Discover Project Structure ──> 2. Select Step Templates from examples/
                                              │
                                              ▼
4. Execute Workflow & Report  <── 3. Generate workflows/<repo-name>/<wf>.md
```

### 1. Discover Project Context
Inspect the repository:
```bash
python3 tools/qa_runner.py discover --target target-repo
```
Examine:
- `target-repo/TESTING.md` and `target-repo/README.md`
- Port numbers, configuration files (`.env.example`), and database connections
- Package scripts or Makefiles

### 2. Choose and Tailor Steps
Assemble workflow steps using the reference guides in `workflows/examples/`:
- **For API endpoints**: Consult [examples/http-request-step.md](examples/http-request-step.md)
- **For SQLite/relational state**: Consult [examples/sql-seed-step.md](examples/sql-seed-step.md)
- **For file/blob uploads**: Consult [examples/blob-storage-step.md](examples/blob-storage-step.md)
- **For server startup**: Consult [examples/health-polling-step.md](examples/health-polling-step.md)

### 3. Step Specification Standard
Every step in the generated workflow should contain:
1. **Step Name & Objective**
2. **Action Type** (Setup, SQL, HTTP, Blob, Healthcheck, Teardown)
3. **Tool Used** (e.g. `tools/send_http_req.py`)
4. **Structured Specification** (JSON, SQL, or parameters)
5. **Exact CLI Command** (Ready to copy or execute)

### 4. Create the Project Workflow
Write the generated workflow to:
`workflows/<repo-name>/<workflow_name>.md`

### 5. Execute and Record
Execute the steps in order and generate the report:
```bash
python3 tools/qa_runner.py report --workflow <name> --source <repo-name> --status PASS --notes "Custom workflow executed."
```
