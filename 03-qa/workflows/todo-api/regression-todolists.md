---
id: WF-TODO-REG-001
name: regression-todolists
target: mkd7x/todo-api
prerequisites:
  api_base: http://localhost:5105
environment:
  API_BASE: http://localhost:5105
timeout_seconds: 300
cleanup_on_failure: true
---

# Workflow: Todo Lists Endpoint Regression for `todo-api`

<!-- @implements REQ-WORK-04 -->
<!-- @verifies REQ-LIST-001 -->
<!-- @verifies REQ-LIST-002 -->
<!-- @verifies REQ-LIST-003 -->
<!-- @verifies REQ-LIST-004 -->
<!-- @verifies REQ-LIST-005 -->
<!-- @verifies REQ-API-001 -->

## Purpose & Scope
Regression coverage for the `/api/todolists` CRUD surface:
`GET /`, `GET /{id}`, `POST /`, `PUT /{id}`, `DELETE /{id}`.

**Prerequisite**: the API must be running at `http://localhost:5105`
(see [regression-test.md](regression-test.md) Steps 4–5).
If executed standalone, run `python3 tools/qa_runner.py clear-audit` first.

---

## Agent Runbook

### Step 1: Create a Todo List (Happy Path)
```bash
python3 tools/send_http_req.py http://localhost:5105/api/todolists \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{"title": "REG-TodoList", "colour": "#FF5722"}' \
  --expect-status 201 \
  --expect-json "id" \
  --step-id step-reg-list-01-create
```
*Expected: `201 Created` with `{ "id": <n> }`; `Location: /api/todolists/<n>`.*

### Step 2: List All Todo Lists
```bash
python3 tools/send_http_req.py http://localhost:5105/api/todolists \
  --expect-status 200 \
  --expect-json "length>=1" \
  --expect-contains "REG-TodoList" \
  --step-id step-reg-list-02-get-all
```
*Expected: `200 OK` array containing the created list and aggregate `totalItems`/`completedItems`.*

### Step 3: Get Todo List by ID
```bash
LID="$(python3 tools/qa_runner.py get-step-output --step step-reg-list-01-create --query output.body.id)"
python3 tools/send_http_req.py "http://localhost:5105/api/todolists/$LID" \
  --expect-status 200 \
  --expect-json "title=REG-TodoList" \
  --expect-json "colour=#FF5722" \
  --expect-json "items.length=0" \
  --step-id step-reg-list-03-get-by-id
```
*Expected: `200 OK` with list detail and an empty `items` array.*

### Step 4: Update Todo List
```bash
LID="$(python3 tools/qa_runner.py get-step-output --step step-reg-list-01-create --query output.body.id)"
python3 tools/send_http_req.py "http://localhost:5105/api/todolists/$LID" \
  -X PUT \
  -H "Content-Type: application/json" \
  -d '{"title": "REG-TodoList-Updated", "colour": "#000000"}' \
  --expect-status 204 \
  --step-id step-reg-list-04-update
```
*Expected: `204 No Content`.*

### Step 5: Verify the Update Persisted
```bash
LID="$(python3 tools/qa_runner.py get-step-output --step step-reg-list-01-create --query output.body.id)"
python3 tools/send_http_req.py "http://localhost:5105/api/todolists/$LID" \
  --expect-status 200 \
  --expect-json "title=REG-TodoList-Updated" \
  --expect-json "colour=#000000" \
  --step-id step-reg-list-05-get-updated
```

### Step 6: Validation Regression — Empty Title
```bash
python3 tools/send_http_req.py http://localhost:5105/api/todolists \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{"title": ""}' \
  --expect-status 400 \
  --expect-contains "One or more validation errors occurred." \
  --step-id step-reg-list-06-invalid-title
```

### Step 7: Validation Regression — Title Over 200 Characters
```bash
TITLE="$(python3 -c "print('A'*201)")"
python3 tools/send_http_req.py http://localhost:5105/api/todolists \
  -X POST \
  -H "Content-Type: application/json" \
  -d "{\"title\": \"$TITLE\"}" \
  --expect-status 400 \
  --step-id step-reg-list-07-title-too-long
```

### Step 8: Validation Regression — Colour Over 50 Characters
```bash
COLOUR="$(python3 -c "print('c'*51)")"
python3 tools/send_http_req.py http://localhost:5105/api/todolists \
  -X POST \
  -H "Content-Type: application/json" \
  -d "{\"title\": \"REG-TodoList\", \"colour\": \"$COLOUR\"}" \
  --expect-status 400 \
  --step-id step-reg-list-08-colour-too-long
```

### Step 9: Not-Found Regression — GET / PUT / DELETE Missing ID
```bash
python3 tools/send_http_req.py http://localhost:5105/api/todolists/999999 \
  --expect-status 404 \
  --expect-json "title=Resource Not Found" \
  --step-id step-reg-list-09-get-missing

python3 tools/send_http_req.py http://localhost:5105/api/todolists/999999 \
  -X PUT \
  -H "Content-Type: application/json" \
  -d '{"title": "ghost"}' \
  --expect-status 404 \
  --step-id step-reg-list-10-update-missing

python3 tools/send_http_req.py http://localhost:5105/api/todolists/999999 \
  -X DELETE \
  --expect-status 404 \
  --step-id step-reg-list-11-delete-missing
```
*Expected: `404 Not Found` with `detail` = `Entity "TodoList" (999999) was not found.`*

### Step 10: Delete the Todo List
```bash
LID="$(python3 tools/qa_runner.py get-step-output --step step-reg-list-01-create --query output.body.id)"
python3 tools/send_http_req.py "http://localhost:5105/api/todolists/$LID" \
  -X DELETE \
  --expect-status 204 \
  --step-id step-reg-list-12-delete
```

### Step 11: Confirm Deletion
```bash
LID="$(python3 tools/qa_runner.py get-step-output --step step-reg-list-01-create --query output.body.id)"
python3 tools/send_http_req.py "http://localhost:5105/api/todolists/$LID" \
  --expect-status 404 \
  --step-id step-reg-list-13-get-after-delete
```
*Expected: `404 Not Found`, proving the delete is durable.*

---

## Teardown
```bash
# Best-effort, idempotent cleanup if the suite aborted mid-way
LID="$(python3 tools/qa_runner.py get-step-output --step step-reg-list-01-create --query output.body.id 2>/dev/null)"
[ -n "$LID" ] && python3 tools/send_http_req.py "http://localhost:5105/api/todolists/$LID" -X DELETE --expect-status 204,404 --step-id step-reg-list-14-cleanup >/dev/null 2>&1 || true
```
