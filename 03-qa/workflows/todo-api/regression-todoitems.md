---
id: WF-TODO-REG-002
name: regression-todoitems
target: mkd7x/todo-api
prerequisites:
  api_base: http://localhost:5105
environment:
  API_BASE: http://localhost:5105
timeout_seconds: 300
cleanup_on_failure: true
---

# Workflow: Todo Items Endpoint Regression for `todo-api`

<!-- @implements REQ-WORK-04 -->
<!-- @verifies REQ-ITEM-002 -->
<!-- @verifies REQ-ITEM-003 -->
<!-- @verifies REQ-ITEM-004 -->
<!-- @verifies REQ-ITEM-005 -->
<!-- @verifies REQ-ITEM-006 -->
<!-- @verifies REQ-API-001 -->

## Purpose & Scope
Regression coverage for the `/api/todoitems` lifecycle:
`POST /`, `GET /{id}`, `PUT /{id}`, `PATCH /{id}/toggle`, `DELETE /{id}`, plus validation and
not-found contracts. Creates an isolated parent list and removes it (cascade) at the end.

**Prerequisite**: the API must be running at `http://localhost:5105`
(see [regression-test.md](regression-test.md) Steps 4–5).
If executed standalone, run `python3 tools/qa_runner.py clear-audit` first.

---

## Agent Runbook

### Step 1: Create the Parent Todo List
```bash
python3 tools/send_http_req.py http://localhost:5105/api/todolists \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{"title": "REG-ItemList", "colour": "#4CAF50"}' \
  --expect-status 201 \
  --expect-json "id" \
  --step-id step-reg-item-01-create-list
```

### Step 2: Create a Todo Item
```bash
LID="$(python3 tools/qa_runner.py get-step-output --step step-reg-item-01-create-list --query output.body.id)"
python3 tools/send_http_req.py http://localhost:5105/api/todoitems \
  -X POST \
  -H "Content-Type: application/json" \
  -d "{\"listId\": $LID, \"title\": \"REG-Item\", \"note\": \"regression note\", \"priority\": 3, \"dueDate\": \"2027-01-01T00:00:00Z\"}" \
  --expect-status 201 \
  --expect-json "id" \
  --step-id step-reg-item-02-create
```
*Expected: `201 Created` with `{ "id": <n> }`.*

### Step 3: Get the Item by ID
```bash
IID="$(python3 tools/qa_runner.py get-step-output --step step-reg-item-02-create --query output.body.id)"
LID="$(python3 tools/qa_runner.py get-step-output --step step-reg-item-01-create-list --query output.body.id)"
python3 tools/send_http_req.py "http://localhost:5105/api/todoitems/$IID" \
  --expect-status 200 \
  --expect-json "listId=$LID" \
  --expect-json "listTitle=REG-ItemList" \
  --expect-json "title=REG-Item" \
  --expect-json "note=regression note" \
  --expect-json "priority=3" \
  --expect-json "isCompleted=false" \
  --step-id step-reg-item-03-get-by-id
```

### Step 4: Toggle to Completed
```bash
IID="$(python3 tools/qa_runner.py get-step-output --step step-reg-item-02-create --query output.body.id)"
python3 tools/send_http_req.py "http://localhost:5105/api/todoitems/$IID/toggle" \
  -X PATCH \
  --expect-status 200 \
  --expect-json "isCompleted=true" \
  --step-id step-reg-item-04-toggle-complete
```

### Step 5: Verify CompletedAt Was Recorded
```bash
IID="$(python3 tools/qa_runner.py get-step-output --step step-reg-item-02-create --query output.body.id)"
python3 tools/send_http_req.py "http://localhost:5105/api/todoitems/$IID" \
  --expect-status 200 \
  --expect-json "isCompleted=true" \
  --expect-json "completedAt" \
  --step-id step-reg-item-05-get-completed
```
*Expected: `isCompleted=true` and a non-null `completedAt` (REQ-ITEM-005).*

### Step 6: Toggle Back to Incomplete
```bash
IID="$(python3 tools/qa_runner.py get-step-output --step step-reg-item-02-create --query output.body.id)"
python3 tools/send_http_req.py "http://localhost:5105/api/todoitems/$IID/toggle" \
  -X PATCH \
  --expect-status 200 \
  --expect-json "isCompleted=false" \
  --step-id step-reg-item-06-toggle-incomplete
```

