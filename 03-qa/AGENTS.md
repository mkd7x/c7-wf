# QA Agent Operating Manual (03-qa)

## Mission
The `03-qa` project is dedicated to **clean room software verification**. Autonomous agents operating in this stage ensure that code delivered from `02-exe` is completely verified, builds reliably from clean checkouts, and satisfies all requirements before passing to `04-review`.

All testing is tracked through **live audit logging**, allowing agents to query step outputs, assert relational and HTTP contracts, and produce immutable audit evidence.

---

## Agent Personas & Responsibilities
<!-- @implements REQ-HAND-03 -->

### 1. Clean Room Orchestrator
- **Responsibility**: Workspace isolation, target cloning, and runtime lifecycle coordination.
- **Rules**:
  - Never execute tests against dirty or untracked local trees.
  - Always use `03-qa/target-repo/` as the sandbox.
  - Use `python3 tools/qa_runner.py setup-cleanroom --source <SOURCE>` to prepare the environment.
  - Reset audit state prior to starting new test runs (`python3 tools/qa_runner.py clear-audit`).
  - Always register teardown shell traps (`trap '...' EXIT INT TERM`) to prevent dangling processes or containers.

### 2. Test Execution Specialist
- **Responsibility**: Test discovery, workflow authoring/linting, and step execution.
- **Rules**:
  - Always inspect project documentation first (`TESTING.md`, `README.md`) using `python3 tools/qa_runner.py discover`.
  - Validate workflow markdown runbooks prior to execution using `python3 tools/qa_runner.py lint-workflow --file <path>`.
  - Execute tool commands with `--step-id <name>` to record execution state into the live audit log (`audit.jsonl`).
  - Retrieve dynamic step outputs via `python3 tools/qa_runner.py get-step-output --step <step-id> --query <jsonpath>` rather than complex shell variables.

### 3. Defect & Quality Analyst
- **Responsibility**: Audit trail analysis, reproduction isolation, and formal reporting.
- **Rules**:
  - Inspect test execution logs via `python3 tools/qa_runner.py view-audit`.
  - Compile the final Markdown report directly from the live audit log via `python3 tools/qa_runner.py report`.
  - For failures, isolate minimal reproduction commands, assertion diffs, and database state.
  - Provide an explicit verdict (`PASS` or `FAIL`) and verification checklist for `04-review`.

---

## Standard Operating Procedure (SOP)

```
[Target Source] ──> 1. Setup Cleanroom & Traps (target-repo/)
                            │
                            ▼
                    2. Discover Docs (TESTING.md)
                            │
                            ▼
                    3. Lint Workflow (qa_runner.py lint-workflow)
                            │
                            ▼
                    4. Execute Steps with --step-id (audit.jsonl)
                            │
                            ▼
                    5. Query Step Outputs (qa_runner.py get-step-output)
                            │
                            ▼
                    6. View Audit & Generate Report (reports/*.md)
                            │
                            ▼
                    7. Handoff Evidence to 04-review
```

### Step 1: Initialize Cleanroom & Register Traps
```bash
# 1. Reset sandbox directory
python3 tools/qa_runner.py setup-cleanroom --source <GIT_URL_OR_LOCAL_PATH>

# 2. Reset audit log
python3 tools/qa_runner.py clear-audit

# 3. Register teardown cleanup trap
trap 'pkill -f <PROCESS_NAME> 2>/dev/null; docker stop $(docker ps -q) 2>/dev/null' EXIT INT TERM
```

### Step 2: Discover Testing Instructions
```bash
python3 tools/qa_runner.py discover
```
Review detected frameworks, test configuration files, and recommended commands.

### Step 3: Lint the Target Workflow Runbook
Before executing steps, ensure the runbook conforms to the QA schema:
```bash
python3 tools/qa_runner.py lint-workflow --file workflows/<repo-name>/<workflow_name>.md
```

### Step 4: Execute Workflow Steps with Audit Logging
Every step must specify `--step-id <id>` to record requests, responses, and assertion outcomes into `03-qa/runs/latest/audit.jsonl`.

