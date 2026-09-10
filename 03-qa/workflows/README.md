# QA Workflows: Per-Project Runbooks & Authoring System

## Overview
Workflows in `03-qa` are organized **per repository** to allow fully custom testing flows for each project without collisions, while providing reusable step guides and templates in `examples/`.

```
03-qa/workflows/
├── README.md                      # This directory guide
├── authoring-guide.md             # How to create a custom workflow for any repository
├── clean-room-guide.md            # Universal clean-room SOP
├── examples/                      # Reusable step definitions & patterns
│   ├── http-request-step.md       # JSON HTTP call schema & send_http_req.py
│   ├── sql-seed-step.md           # Database seeding & run_sql_cmd.py
│   ├── blob-storage-step.md       # Blob storage assertions & query_blob_storage.py
│   ├── health-polling-step.md     # Server launch & wait_for_service.py
│   └── workflow-template.md       # Scaffold template for new workflows
└── <repo-name>/                   # Concrete workflows for specific repositories
    └── sample-project/            # Fixture project workflows
        ├── smoke-test.md
        ├── unit-test.md
        ├── integration-test.md
        └── regression-test.md
```

---

## How AI Agents Execute Workflows

When an agent is assigned to test a repository `<repo-name>`:

1. **Check for Existing Workflow**:
   Look for `workflows/<repo-name>/<workflow_name>.md`.
2. **If Workflow Exists**:
   Follow the runbook step-by-step, executing the tailored CLI commands.
3. **If Workflow Does Not Exist**:
   - Run `python3 tools/qa_runner.py discover` to inspect the project.
   - Read [authoring-guide.md](authoring-guide.md) and relevant guides in [examples/](examples/).
   - Generate `workflows/<repo-name>/<workflow_name>.md`.
   - Execute the workflow and compile the report via `python3 tools/qa_runner.py report`.

---

## Tailored Step Guides in `examples/`

| Step Guide | Action Type | Primary Tool | Description |
| :--- | :--- | :--- | :--- |
| [http-request-step.md](examples/http-request-step.md) | HTTP Request | `tools/send_http_req.py` | JSON payload schema, headers, status codes, and body assertions |
| [sql-seed-step.md](examples/sql-seed-step.md) | SQL Seeding / Query | `tools/run_sql_cmd.py` | Database migrations, seeding, and row count assertions |
| [blob-storage-step.md](examples/blob-storage-step.md) | Blob Storage | `tools/query_blob_storage.py` | Object existence, listing, upload, and deletion checks |
| [health-polling-step.md](examples/health-polling-step.md) | Readiness Check | `tools/wait_for_service.py` | Healthcheck URL and TCP port polling with backoff |
| [workflow-template.md](examples/workflow-template.md) | Blank Scaffold | Any | Starting template for a new project workflow |
