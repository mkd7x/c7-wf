---
id: WF-TODO-000
name: smoke-test
target: mkd7x/todo-api
prerequisites:
  dotnet: ">=10.0"
environment:
  ASPNETCORE_ENVIRONMENT: Development
  USE_SQLITE: "true"
timeout_seconds: 120
cleanup_on_failure: true
---

# Workflow: Smoke Test for `todo-api`

<!-- @verifies REQ-WORK-01 -->
<!-- @verifies REQ-TOOL-WAIT -->
<!-- @verifies REQ-TOOL-HTTP -->

## Purpose & Scope
Fast sanity and smoke verification for the `todo-api` project. Executes automated unit tests, boots the API service in cleanroom mode, and verifies the `/alive` health probe and `/api/todolists` root query.

---

## Agent Runbook: Step-by-Step

### Step 1: Cleanroom Setup & Register Trap
```bash
python3 tools/qa_runner.py setup-cleanroom --source https://github.com/mkd7x/todo-api.git

# Register failure cleanup trap
trap 'pkill -f TodoApi.ApiService 2>/dev/null' EXIT INT TERM
```

### Step 2: Execute Core Unit Tests
- **Action**: Unit Test Suite
- **Command**:
```bash
dotnet test target-repo/tests/TodoApi.Application.UnitTests
```
*Assert: All 19 unit tests pass.*

### Step 3: Launch Service & Poll Liveness
```bash
# 1. Start service in background
ASPNETCORE_ENVIRONMENT=Development USE_SQLITE=true dotnet run --project target-repo/src/TodoApi.ApiService --launch-profile http &

# 2. Poll liveness with audit logging
python3 tools/wait_for_service.py \
  --url http://localhost:5105/alive \
  --expect-status 200 \
  --timeout 60 \
  --step-id step-03-liveness
```

### Step 4: Verify Default Todo Lists Endpoint
```bash
python3 tools/send_http_req.py http://localhost:5105/api/todolists \
  --expect-status 200 \
  --expect-contains "Work & Projects" \
  --step-id step-04-seed-lists
```

### Step 5: Teardown & Report Compilation
```bash
pkill -f TodoApi.ApiService 2>/dev/null
python3 tools/qa_runner.py report \
  --workflow smoke \
  --source todo-api \
  --status PASS \
  --notes "Smoke test clean: 19 unit tests passed, service booted healthy, and todolists endpoint returned seed data."
```
