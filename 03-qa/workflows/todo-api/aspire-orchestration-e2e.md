---
id: WF-TODO-002
name: aspire-orchestration-e2e
target: mkd7x/todo-api
prerequisites:
  docker: true
  dotnet: ">=10.0"
environment:
  ASPNETCORE_ENVIRONMENT: Development
timeout_seconds: 300
cleanup_on_failure: true
---

# Workflow: Aspire Orchestration End-to-End for `todo-api`

<!-- @verifies REQ-WORK-03 -->
<!-- @verifies REQ-TOOL-HTTP -->
<!-- @verifies REQ-TOOL-SQL -->
<!-- @verifies REQ-TOOL-WAIT -->

## Purpose & Scope
This workflow validates full **.NET Aspire Orchestration** for the `mkd7x/todo-api` repository running with live **Docker container dependencies**. It verifies:
1. Aspire AppHost startup and container provisioning (Microsoft SQL Server 2022).
2. Aspire Dashboard and OTLP telemetry service availability.
3. Health check and liveness readiness probes.
4. End-to-end CRUD operations on Todo Lists and Items.
5. Verification of data persistence in containerized SQL Server using `run_sql_cmd.py --driver docker`.
6. Scalar OpenAPI 3.1 documentation accessibility.

---

## Agent Runbook: Step-by-Step

### Step 1: Verify Prerequisites & Register Teardown Trap
Ensure Docker is running and .NET 10 SDK is available, and set up a failure trap:
```bash
docker info
dotnet --version

# Register failure cleanup trap
trap 'pkill -f TodoApi.AppHost 2>/dev/null; pkill -f TodoApi.ApiService 2>/dev/null' EXIT INT TERM
```

### Step 2: Launch Aspire AppHost
Start the orchestrator in the background:
```bash
dotnet run --project target-repo/todo-api/src/TodoApi.AppHost --launch-profile http &
```

Aspire will:
- Spin up the Microsoft SQL Server 2022 container (`sql`).
- Wait for SQL Server to report healthy.
- Launch `TodoApi.ApiService` and inject the connection string for database `tododb`.
- Start the Aspire Dashboard and OpenTelemetry collector.

### Step 3: Poll Service Health Readiness
Poll the API service health endpoint using `wait_for_service.py`:
- **Tool**: `tools/wait_for_service.py`
- **Commands**:
```bash
python3 tools/wait_for_service.py \
  --url http://localhost:5105/alive \
  --expect-status 200 \
  --timeout 60 \
  --step-id step-03-alive-check

python3 tools/wait_for_service.py \
  --url http://localhost:5105/health \
  --expect-status 200 \
  --timeout 60 \
  --step-id step-03-health-check
```

---

## Step Scenarios: HTTP API Verification

### Step 4: Query Default Seeded Todo Lists
Verify that EF Core migrations and initial seeding executed on SQL Server:
- **Tool**: `tools/send_http_req.py`
- **Execution Command**:
```bash
python3 tools/send_http_req.py http://localhost:5105/api/todolists \
  --expect-status 200 \
  --expect-contains "Work & Projects" \
  --expect-contains "Personal Goals" \
  --step-id step-04-query-seed-lists
```

### Step 5: Create a New Todo List
- **Action**: HTTP POST
- **Tool**: `tools/send_http_req.py`
- **Execution Command**:
```bash
python3 tools/send_http_req.py http://localhost:5105/api/todolists \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{"title": "Aspire Production Verification", "colour": "#673AB7"}' \
  --expect-status 201 \
  --expect-json "id" \
  --step-id step-05-create-list
```

### Step 6: Query Generated List ID (Audit State Inspection)
The agent retrieves the generated ID from the live audit state:
```bash
python3 tools/qa_runner.py get-step-output --step step-05-create-list --query output.body.id
```

### Step 7: Create a Todo Item Under New List
- **Action**: HTTP POST
- **Tool**: `tools/send_http_req.py`
- **Execution Command**:
```bash
python3 tools/send_http_req.py http://localhost:5105/api/todoitems \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{"listId": 3, "title": "Verify Aspire SQL Server Container", "priority": 3, "note": "Orchestrated via Aspire AppHost"}' \
  --expect-status 201 \
  --expect-json "id" \
  --step-id step-07-create-item
```

### Step 8: Toggle Item Completion Status
- **Action**: HTTP PATCH
- **Tool**: `tools/send_http_req.py`
- **Execution Command**:
```bash
python3 tools/send_http_req.py http://localhost:5105/api/todoitems/6/toggle \
  -X PATCH \
  --expect-status 200 \
  --expect-json "isCompleted=true" \
  --step-id step-08-toggle-item
```

### Step 9: Query Filtered & Paginated Items
- **Action**: HTTP GET
- **Tool**: `tools/send_http_req.py`
- **Execution Command**:
```bash
python3 tools/send_http_req.py "http://localhost:5105/api/todoitems?listId=3" \
  -X GET \
  --expect-status 200 \
  --expect-json "items[0].isCompleted=true" \
  --expect-json "items[0].title=Verify Aspire SQL Server Container" \
  --step-id step-09-query-items
```

### Step 10: Verify Containerized SQL Server Persistence
Execute SQL directly against the containerized database using `run_sql_cmd.py`:
- **Tool**: `tools/run_sql_cmd.py`
- **Execution Command**:
```bash
python3 tools/run_sql_cmd.py \
  --driver docker \
  --database tododb \
  --query "SELECT Id, Title, Colour FROM TodoLists;" \
  --expect-count 3 \
  --step-id step-10-assert-sql-lists

python3 tools/run_sql_cmd.py \
  --driver docker \
  --database tododb \
  --query "SELECT Id, ListId, Title, IsCompleted FROM TodoItems WHERE Id=6;" \
  --expect-count 1 \
  --step-id step-10-assert-sql-items
```

### Step 11: Delete Todo Item
- **Action**: HTTP DELETE
- **Tool**: `tools/send_http_req.py`
- **Execution Command**:
```bash
python3 tools/send_http_req.py http://localhost:5105/api/todoitems/6 \
  -X DELETE \
  --expect-status 204 \
  --step-id step-11-delete-item
```

### Step 12: Verify Scalar OpenAPI Documentation
- **Action**: HTTP GET
- **Tool**: `tools/send_http_req.py`
- **Execution Command**:
```bash
python3 tools/send_http_req.py http://localhost:5105/scalar/v1 \
  -X GET \
  --expect-status 200 \
  --expect-contains "Scalar" \
  --step-id step-12-scalar-docs
```

---

## Teardown & Reporting

### Step 13: Shutdown Aspire AppHost & Clean Containers
1. Terminate the Aspire AppHost process:
   ```bash
   pkill -f TodoApi.AppHost 2>/dev/null
   pkill -f TodoApi.ApiService 2>/dev/null
   ```
2. Stop and remove the SQL Server container if desired:
   ```bash
   docker stop $(docker ps -q --filter "ancestor=mcr.microsoft.com/mssql/server:2022-latest")
   ```
3. Record test run report from live audit log:
   ```bash
   python3 tools/qa_runner.py report \
     --workflow aspire-orchestration-e2e \
     --source todo-api \
     --status PASS \
     --notes "Aspire AppHost with Docker SQL Server 2022 successfully spun up, executed health checks, full CRUD, database verification, and Scalar UI checks."
   ```
