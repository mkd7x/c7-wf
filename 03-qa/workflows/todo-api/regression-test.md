---
id: WF-TODO-REG-000
name: regression
target: mkd7x/todo-api
prerequisites:
  dotnet: ">=10.0"
  docker: true
environment:
  ASPNETCORE_ENVIRONMENT: Development
  DOTNET_ENVIRONMENT: Development
  API_BASE: http://localhost:5105
timeout_seconds: 900
cleanup_on_failure: true
---

# Workflow: Comprehensive API Regression Suite for `todo-api`

<!-- @implements REQ-WORK-04 -->
<!-- @verifies REQ-WORK-04 -->
<!-- @verifies REQ-API-001 -->
<!-- @verifies REQ-API-002 -->
<!-- @verifies REQ-API-003 -->
<!-- @verifies REQ-API-004 -->

## Purpose & Scope
Master regression runbook for the `mkd7x/todo-api` HTTP surface. It brings up the Aspire
environment (SQL Server 2022 + `TodoApi.ApiService`), then drives the focused regression suites
against the live API at `http://localhost:5105`.

| Suite | File | Covers |
| :--- | :--- | :--- |
| Todo Lists | [regression-todolists.md](regression-todolists.md) | `REQ-LIST-001..005`, `REQ-API-001` |
| Todo Items | [regression-todoitems.md](regression-todoitems.md) | `REQ-ITEM-002..006`, `REQ-API-001` |
| Query / Filtering | [regression-query.md](regression-query.md) | `REQ-ITEM-001`, `REQ-LIST-001` |
| Error Handling | [regression-errors.md](regression-errors.md) | `REQ-API-002` |
| Observability | [regression-observability.md](regression-observability.md) | `REQ-API-003`, `REQ-API-004` |

**Expected baseline**: all suites `PASS` except the `REQ-API-002` `errors` dictionary check in
`regression-errors.md`, which is a known spec deviation (see that file's *Known Deviations*).

---

## Agent Runbook

### Step 1: Initialize Cleanroom
```bash
python3 tools/qa_runner.py setup-cleanroom --source https://github.com/mkd7x/todo-api.git
```

### Step 2: Discover Test Instructions
```bash
python3 tools/qa_runner.py discover --target target-repo
```

### Step 3: Reset Audit Log & Register Teardown Trap
```bash
# 1. Reset the live audit log so the report reflects only this regression run
#    (prior run is archived to runs/latest/audit.<run-id>.jsonl, not deleted)
python3 tools/qa_runner.py clear-audit

# 2. Register teardown trap for the Aspire AppHost and its SQL Server container
trap 'pkill -f "TodoApi.AppHost" 2>/dev/null; docker stop $(docker ps -q --filter "ancestor=mcr.microsoft.com/mssql/server:2022-latest") 2>/dev/null; docker rm -f $(docker ps -aq --filter "ancestor=mcr.microsoft.com/mssql/server:2022-latest") 2>/dev/null' EXIT INT TERM
```

### Step 4: Build the Solution
```bash
python3 tools/qa_runner.py exec --cmd "dotnet build TodoApi.slnx -c Release --nologo" --timeout 300 --step-id step-reg-build
```
*Expected: `Build succeeded. 0 Error(s)`.*

### Step 5: Start Aspire AppHost & Wait for the API
> **Note:** the bundled Aspire CLI always launches the AppHost in `Debug`; do not pass
> `-c Release --no-build` to the AppHost. The API keeps its fixed launch-profile port `5105`.
```bash
# 1. Start the Aspire AppHost (SQL Server 2022 + apiservice) in the background
python3 tools/qa_runner.py exec --cmd "dotnet run --project src/TodoApi.AppHost --launch-profile http > /tmp/todo-api-aspire.log 2>&1 &" --step-id step-reg-apphost-start

# 2. Wait for the API readiness probe (first run pulls the SQL Server image)
python3 tools/wait_for_service.py \
  --url http://localhost:5105/health \
  --expect-status 200 \
  --timeout 300 \
  --interval 2.0 \
  --step-id step-reg-00-api-ready
```
*Expected: `[✓] Endpoint http://localhost:5105/health is healthy (HTTP 200)`.*

### Step 6: Execute the Regression Suites
Run each focused runbook in order against the live API. Keep the same audit log so the final
report aggregates every step.

1. [regression-todolists.md](regression-todolists.md) — Todo List CRUD lifecycle.
2. [regression-todoitems.md](regression-todoitems.md) — Todo Item CRUD + toggle lifecycle.
3. [regression-query.md](regression-query.md) — pagination, filtering, search, clamping.
4. [regression-errors.md](regression-errors.md) — 400/404 RFC 7807 contracts.
5. [regression-observability.md](regression-observability.md) — health, OpenAPI, Scalar, root.

### Step 7: Teardown & Compile Report
```bash
# Explicit teardown (also enforced by the Step 3 trap)
pkill -f "TodoApi.AppHost" 2>/dev/null
docker stop $(docker ps -q --filter "ancestor=mcr.microsoft.com/mssql/server:2022-latest") 2>/dev/null
docker rm -f $(docker ps -aq --filter "ancestor=mcr.microsoft.com/mssql/server:2022-latest") 2>/dev/null

# Compile the aggregate report from the live audit log
python3 tools/qa_runner.py report \
  --workflow regression \
  --source mkd7x/todo-api \
  --status PASS \
  --notes "Comprehensive API regression suite executed against http://localhost:5105."
```

---

## Failure Handling
- If Step 5 times out, inspect `/tmp/todo-api-aspire.log` and confirm Docker Desktop is running.
- The audit log aggregates every `send_http_req.py --step-id` and `wait_for_service.py --step-id`
  step, so a single failed assertion yields an overall `FAIL` report with the failing JSON path.
- The Step 3 trap removes the AppHost process and SQL Server container on any exit.
