---
id: WF-TODO-REG-004
name: regression-errors
target: mkd7x/todo-api
prerequisites:
  api_base: http://localhost:5105
environment:
  API_BASE: http://localhost:5105
timeout_seconds: 300
cleanup_on_failure: true
---

# Workflow: Error Handling & RFC 7807 Regression for `todo-api`

<!-- @implements REQ-WORK-04 -->
<!-- @verifies REQ-API-002 -->

## Purpose & Scope
Regression coverage for the centralized exception handler and RFC 7807 `ProblemDetails` contract:

| Condition | Exception | Status | Title |
| :--- | :--- | :--- | :--- |
| Validation failure | `ValidationException` | `400` | `One or more validation errors occurred.` |
| Missing entity | `NotFoundException` | `404` | `Resource Not Found` |

**Prerequisite**: the API must be running at `http://localhost:5105`
(see [regression-test.md](regression-test.md) Steps 4–5).
If executed standalone, run `python3 tools/qa_runner.py clear-audit` first.

> ## ⚠️ Known Deviation (REQ-API-002)
> The 400 `ValidationProblemDetails` payload currently serializes **without** the `errors`
> dictionary because `CustomExceptionHandler` casts the value to the base `ProblemDetails` type
> before `WriteAsJsonAsync`, dropping the derived `Errors` property. Step 1b is therefore expected
> to **FAIL** until the handler serializes the concrete `ValidationProblemDetails` type. This is a
> genuine spec regression, not a workflow defect.

---

## Agent Runbook

### Step 1a: 400 — Create List with Empty Title (Status & Title)
```bash
python3 tools/send_http_req.py http://localhost:5105/api/todolists \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{"title": ""}' \
  --expect-status 400 \
  --expect-json "status=400" \
  --expect-json "title=One or more validation errors occurred." \
  --step-id step-reg-err-01-validation-status
```

### Step 1b: Spec Conformance — Validation `errors` Dictionary (REQ-API-002)
```bash
python3 tools/send_http_req.py http://localhost:5105/api/todolists \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{"title": ""}' \
  --expect-status 400 \
  --expect-json "errors" \
  --step-id step-reg-err-02-validation-errors-map
```
*Expected per spec: an `errors` object keyed by property name (e.g. `errors.Title`).
**Currently fails** — see Known Deviation above.*

### Step 2: 400 — Create Item with Non-Positive ListId
```bash
python3 tools/send_http_req.py http://localhost:5105/api/todoitems \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{"listId": 0, "title": "bad"}' \
  --expect-status 400 \
  --expect-json "status=400" \
  --step-id step-reg-err-03-item-listid
```

### Step 3: 400 — Update Item with Invalid Route ID
```bash
python3 tools/send_http_req.py http://localhost:5105/api/todoitems/0 \
  -X PUT \
  -H "Content-Type: application/json" \
  -d '{"title": "bad id"}' \
  --expect-status 400 \
  --expect-json "status=400" \
  --step-id step-reg-err-04-update-id-zero
```

### Step 4: 400 — Oversized Fields (Colour, Note, Title)
```bash
COLOUR="$(python3 -c "print('c'*51)")"
python3 tools/send_http_req.py http://localhost:5105/api/todolists \
  -X POST -H "Content-Type: application/json" \
  -d "{\"title\": \"REG-Err\", \"colour\": \"$COLOUR\"}" \
  --expect-status 400 \
  --step-id step-reg-err-05-colour

TITLE="$(python3 -c "print('T'*201)")"
python3 tools/send_http_req.py http://localhost:5105/api/todoitems \
  -X POST -H "Content-Type: application/json" \
  -d "{\"listId\": 1, \"title\": \"$TITLE\"}" \
  --expect-status 400 \
  --step-id step-reg-err-06-title

NOTE="$(python3 -c "print('n'*1001)")"
python3 tools/send_http_req.py http://localhost:5105/api/todoitems \
  -X POST -H "Content-Type: application/json" \
  -d "{\"listId\": 1, \"title\": \"REG-Err\", \"note\": \"$NOTE\"}" \
  --expect-status 400 \
  --step-id step-reg-err-07-note
```

### Step 5: 404 — Missing Todo List
```bash
python3 tools/send_http_req.py http://localhost:5105/api/todolists/999999 \
  --expect-status 404 \
  --expect-json "status=404" \
  --expect-json "title=Resource Not Found" \
  --expect-contains "was not found" \
  --step-id step-reg-err-08-list-404

python3 tools/send_http_req.py http://localhost:5105/api/todolists/999999 \
  -X PUT -H "Content-Type: application/json" -d '{"title": "ghost"}' \
  --expect-status 404 \
  --step-id step-reg-err-09-list-update-404

python3 tools/send_http_req.py http://localhost:5105/api/todolists/999999 \
  -X DELETE \
  --expect-status 404 \
  --step-id step-reg-err-10-list-delete-404
```

### Step 6: 404 — Missing Todo Item
```bash
python3 tools/send_http_req.py http://localhost:5105/api/todoitems/999999 \
  --expect-status 404 \
  --expect-json "title=Resource Not Found" \
  --expect-contains "was not found" \
  --step-id step-reg-err-11-item-404

python3 tools/send_http_req.py http://localhost:5105/api/todoitems/999999/toggle \
  -X PATCH \
  --expect-status 404 \
  --step-id step-reg-err-12-item-toggle-404

python3 tools/send_http_req.py http://localhost:5105/api/todoitems/999999 \
  -X DELETE \
  --expect-status 404 \
  --step-id step-reg-err-13-item-delete-404
```

### Step 7: 404 — Create Item Under Missing List
```bash
python3 tools/send_http_req.py http://localhost:5105/api/todoitems \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{"listId": 999999, "title": "orphan"}' \
  --expect-status 404 \
  --expect-json "title=Resource Not Found" \
  --step-id step-reg-err-14-missing-parent
```

---

## Teardown
No persistent state is created by this suite (all mutations are rejected), so no cleanup is required.
