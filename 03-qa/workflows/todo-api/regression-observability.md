---
id: WF-TODO-REG-005
name: regression-observability
target: mkd7x/todo-api
prerequisites:
  api_base: http://localhost:5105
environment:
  API_BASE: http://localhost:5105
timeout_seconds: 180
cleanup_on_failure: false
---

# Workflow: Observability & Documentation Regression for `todo-api`

<!-- @implements REQ-WORK-04 -->
<!-- @verifies REQ-API-003 -->
<!-- @verifies REQ-API-004 -->

## Purpose & Scope
Regression coverage for the operational surface exposed by Aspire Service Defaults and the
OpenAPI/Scalar documentation:
- `GET /health` — readiness probe (REQ-API-004).
- `GET /alive` — liveness probe (REQ-API-004).
- `GET /openapi/v1.json` — OpenAPI 3.1 document (REQ-API-003).
- `GET /scalar/v1` — interactive Scalar UI (REQ-API-003).
- `GET /` — redirects to `/scalar/v1` (REQ-API-003).

**Prerequisite**: the API must be running at `http://localhost:5105`
(see [regression-test.md](regression-test.md) Steps 4–5).
If executed standalone, run `python3 tools/qa_runner.py clear-audit` first.

---

## Agent Runbook

### Step 1: Readiness Probe
```bash
python3 tools/send_http_req.py http://localhost:5105/health \
  --expect-status 200 \
  --expect-contains "Healthy" \
  --step-id step-reg-obs-01-health
```

### Step 2: Liveness Probe
```bash
python3 tools/send_http_req.py http://localhost:5105/alive \
  --expect-status 200 \
  --expect-contains "Healthy" \
  --step-id step-reg-obs-02-alive
```

### Step 3: OpenAPI 3.1 Document
```bash
python3 tools/send_http_req.py http://localhost:5105/openapi/v1.json \
  --expect-status 200 \
  --expect-contains "openapi" \
  --expect-contains "/api/todolists" \
  --expect-contains "/api/todoitems" \
  --step-id step-reg-obs-03-openapi
```

### Step 4: Scalar Interactive UI
```bash
python3 tools/send_http_req.py http://localhost:5105/scalar/v1 \
  --expect-status 200 \
  --step-id step-reg-obs-04-scalar
```

### Step 5: Root Redirect to Scalar
```bash
# urllib follows the 302 redirect, so the terminal response is the Scalar page (200)
python3 tools/send_http_req.py http://localhost:5105/ \
  --expect-status 200 \
  --step-id step-reg-obs-05-root-redirect
```
*Expected: root redirects (`302` → `/scalar/v1`) and resolves to `200 OK`.*

---

## Teardown
No state is created by this suite; no cleanup is required.
