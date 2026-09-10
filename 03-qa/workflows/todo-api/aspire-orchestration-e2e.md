# Workflow: Aspire Orchestration End-to-End for `todo-api`

<!-- @verifies REQ-WORK-03 -->
<!-- @verifies REQ-TOOL-HTTP -->
<!-- @verifies REQ-TOOL-WAIT -->

## Purpose & Scope
This workflow validates full **.NET Aspire Orchestration** for the `mkd7x/todo-api` repository running with live **Docker container dependencies**. It verifies:
1. Aspire AppHost startup and container provisioning (Microsoft SQL Server 2022).
2. Aspire Dashboard and OTLP telemetry service availability.
3. Health check and liveness readiness probes.
4. End-to-end CRUD operations on Todo Lists and Items.
5. Verification of data persistence in containerized SQL Server.
6. Scalar OpenAPI 3.1 documentation accessibility.

---

## Agent Runbook: Step-by-Step

### Step 1: Verify Prerequisites
Ensure Docker is running and .NET 10 SDK is available:
```bash
docker info
dotnet --version
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
- **Command**:
```bash
python3 tools/wait_for_service.py --url http://localhost:5105/alive --expect-status 200 --timeout 60
python3 tools/wait_for_service.py --url http://localhost:5105/health --expect-status 200 --timeout 60
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
  --expect-contains "Personal Goals"
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
  --expect-json "id"
```

### Step 6: Create a Todo Item Under New List
- **Action**: HTTP POST
- **Tool**: `tools/send_http_req.py`
- **Execution Command**:
```bash
python3 tools/send_http_req.py http://localhost:5105/api/todoitems \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{"listId": 3, "title": "Verify Aspire SQL Server Container", "priority": 3, "note": "Orchestrated via Aspire AppHost"}' \
  --expect-status 201 \
  --expect-json "id"
```

### Step 7: Toggle Item Completion Status
- **Action**: HTTP PATCH
- **Tool**: `tools/send_http_req.py`
- **Execution Command**:
```bash
python3 tools/send_http_req.py http://localhost:5105/api/todoitems/6/toggle \
  -X PATCH \
  --expect-status 200 \
  --expect-json "isCompleted=true"
```

### Step 8: Query Filtered & Paginated Items
- **Action**: HTTP GET
- **Tool**: `tools/send_http_req.py`
- **Execution Command**:
```bash
python3 tools/send_http_req.py "http://localhost:5105/api/todoitems?listId=3" \
  -X GET \
  --expect-status 200 \
  --expect-contains "Verify Aspire SQL Server Container"
```

### Step 9: Verify Containerized SQL Server Persistence
Execute `sqlcmd` inside the Docker container to verify database rows:
```bash
# Locate container name
SQL_CONTAINER=$(docker ps --filter "ancestor=mcr.microsoft.com/mssql/server:2022-latest" --format "{{.Names}}")
SQL_PASS=$(docker inspect $SQL_CONTAINER | grep MSSQL_SA_PASSWORD | cut -d'=' -f2 | tr -d '", ')

docker exec $SQL_CONTAINER /opt/mssql-tools18/bin/sqlcmd \
  -S localhost -U sa -P "$SQL_PASS" -C -d tododb \
  -Q "SELECT Id, Title, Colour FROM TodoLists; SELECT Id, ListId, Title, IsCompleted FROM TodoItems;"
```

### Step 10: Delete Todo Item
- **Action**: HTTP DELETE
- **Tool**: `tools/send_http_req.py`
- **Execution Command**:
```bash
python3 tools/send_http_req.py http://localhost:5105/api/todoitems/6 \
  -X DELETE \
  --expect-status 204
```

### Step 11: Verify Scalar OpenAPI Documentation
- **Action**: HTTP GET
- **Tool**: `tools/send_http_req.py`
- **Execution Command**:
```bash
python3 tools/send_http_req.py http://localhost:5105/scalar/v1 \
  -X GET \
  --expect-status 200 \
  --expect-contains "Scalar"
```

---

## Teardown & Reporting

### Step 12: Shutdown Aspire AppHost & Clean Containers
1. Terminate the Aspire AppHost process:
   ```bash
   pkill -f TodoApi.AppHost
   pkill -f TodoApi.ApiService
   ```
2. Stop and remove the SQL Server container if desired:
   ```bash
   docker stop $(docker ps -q --filter "ancestor=mcr.microsoft.com/mssql/server:2022-latest")
   ```
3. Record test run report:
   ```bash
   python3 tools/qa_runner.py report \
     --workflow aspire-orchestration-e2e \
     --source todo-api \
     --status PASS \
     --notes "Aspire AppHost with Docker SQL Server 2022 successfully spun up, executed health checks, full CRUD, database verification, and Scalar UI checks."
   ```
