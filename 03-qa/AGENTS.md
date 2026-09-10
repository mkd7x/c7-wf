# QA Agent Operating Manual (03-qa)

## Mission
The `03-qa` project is dedicated to **clean room software verification**. Autonomous agents operating in this stage ensure that code delivered from `02-exe` is completely verified, builds reliably from clean checkouts, and satisfies all requirements before passing to `04-review`.

---

## Agent Personas & Responsibilities
<!-- @implements REQ-HAND-03 -->

### 1. Clean Room Orchestrator
- **Responsibility**: Workspace isolation, target cloning, and workflow coordination.
- **Rules**:
  - Never execute tests against dirty or untracked local trees.
  - Always use `03-qa/target-repo/` as the sandbox.
  - Use `python3 tools/qa_runner.py setup-cleanroom --source <SOURCE>` to prepare the environment.

### 2. Test Execution Specialist
- **Responsibility**: Test discovery and execution.
- **Rules**:
  - Always inspect project documentation first (`TESTING.md`, `README.md`).
  - Use `python3 tools/qa_runner.py discover` to inspect test configuration.
  - Run the appropriate workflow (`smoke`, `unit`, `integration`, `regression`).

### 3. Defect & Quality Analyst
- **Responsibility**: Log analysis, repro case isolation, and reporting.
- **Rules**:
  - Format all results into `reports/` using the standard format.
  - For failures, isolate minimal reproduction commands, stack traces, and affected components.
  - Provide an explicit verdict (`PASS` or `FAIL`) and handoff recommendation for `04-review`.

---

## Standard Operating Procedure (SOP)

```
[Target Source] ──> 1. Setup Cleanroom (target-repo/)
                            │
                            ▼
                    2. Discover Docs (TESTING.md)
                            │
                            ▼
                    3. Run Workflow (tools/qa_runner.py)
                            │
                            ▼
                    4. Generate Report (reports/*.md)
                            │
                            ▼
                    5. Handoff to 04-review
```

### Step 1: Initialize Cleanroom
```bash
python3 tools/qa_runner.py setup-cleanroom --source <GIT_URL_OR_LOCAL_PATH>
```

### Step 2: Discover Testing Instructions
```bash
python3 tools/qa_runner.py discover
```
Review detected documentation files and recommended commands.

### Step 3: Execute Target Workflow Runbook
Agents execute the workflow steps specified in `workflows/<workflow-name>.md` using the specialized CLI tool suite:
- **Seed Relational State**:
  ```bash
  python3 tools/run_sql_cmd.py --db target-repo/test.db --file fixtures/seed.sql
  ```
- **Poll Service Readiness**:
  ```bash
  python3 tools/wait_for_service.py --url http://127.0.0.1:8080/health --expect-status 200
  ```
- **Dispatch HTTP Scenarios**:
  ```bash
  python3 tools/send_http_req.py http://127.0.0.1:8080/api/endpoint -X POST -d '{"key":"val"}' --expect-status 201
  ```
- **Query Blob Stores**:
  ```bash
  python3 tools/query_blob_storage.py list --dir target-repo/storage/uploads
  ```

### Step 4: Verify and Document Handoff
1. Ensure the markdown report exists in `reports/` via:
   ```bash
   python3 tools/qa_runner.py report --workflow <name> --status PASS --notes "Verification passed."
   ```
2. Check the overall status in the report:
   - If `PASS`: formulate sign-off notice for `04-review`.
   - If `FAIL`: format defect analysis and assign back to `02-exe` for resolution.

---

## Safety & Isolation Rules
- **No Global Leakage**: Do not install packages globally; use sandbox virtual environments or project-local node modules.
- **No Leaked Credentials**: Never include `.env` or API tokens in reports.
- **Timeout Containment**: Individual test runs should have appropriate timeouts (default: 180s) to avoid hanging processes.
