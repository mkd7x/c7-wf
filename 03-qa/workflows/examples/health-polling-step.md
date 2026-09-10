# Step Guide: Service Startup & Readiness Polling

<!-- @verifies REQ-TOOL-WAIT -->

## Purpose
Use this step guide when an agent starts a background server or service container and must confirm that the service is healthy before executing any test scenarios.

---

## Tool Reference
**Tool**: `tools/wait_for_service.py`

### CLI Flags
- `--url`, `-u`: HTTP URL to poll (e.g. `http://127.0.0.1:8080/health`)
- `--tcp`, `-t`: TCP socket to poll in `host:port` format (e.g. `127.0.0.1:5432`)
- `--expect-status`, `-s`: Expected HTTP status (default: `200`)
- `--timeout`: Maximum seconds to wait before failing (default: `60`)
- `--interval`: Seconds between polling attempts (default: `1.0`)

---

## Step Definition Schema

```json
{
  "step_type": "service_readiness",
  "name": "Wait for API Server",
  "target": "http://127.0.0.1:8080/health",
  "expected_status": 200,
  "timeout_seconds": 60
}
```

---

## Example Workflow Steps

### Example 1: Polling HTTP Health Endpoint
```markdown
### Step: Launch Application Server and Poll Health
- **Action**: Service Readiness
- **Tool**: `tools/wait_for_service.py`
- **CLI Execution**:
```bash
# 1. Start application in background
python3 tools/qa_runner.py exec --cmd "npm start &"

# 2. Wait for /health readiness
python3 tools/wait_for_service.py --url http://127.0.0.1:8080/health --expect-status 200 --timeout 45
```
```

### Example 2: Polling Database TCP Port
```markdown
### Step: Confirm Database Port Availability
- **Action**: TCP Socket Readiness
- **Tool**: `tools/wait_for_service.py`
- **CLI Execution**:
```bash
python3 tools/wait_for_service.py --tcp 127.0.0.1:5432 --timeout 30
```
```
