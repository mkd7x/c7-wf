---
id: WF-TEMPLATE-001
name: workflow-template
target: sample-project
prerequisites:
  python: ">=3.10"
environment:
  ENV: test
timeout_seconds: 180
cleanup_on_failure: true
---

# Workflow: [Workflow Name] for `[Repo Name]`

<!-- @verifies REQ-WORK-01 -->

## Purpose & Scope
Describe the objective of this workflow for `[Repo Name]`.

---

## Agent Runbook

### Step 1: Cleanroom Setup
```bash
python3 tools/qa_runner.py setup-cleanroom --source [TARGET_SOURCE]
```

### Step 2: Configure Environment & Register Teardown Trap
Set test environment variables and register a cleanup trap:
```bash
export PORT=8080
export DB_PATH="target-repo/test.db"

# Register teardown trap
trap 'pkill -f [PROCESS_NAME] 2>/dev/null' EXIT INT TERM
```

### Step 3: Database Seeding (if applicable)
```bash
python3 tools/run_sql_cmd.py \
  --db target-repo/test.db \
  --file fixtures/seed.sql \
  --step-id step-03-seed-db
```

### Step 4: Start Application & Poll Health
```bash
# 1. Start application in background (redirect so the launcher never blocks)
python3 tools/qa_runner.py exec --cmd "[START_COMMAND] > /tmp/app.log 2>&1 &" --step-id step-04-app-start

# 2. Wait for healthcheck with audit logging
python3 tools/wait_for_service.py \
  --url http://127.0.0.1:8080/health \
  --expect-status 200 \
  --timeout 60 \
  --step-id step-04-health-poll
```

### Step 5: Test Execution & Assertions
```bash
python3 tools/send_http_req.py http://127.0.0.1:8080/api/v1/[ENDPOINT] \
  -X [METHOD] \
  -H "Content-Type: application/json" \
  -d '[PAYLOAD_JSON]' \
  --expect-status 200 \
  --expect-json "[KEY]=[VALUE]" \
  --step-id step-05-api-test
```

### Step 6: Query Step State (if dependent steps exist)
```bash
# Inspect generated value from step 5:
python3 tools/qa_runner.py get-step-output --step step-05-api-test --query output.body.id
```

### Step 7: Teardown & Report Compilation
```bash
# Compile report directly from live audit log
python3 tools/qa_runner.py report \
  --workflow [WORKFLOW_NAME] \
  --source [REPO_NAME] \
  --status PASS \
  --notes "Completed [Workflow Name]."
```