### Step 7: Update the Item
```bash
IID="$(python3 tools/qa_runner.py get-step-output --step step-reg-item-02-create --query output.body.id)"
python3 tools/send_http_req.py "http://localhost:5105/api/todoitems/$IID" \
  -X PUT \
  -H "Content-Type: application/json" \
  -d '{"title": "REG-Item-Updated", "note": "updated note", "priority": 1, "dueDate": null}' \
  --expect-status 204 \
  --step-id step-reg-item-07-update
```

### Step 8: Verify the Update Persisted
```bash
IID="$(python3 tools/qa_runner.py get-step-output --step step-reg-item-02-create --query output.body.id)"
python3 tools/send_http_req.py "http://localhost:5105/api/todoitems/$IID" \
  --expect-status 200 \
  --expect-json "title=REG-Item-Updated" \
  --expect-json "note=updated note" \
  --expect-json "priority=1" \
  --step-id step-reg-item-08-get-updated
```

### Step 9: Validation Regression — Non-Positive ListId
```bash
python3 tools/send_http_req.py http://localhost:5105/api/todoitems \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{"listId": 0, "title": "bad list id"}' \
  --expect-status 400 \
  --expect-contains "One or more validation errors occurred." \
  --step-id step-reg-item-09-invalid-listid
```

### Step 10: Validation Regression — Empty Title & Oversized Note
```bash
python3 tools/send_http_req.py http://localhost:5105/api/todoitems \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{"listId": 1, "title": ""}' \
  --expect-status 400 \
  --step-id step-reg-item-10-empty-title

NOTE="$(python3 -c "print('n'*1001)")"
python3 tools/send_http_req.py http://localhost:5105/api/todoitems \
  -X POST \
  -H "Content-Type: application/json" \
  -d "{\"listId\": 1, \"title\": \"REG-Item\", \"note\": \"$NOTE\"}" \
  --expect-status 400 \
  --step-id step-reg-item-11-note-too-long
```

### Step 11: Not-Found Regression — Missing Parent List
```bash
python3 tools/send_http_req.py http://localhost:5105/api/todoitems \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{"listId": 999999, "title": "orphan"}' \
  --expect-status 404 \
  --expect-json "title=Resource Not Found" \
  --step-id step-reg-item-12-missing-parent
```

### Step 12: Not-Found Regression — Missing Item
```bash
python3 tools/send_http_req.py http://localhost:5105/api/todoitems/999999 \
  --expect-status 404 \
  --step-id step-reg-item-13-get-missing

python3 tools/send_http_req.py http://localhost:5105/api/todoitems/999999 \
  -X PUT \
  -H "Content-Type: application/json" \
  -d '{"title": "ghost"}' \
  --expect-status 404 \
  --step-id step-reg-item-14-update-missing

python3 tools/send_http_req.py http://localhost:5105/api/todoitems/999999/toggle \
  -X PATCH \
  --expect-status 404 \
  --step-id step-reg-item-15-toggle-missing

python3 tools/send_http_req.py http://localhost:5105/api/todoitems/999999 \
  -X DELETE \
  --expect-status 404 \
  --step-id step-reg-item-16-delete-missing
```

### Step 13: Delete the Item
```bash
IID="$(python3 tools/qa_runner.py get-step-output --step step-reg-item-02-create --query output.body.id)"
python3 tools/send_http_req.py "http://localhost:5105/api/todoitems/$IID" \
  -X DELETE \
  --expect-status 204 \
  --step-id step-reg-item-17-delete
```

### Step 14: Delete the Parent List (Cascade Regression)
```bash
LID="$(python3 tools/qa_runner.py get-step-output --step step-reg-item-01-create-list --query output.body.id)"
python3 tools/send_http_req.py "http://localhost:5105/api/todolists/$LID" \
  -X DELETE \
  --expect-status 204 \
  --step-id step-reg-item-18-delete-list
```

---

## Teardown
```bash
LID="$(python3 tools/qa_runner.py get-step-output --step step-reg-item-01-create-list --query output.body.id 2>/dev/null)"
[ -n "$LID" ] && python3 tools/send_http_req.py "http://localhost:5105/api/todolists/$LID" -X DELETE --expect-status 204,404 --step-id step-reg-item-19-cleanup >/dev/null 2>&1 || true
```
