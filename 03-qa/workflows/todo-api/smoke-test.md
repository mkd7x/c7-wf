# Workflow: Smoke Test for `todo-api`

<!-- @verifies REQ-WORK-01 -->
<!-- @verifies REQ-TOOL-WAIT -->
<!-- @verifies REQ-TOOL-HTTP -->

## Purpose & Scope
Fast sanity and smoke verification for the `todo-api` project. Executes automated unit tests, boots the API service in cleanroom mode, and verifies the `/alive` health probe and `/api/todolists` root query.

---

## Agent Runbook: Step-by-Step

### Step 1: Cleanroom Setup
```bash
python3 tools/qa_runner.py setup-cleanroom --source https://github.com/mkd7x/todo-api.git
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

# 2. Poll liveness
python3 tools/wait_for_service.py --url http://localhost:5105/alive --expect-status 200 --timeout 60
```

### Step 4: Verify Default Todo Lists Endpoint
```bash
python3 tools/send_http_req.py http://localhost:5105/api/todolists --expect-status 200 --expect-contains "Work & Projects"
```

### Step 5: Teardown & Report Compilation
```bash
pkill -f TodoApi.ApiService
python3 tools/qa_runner.py report \
  --workflow smoke \
  --source todo-api \
  --status PASS \
  --notes "Smoke test clean: 19 unit tests passed, service booted healthy, and todolists endpoint returned seed data."
```
