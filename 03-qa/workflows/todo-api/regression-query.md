---
id: WF-TODO-REG-003
name: regression-query
target: mkd7x/todo-api
prerequisites:
  api_base: http://localhost:5105
environment:
  API_BASE: http://localhost:5105
timeout_seconds: 300
cleanup_on_failure: true
---

# Workflow: Query, Pagination & Filtering Regression for `todo-api`

<!-- @implements REQ-WORK-04 -->
<!-- @verifies REQ-ITEM-001 -->
<!-- @verifies REQ-LIST-001 -->

## Purpose & Scope
Regression coverage for the read/query surface:
- `GET /api/todoitems` pagination (`pageNumber`, `pageSize`) and clamping.
- Multi-filtering by `listId`, `isCompleted`, `priority`, and `searchQuery`.
- Aggregate counts on `GET /api/todolists` and detail item collections.

Creates two isolated lists (A with 3 items, B with 1 item), asserts against list-scoped filters so
results are independent of any pre-existing/persisted data, then removes both lists.

**Prerequisite**: the API must be running at `http://localhost:5105`
(see [regression-test.md](regression-test.md) Steps 4–5).
If executed standalone, run `python3 tools/qa_runner.py clear-audit` first.

---

## Agent Runbook

### Step 1: Seed List A
```bash
python3 tools/send_http_req.py http://localhost:5105/api/todolists \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{"title": "REG-Query-A", "colour": "#111111"}' \
  --expect-status 201 \
  --expect-json "id" \
  --step-id step-reg-query-01-create-list-a
```

### Step 2: Seed Three Items in List A
```bash
LIDA="$(python3 tools/qa_runner.py get-step-output --step step-reg-query-01-create-list-a --query output.body.id)"
python3 tools/send_http_req.py http://localhost:5105/api/todoitems \
  -X POST -H "Content-Type: application/json" \
  -d "{\"listId\": $LIDA, \"title\": \"REG-Query-High\", \"priority\": 3}" \
  --expect-status 201 --expect-json "id" \
  --step-id step-reg-query-02-item-high

python3 tools/send_http_req.py http://localhost:5105/api/todoitems \
  -X POST -H "Content-Type: application/json" \
  -d "{\"listId\": $LIDA, \"title\": \"REG-Query-Med\", \"priority\": 2}" \
  --expect-status 201 --expect-json "id" \
  --step-id step-reg-query-03-item-med

python3 tools/send_http_req.py http://localhost:5105/api/todoitems \
  -X POST -H "Content-Type: application/json" \
  -d "{\"listId\": $LIDA, \"title\": \"REG-Query-Done\", \"priority\": 1}" \
  --expect-status 201 --expect-json "id" \
  --step-id step-reg-query-04-item-done
```

### Step 3: Mark One Item Complete
```bash
IID="$(python3 tools/qa_runner.py get-step-output --step step-reg-query-04-item-done --query output.body.id)"
python3 tools/send_http_req.py "http://localhost:5105/api/todoitems/$IID/toggle" \
  -X PATCH \
  --expect-status 200 \
  --expect-json "isCompleted=true" \
  --step-id step-reg-query-05-toggle-done
```

### Step 4: Seed List B with One Item
```bash
python3 tools/send_http_req.py http://localhost:5105/api/todolists \
  -X POST -H "Content-Type: application/json" \
  -d '{"title": "REG-Query-B", "colour": "#222222"}' \
  --expect-status 201 --expect-json "id" \
  --step-id step-reg-query-06-create-list-b

LIDB="$(python3 tools/qa_runner.py get-step-output --step step-reg-query-06-create-list-b --query output.body.id)"
python3 tools/send_http_req.py http://localhost:5105/api/todoitems \
  -X POST -H "Content-Type: application/json" \
  -d "{\"listId\": $LIDB, \"title\": \"REG-Query-Other\", \"priority\": 2}" \
  --expect-status 201 --expect-json "id" \
  --step-id step-reg-query-07-item-other
```

### Step 5: Filter by listId
```bash
LIDA="$(python3 tools/qa_runner.py get-step-output --step step-reg-query-01-create-list-a --query output.body.id)"
python3 tools/send_http_req.py "http://localhost:5105/api/todoitems?listId=$LIDA" \
  --expect-status 200 \
  --expect-json "items.length=3" \
  --expect-json "totalCount=3" \
  --expect-json "pageNumber=1" \
  --step-id step-reg-query-08-filter-listid
```

### Step 6: Filter by listId + isCompleted
```bash
LIDA="$(python3 tools/qa_runner.py get-step-output --step step-reg-query-01-create-list-a --query output.body.id)"
python3 tools/send_http_req.py "http://localhost:5105/api/todoitems?listId=$LIDA&isCompleted=false" \
  --expect-status 200 \
  --expect-json "totalCount=2" \
  --expect-json "items[0].isCompleted=false" \
  --step-id step-reg-query-09-filter-completed

python3 tools/send_http_req.py "http://localhost:5105/api/todoitems?listId=$LIDA&isCompleted=true" \
  --expect-status 200 \
  --expect-json "totalCount=1" \
  --expect-json "items[0].isCompleted=true" \
  --step-id step-reg-query-10-filter-incomplete
```

