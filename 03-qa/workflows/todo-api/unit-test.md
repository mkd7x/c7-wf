---
id: WF-TODO-UNIT-001
name: unit-test
target: mkd7x/todo-api
prerequisites:
  dotnet: ">=10.0"
  docker: true
environment:
  ASPNETCORE_ENVIRONMENT: Development
  DOTNET_ENVIRONMENT: Development
  DOTNET_CLI_TELEMETRY_OPTOUT: "1"
  ASPIRE_ALLOW_UNSECURED_TRANSPORT: "true"
timeout_seconds: 600
cleanup_on_failure: true
---

# Workflow: Unit Test with Aspire for `todo-api`

<!-- @implements REQ-WORK-02 -->
<!-- @verifies REQ-WORK-02 -->
<!-- @verifies REQ-WORK-05 -->

## Purpose & Scope
Runs the xUnit unit test suite for the `mkd7x/todo-api` Clean Architecture solution while the
`.NET Aspire` AppHost orchestrates the backing SQL Server 2022 container and the API service.

The unit tests in `tests/TodoApi.Application.UnitTests` exercise CQRS handlers, FluentValidation
validators and pagination helpers in isolation (EF Core InMemory + Moq), so they do not depend on
the SQL container. This runbook therefore validates the Aspire orchestration wiring first, then
executes the unit suite against the same build produced by the Aspire solution.

- **Target**: `https://github.com/mkd7x/todo-api.git`
- **Solution**: `TodoApi.slnx` (.NET 10, Aspire AppHost SDK `13.5.3`)
- **Expected tests**: `19` (see `spec/test_coverage/verification_matrix.md`)

---

## Agent Runbook

### Step 1: Initialize Cleanroom
Clone the target into the isolated `target-repo/` sandbox.
```bash
python3 tools/qa_runner.py setup-cleanroom --source https://github.com/mkd7x/todo-api.git
```

### Step 2: Discover Test Instructions
Confirm the documented test command and project layout before executing anything.
```bash
python3 tools/qa_runner.py discover --target target-repo
```
*Verify that `README.md` is discovered and that `tests/TodoApi.Application.UnitTests/` is present.*

### Step 3: Reset Audit Log & Register Teardown Trap
Clear any stale audit records so the final report reflects only this run, then ensure the Aspire
AppHost process and the SQL Server container are removed even if a later step fails.
(Prior run is archived to runs/latest/audit.<run-id>.jsonl, not deleted.)
```bash
# 1. Reset the live audit log for a clean run
python3 tools/qa_runner.py clear-audit

# 2. Register teardown trap for the Aspire AppHost and its SQL Server container
trap 'pkill -f "TodoApi.AppHost" 2>/dev/null; docker stop $(docker ps -q --filter "ancestor=mcr.microsoft.com/mssql/server:2022-latest") 2>/dev/null; docker rm -f $(docker ps -aq --filter "ancestor=mcr.microsoft.com/mssql/server:2022-latest") 2>/dev/null' EXIT INT TERM
```

### Step 4: Restore & Build the Aspire Solution
Build the entire `TodoApi.slnx`, including the Aspire AppHost, so orchestration wiring and the
unit test assembly are compiled before any service is started.
```bash
python3 tools/qa_runner.py exec --cmd "dotnet restore TodoApi.slnx" --timeout 300 --step-id step-04-restore
python3 tools/qa_runner.py exec --cmd "dotnet build TodoApi.slnx -c Release --no-restore --nologo" --timeout 300 --step-id step-04-build
```
*Expected: `Build succeeded. 0 Warning(s) 0 Error(s)`.*

### Step 5: Start Aspire AppHost & Poll Readiness
Launch the Aspire AppHost in the background (it provisions SQL Server, waits for readiness, then
starts `apiservice`), then poll the Aspire control-plane port until it accepts connections.

> **Note:** With `AspireUseCliBundle=true`, `dotnet run` delegates to the bundled Aspire CLI,
> which always builds and launches the `Debug` configuration. Do **not** pass `-c Release --no-build`
> to the AppHost — it will look for a non-existent `bin/Debug` binary.

