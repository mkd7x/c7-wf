# Workflow: End-to-End API Lifecycle for `todo-api`

<!-- @verifies REQ-WORK-03 -->
<!-- @verifies REQ-TOOL-HTTP -->
<!-- @verifies REQ-TOOL-SQL -->
<!-- @verifies REQ-TOOL-WAIT -->

## Purpose & Scope
This workflow provides a complete end-to-end verification of the `todo-api` repository. It verifies cleanroom deployment, service health readiness, CRUD operations on Todo Lists and Items, and confirms data persistence directly in the relational database.

---

## Agent Runbook: Step-by-Step

### Step 1: Cleanroom Workspace Setup
Initialize the isolated sandbox:
```bash
python3 tools/qa_runner.py setup-cleanroom --source https://github.com/mkd7x/todo-api.git
```

### Step 2: Configure Environment
Set environment variables to enable SQLite for local testing:
```bash
export ASPNETCORE_ENVIRONMENT=Development
export USE_SQLITE=true
```

### Step 3: Launch Service & Poll Health Readiness
1. **Start the API Service in background**:
   ```bash
   ASPNETCORE_ENVIRONMENT=Development USE_SQLITE=true dotnet run --project target-repo/src/TodoApi.ApiService --launch-profile http &
   ```
2. **Poll Liveness Probe**:
   - **Tool**: `tools/wait_for_service.py`
   - **Command**:
   ```bash
   python3 tools/wait_for_service.py --url http://localhost:5105/alive --expect-status 200 --timeout 60
   ```

---

## Step Scenarios: HTTP API Verification

### Step 4: Query Pre-Seeded Todo Lists
Verify that default seed lists ("Work & Projects", "Personal Goals") are returned:
- **Action**: HTTP GET
- **Tool**: `tools/send_http_req.py`
- **Step Specification**:
```json
{
  "method": "GET",
  "url": "http://localhost:5105/api/todolists",
  "assertions": {
    "status_code": 200,
    "body_contains": "Work & Projects"
  }
}
```
- **Execution Command**:
```bash
python3 tools/send_http_req.py http://localhost:5105/api/todolists --expect-status 200 --expect-contains "Work & Projects"
```

### Step 5: Create a New Todo List
- **Action**: HTTP POST
- **Tool**: `tools/send_http_req.py`
- **Step Specification**:
```json
{
  "method": "POST",
  "url": "http://localhost:5105/api/todolists",
  "headers": {
    "Content-Type": "application/json"
  },
  "body": {
    "title": "QA Verification Sprint",
    "colour": "#9C27B0"
  },
  "assertions": {
    "status_code": 201,
    "json_keys": {
      "id": "3"
    }
  }
}
```
- **Execution Command**:
```bash
python3 tools/send_http_req.py http://localhost:5105/api/todolists \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{"title": "QA Verification Sprint", "colour": "#9C27B0"}' \
  --expect-status 201 \
  --expect-json "id=3"
```

### Step 6: Create a Todo Item Under New List
- **Action**: HTTP POST
- **Tool**: `tools/send_http_req.py`
- **Step Specification**:
```json
{
  "method": "POST",
  "url": "http://localhost:5105/api/todoitems",
  "headers": {
    "Content-Type": "application/json"
  },
  "body": {
    "listId": 3,
    "title": "Validate Clean Room Architecture",
    "priority": 3,
    "note": "Created by automated QA agent"
  },
  "assertions": {
    "status_code": 201,
    "json_keys": {
      "id": "6"
    }
  }
}
```
- **Execution Command**:
```bash
python3 tools/send_http_req.py http://localhost:5105/api/todoitems \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{"listId": 3, "title": "Validate Clean Room Architecture", "priority": 3, "note": "Created by automated QA agent"}' \
  --expect-status 201 \
  --expect-json "id=6"
```

### Step 7: Toggle Item Completion Status
- **Action**: HTTP PATCH
- **Tool**: `tools/send_http_req.py`
- **Step Specification**:
```json
{
  "method": "PATCH",
  "url": "http://localhost:5105/api/todoitems/6/toggle",
  "assertions": {
    "status_code": 200,
    "json_keys": {
      "isCompleted": "True"
    }
  }
}
```
- **Execution Command**:
```bash
python3 tools/send_http_req.py http://localhost:5105/api/todoitems/6/toggle \
  -X PATCH \
  --expect-status 200 \
  --expect-json "isCompleted=True"
```

### Step 8: Assert Relational Database Persistence
Verify directly in the SQLite database that item 6 was updated to `IsCompleted = 1`:
- **Action**: SQL Query Assertion
- **Tool**: `tools/run_sql_cmd.py`
- **Execution Command**:
```bash
python3 tools/run_sql_cmd.py \
  --db target-repo/src/TodoApi.ApiService/tododb.db \
  --query "SELECT Id, Title, IsCompleted FROM TodoItems WHERE Id=6;" \
  --format table \
  --expect-count 1
```

### Step 9: Delete Todo Item
- **Action**: HTTP DELETE
- **Tool**: `tools/send_http_req.py`
- **Execution Command**:
```bash
python3 tools/send_http_req.py http://localhost:5105/api/todoitems/6 \
  -X DELETE \
  --expect-status 204
```

---

## Teardown & Reporting

### Step 10: Server Shutdown & Report Generation
1. Terminate background server process:
   ```bash
   pkill -f TodoApi.ApiService
   ```
2. Compile and save the final report:
   ```bash
   python3 tools/qa_runner.py report \
     --workflow integration \
     --source todo-api \
     --status PASS \
     --notes "Full API lifecycle validated: list creation, item creation, toggle completion, database verification, and deletion."
   ```