- **Poll Service Health & Liveness**:
  ```bash
  python3 tools/wait_for_service.py \
    --url http://localhost:5105/health \
    --expect-status 200 \
    --step-id step-01-health-check
  ```
- **Execute HTTP Scenarios & Nested JSONPath Assertions**:
  ```bash
  python3 tools/send_http_req.py http://localhost:5105/api/todolists \
    -X POST \
    -H "Content-Type: application/json" \
    -d '{"title": "Sprint 1"}' \
    --expect-status 201 \
    --expect-json "id" \
    --step-id step-02-create-list
  ```
- **Query State from a Prior Step**:
  ```bash
  # Retrieve generated ID without shell variables
  python3 tools/qa_runner.py get-step-output --step step-02-create-list --query output.body.id
  ```
- **Verify Database Persistence (SQLite or Docker Container)**:
  ```bash
  # SQLite:
  python3 tools/run_sql_cmd.py --db target-repo/test.db --query "SELECT * FROM Users;" --expect-count 1 --step-id step-03-assert-sql

  # Docker Container (SQL Server, Postgres):
  python3 tools/run_sql_cmd.py --driver docker --database tododb --query "SELECT * FROM TodoLists;" --expect-count 3 --step-id step-03-assert-docker-sql
  ```
- **Query Blob Stores**:
  ```bash
  python3 tools/query_blob_storage.py list --dir target-repo/storage/uploads --step-id step-04-assert-blobs
  ```

### Step 5: Review Live Audit Trail
```bash
python3 tools/qa_runner.py view-audit
```
Verify that all steps passed and check duration latencies.

### Step 6: Generate Standardized Report
Compile the final Markdown report directly from the live audit log:
```bash
python3 tools/qa_runner.py report \
  --workflow <name> \
  --source <repo-name> \
  --status PASS \
  --notes "Full cleanroom lifecycle verified with live audit trail."
```

### Step 7: Formulate Handoff to `04-review`
- If **PASS**: Reference the report in `reports/` and notify `04-review` that all functional and relational assertions succeeded.
- If **FAIL**: Extract minimal reproduction details from `audit.jsonl` and hand back to `02-exe` for defect resolution.

---

## Tool Suite Reference Summary

| Tool | Key Capabilities & Flags | Primary Use Case |
|---|---|---|
| [`qa_runner.py`](file:///Users/michaelk/dev/c7-wf/03-qa/tools/qa_runner.py) | `setup-cleanroom`, `discover`, `get-step-output`, `view-audit`, `clear-audit`, `lint-workflow`, `report` | Lifecycle orchestration, audit queries, and reporting |
| [`send_http_req.py`](file:///Users/michaelk/dev/c7-wf/03-qa/tools/send_http_req.py) | `-X`, `-H`, `-d`, `--expect-status`, `--expect-json` (JSONPath/array indexing), `--step-id` | REST API requests & response assertions |
| [`run_sql_cmd.py`](file:///Users/michaelk/dev/c7-wf/03-qa/tools/run_sql_cmd.py) | `--driver sqlite\|docker`, `--database`, `--query`, `--format table\|json\|csv`, `--expect-count`, `--step-id` | Database assertions & migrations |
| [`wait_for_service.py`](file:///Users/michaelk/dev/c7-wf/03-qa/tools/wait_for_service.py) | `--url`, `--tcp`, `--expect-status`, `--timeout`, `--step-id` | Health readiness polling & startup gating |
| [`query_blob_storage.py`](file:///Users/michaelk/dev/c7-wf/03-qa/tools/query_blob_storage.py) | `list`, `exists`, `get`, `put`, `delete`, `--step-id` | Local/mock object storage verification |

---

## Safety & Containment Rules
1. **Cleanroom Isolation**: Target repositories are cloned exclusively into `target-repo/` (ignored by git).
2. **Process Teardown**: Always trap signals (`EXIT`, `INT`, `TERM`) to kill background processes and containers.
3. **No Hardcoded Credentials**: Database passwords in containers are auto-discovered from container metadata.
4. **Transient Logs**: The `03-qa/runs/` directory stores local audit JSONL files and is excluded from git commits.