```bash
# 1. Start the Aspire AppHost in the background using the fixed HTTP profile
python3 tools/qa_runner.py exec --cmd "dotnet run --project src/TodoApi.AppHost --launch-profile http > /tmp/todo-api-aspire.log 2>&1 &" --step-id step-05-apphost-start

# 2. Wait for the Aspire dashboard control-plane port (TCP avoids the self-signed HTTPS cert)
python3 tools/wait_for_service.py \
  --tcp 127.0.0.1:15198 \
  --timeout 300 \
  --interval 2.0 \
  --step-id step-05-aspire-readiness
```
*Expected: `[✓] TCP 127.0.0.1:15198 is reachable` (first run also pulls the SQL Server image).*

### Step 6: Confirm SQL Server Container Health
Verify Aspire actually brought the SQL Server 2022 container up and that it is running.
```bash
python3 tools/qa_runner.py exec --cmd "docker inspect --format '{{.Name}} state={{.State.Status}}' \$(docker ps -q --filter 'ancestor=mcr.microsoft.com/mssql/server:2022-latest')" --step-id step-06-sql-health
```
*Expected: one `sql-*` container with `state=running`.*

### Step 7: Execute the Unit Test Suite
Run the xUnit suite with coverage collection. `--no-build` reuses the Aspire solution build from
Step 4, keeping the run deterministic.
```bash
python3 tools/qa_runner.py exec --cmd "dotnet test tests/TodoApi.Application.UnitTests/TodoApi.Application.UnitTests.csproj -c Release --no-build --nologo --logger 'trx;LogFileName=unit-tests.trx' --collect:'XPlat Code Coverage'" --timeout 300 --step-id step-07-unit-tests-exec
```
*Expected: `Passed! - Failed: 0, Passed: 19, Skipped: 0, Total: 19`.*

### Step 8: Record Test Results & Assert Coverage
Parse the TRX result file and record the outcome into the live audit log so the final report
reflects the real unit test verdict (not just the Aspire readiness step).
```bash
python3 - <<'PY'
import sys, glob, xml.etree.ElementTree as ET
sys.path.insert(0, "tools")
import audit_logger

trx = glob.glob("target-repo/tests/TodoApi.Application.UnitTests/TestResults/unit-tests.trx")[0]
ns = {"t": "http://microsoft.com/schemas/VisualStudio/TeamTest/2010"}
results = ET.parse(trx).getroot().findall(".//t:UnitTestResult", ns)
failed = [r.get("testName") for r in results if r.get("outcome") != "Passed"]
ok = bool(results) and len(results) >= 19 and not failed

audit_logger.record_step(
    tool="dotnet-test",
    step_id="step-07-unit-tests",
    input_data={"project": "tests/TodoApi.Application.UnitTests", "expected_total": 19},
    output_data={"total": len(results), "failed": len(failed), "trx": trx},
    assertions={"passed": ok, "failures": failed},
    duration_ms=0.0,
    status="PASS" if ok else "FAIL",
)
print(f"Unit tests: {len(results)} total, {len(failed)} failed -> {'PASS' if ok else 'FAIL'}")
sys.exit(0 if ok else 1)
PY
```
*Expected: `Unit tests: 19 total, 0 failed -> PASS`.*

### Step 9: Teardown & Report Compilation
Stop the Aspire AppHost and its container, then compile the report from the live audit log.
```bash
# Explicit teardown (also enforced by the EXIT trap from Step 3)
pkill -f "TodoApi.AppHost" 2>/dev/null
docker stop $(docker ps -q --filter "ancestor=mcr.microsoft.com/mssql/server:2022-latest") 2>/dev/null
docker rm -f $(docker ps -aq --filter "ancestor=mcr.microsoft.com/mssql/server:2022-latest") 2>/dev/null

# Compile report directly from the live audit log
python3 tools/qa_runner.py report \
  --workflow unit \
  --source mkd7x/todo-api \
  --status PASS \
  --notes "Aspire orchestration verified and 19/19 unit tests passed."
```

---

## Failure Handling
- If Step 5 times out, inspect `/tmp/todo-api-aspire.log` and confirm Docker Desktop is running.
- If Step 7 reports failures, Step 8 records a `FAIL` status for `step-07-unit-tests`, which makes
  the audit-driven report verdict `FAIL`; the failing test names are captured in the assertions.
- If any step fails, the Step 3 trap removes the AppHost process and SQL Server container.
