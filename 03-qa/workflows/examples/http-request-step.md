# Step Guide: HTTP Request & Assertions

<!-- @verifies REQ-TOOL-HTTP -->

## Purpose
Use this step guide when an agent needs to send an HTTP request (GET, POST, PUT, DELETE, PATCH), validate response status codes, verify response headers, check JSON keys, or assert body text contents.

---

## Tool Reference
**Tool**: `tools/send_http_req.py`

### CLI Flag Reference
- `url`: Target endpoint URL
- `--method`, `-X`: HTTP verb (`GET`, `POST`, `PUT`, `DELETE`, `PATCH`, `HEAD`)
- `--header`, `-H`: Request headers (repeatable: `-H "Authorization: Bearer token" -H "Content-Type: application/json"`)
- `--data`, `-d`: Request payload string or JSON string
- `--expect-status`, `-s`: Expected HTTP status code(s) (e.g. `200`, `201`, `200,204`)
- `--expect-json`: Assert that JSON response contains `key=value` or has `key`
- `--expect-contains`: Assert that response body string contains substring
- `--no-redirect`: Do not follow redirects; assert the 3xx directly (`Location` is audited)
- `--insecure`: Skip TLS verification for self-signed dev certs
- `--ca-cert`: Path to a custom CA bundle for TLS verification
- `--verbose`, `-v`: Print verbose request and response details
- `--save`: Save response body to a file

---

## Step Definition Schema (JSON)

When authoring an HTTP request step in a project workflow, document it in JSON format:

```json
{
  "step_type": "http_request",
  "name": "Create Resource",
  "method": "POST",
  "url": "http://127.0.0.1:8080/api/v1/items",
  "headers": {
    "Content-Type": "application/json",
    "Authorization": "Bearer test-api-key"
  },
  "body": {
    "title": "Test Item",
    "price": 29.99
  },
  "assertions": {
    "status_code": 201,
    "json_keys": {
      "status": "created",
      "title": "Test Item"
    },
    "body_contains": "Test Item"
  }
}
```

---

## Example Workflow Steps

### Example 1: Authenticated GET Request with Status & JSON Assertion
```markdown
### Step: Fetch Current User Profile
- **Action**: HTTP GET
- **Tool**: `tools/send_http_req.py`
- **Specification**:
```json
{
  "method": "GET",
  "url": "http://127.0.0.1:8080/api/v1/me",
  "headers": {
    "Authorization": "Bearer user-session-token"
  },
  "assertions": {
    "status_code": 200,
    "json_keys": {
      "role": "admin"
    }
  }
}
```
- **Execution Command**:
```bash
python3 tools/send_http_req.py http://127.0.0.1:8080/api/v1/me \
  -H "Authorization: Bearer user-session-token" \
  --expect-status 200 \
  --expect-json "role=admin"
```
```

### Example 2: POST JSON Request Creating a Resource
```markdown
### Step: Submit New Order
- **Action**: HTTP POST
- **Tool**: `tools/send_http_req.py`
- **Specification**:
```json
{
  "method": "POST",
  "url": "http://127.0.0.1:8080/api/v1/orders",
  "headers": {
    "Content-Type": "application/json"
  },
  "body": {
    "orderId": 1042,
    "amount": 150
  },
  "assertions": {
    "status_code": 201,
    "json_keys": {
      "status": "confirmed"
    }
  }
}
```
- **Execution Command**:
```bash
python3 tools/send_http_req.py http://127.0.0.1:8080/api/v1/orders \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{"orderId": 1042, "amount": 150}' \
  --expect-status 201 \
  --expect-json "status=confirmed"
```
```
