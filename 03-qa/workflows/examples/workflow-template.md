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

### Step 2: Configure Environment & Credentials
Set environment variables or create `target-repo/.env.test`:
```bash
export PORT=8080
export DB_PATH="target-repo/test.db"
```

### Step 3: Database Seeding (if applicable)
```bash
python3 tools/run_sql_cmd.py --db target-repo/test.db --file fixtures/seed.sql
```

### Step 4: Start Application & Poll Health
```bash
# 1. Start application
python3 tools/qa_runner.py exec --cmd "[START_COMMAND] &"

# 2. Wait for healthcheck
python3 tools/wait_for_service.py --url http://127.0.0.1:8080/health --expect-status 200 --timeout 60
```

### Step 5: Test Execution & Assertions
```bash
python3 tools/send_http_req.py http://127.0.0.1:8080/api/v1/[ENDPOINT] \
  -X [METHOD] \
  -H "Content-Type: application/json" \
  -d '[PAYLOAD_JSON]' \
  --expect-status 200 \
  --expect-json "[KEY]=[VALUE]"
```

### Step 6: Teardown & Report Compilation
```bash
# Kill background server and clean up sockets
python3 tools/qa_runner.py report --workflow [WORKFLOW_NAME] --source [REPO_NAME] --status PASS --notes "Completed [Workflow Name]."
```