### Step 7: Filter by Priority
```bash
LIDA="$(python3 tools/qa_runner.py get-step-output --step step-reg-query-01-create-list-a --query output.body.id)"
python3 tools/send_http_req.py "http://localhost:5105/api/todoitems?listId=$LIDA&priority=3" \
  --expect-status 200 \
  --expect-json "totalCount=1" \
  --expect-json "items[0].priority=3" \
  --expect-json "items[0].title=REG-Query-High" \
  --step-id step-reg-query-11-filter-priority
```

### Step 8: Search Query
```bash
python3 tools/send_http_req.py "http://localhost:5105/api/todoitems?searchQuery=REG-Query-High" \
  --expect-status 200 \
  --expect-json "totalCount>=1" \
  --expect-json "items[0].title=REG-Query-High" \
  --step-id step-reg-query-12-search
```

### Step 9: Pagination — Page 1 / Page 2
```bash
LIDA="$(python3 tools/qa_runner.py get-step-output --step step-reg-query-01-create-list-a --query output.body.id)"
python3 tools/send_http_req.py "http://localhost:5105/api/todoitems?listId=$LIDA&pageNumber=1&pageSize=1" \
  --expect-status 200 \
  --expect-json "items.length=1" \
  --expect-json "pageNumber=1" \
  --expect-json "totalPages=3" \
  --expect-json "hasPreviousPage=false" \
  --expect-json "hasNextPage=true" \
  --step-id step-reg-query-13-page-1

python3 tools/send_http_req.py "http://localhost:5105/api/todoitems?listId=$LIDA&pageNumber=2&pageSize=1" \
  --expect-status 200 \
  --expect-json "items.length=1" \
  --expect-json "pageNumber=2" \
  --expect-json "hasPreviousPage=true" \
  --expect-json "hasNextPage=true" \
  --step-id step-reg-query-14-page-2

python3 tools/send_http_req.py "http://localhost:5105/api/todoitems?listId=$LIDA&pageNumber=3&pageSize=1" \
  --expect-status 200 \
  --expect-json "pageNumber=3" \
  --expect-json "hasNextPage=false" \
  --step-id step-reg-query-15-page-3
```

### Step 10: Pagination Clamping
```bash
python3 tools/send_http_req.py "http://localhost:5105/api/todoitems?pageSize=0&pageNumber=1" \
  --expect-status 200 \
  --expect-json "pageNumber=1" \
  --expect-json "items.length<=10" \
  --step-id step-reg-query-16-clamp-pagesize

python3 tools/send_http_req.py "http://localhost:5105/api/todoitems?pageNumber=-5&pageSize=2" \
  --expect-status 200 \
  --expect-json "pageNumber=1" \
  --step-id step-reg-query-17-clamp-pagenumber
```

### Step 11: Empty Result Set
```bash
python3 tools/send_http_req.py "http://localhost:5105/api/todoitems?listId=999999" \
  --expect-status 200 \
  --expect-json "items.length=0" \
  --expect-json "totalCount=0" \
  --expect-json "totalPages=0" \
  --expect-json "hasNextPage=false" \
  --step-id step-reg-query-18-empty
```

### Step 12: Aggregate Counts on List Detail
```bash
LIDA="$(python3 tools/qa_runner.py get-step-output --step step-reg-query-01-create-list-a --query output.body.id)"
python3 tools/send_http_req.py "http://localhost:5105/api/todolists/$LIDA" \
  --expect-status 200 \
  --expect-json "title=REG-Query-A" \
  --expect-json "items.length=3" \
  --step-id step-reg-query-19-list-detail-count

python3 tools/send_http_req.py http://localhost:5105/api/todolists \
  --expect-status 200 \
  --expect-contains "REG-Query-A" \
  --expect-contains "totalItems" \
  --step-id step-reg-query-20-list-aggregates
```

### Step 13: Cleanup
```bash
LIDA="$(python3 tools/qa_runner.py get-step-output --step step-reg-query-01-create-list-a --query output.body.id)"
LIDB="$(python3 tools/qa_runner.py get-step-output --step step-reg-query-06-create-list-b --query output.body.id)"
python3 tools/send_http_req.py "http://localhost:5105/api/todolists/$LIDA" -X DELETE --expect-status 204 --step-id step-reg-query-21-delete-a
python3 tools/send_http_req.py "http://localhost:5105/api/todolists/$LIDB" -X DELETE --expect-status 204 --step-id step-reg-query-22-delete-b
```

---

## Teardown
```bash
for STEP in step-reg-query-01-create-list-a step-reg-query-06-create-list-b; do
  LID="$(python3 tools/qa_runner.py get-step-output --step "$STEP" --query output.body.id 2>/dev/null)"
  [ -n "$LID" ] && python3 tools/send_http_req.py "http://localhost:5105/api/todolists/$LID" -X DELETE --expect-status 204,404 --step-id "${STEP}-cleanup" >/dev/null 2>&1 || true
done
```
