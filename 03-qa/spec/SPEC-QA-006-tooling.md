# SPEC-QA-006: Specialized Agent Testing Tool Suite

## 1. Summary
The framework provides lightweight, zero-dependency CLI helper tools that autonomous agents can invoke during workflow execution to interact with HTTP APIs, databases, object stores, and service health endpoints.

## 2. Requirements

| Requirement ID | Title | Description | Acceptance Criteria |
| :--- | :--- | :--- | :--- |
| **REQ-TOOL-HTTP** | HTTP Request & Assertions | CLI tool to send HTTP requests with custom verbs, headers, payloads, and automated assertions. | `send_http_req.py` supports GET/POST/PUT/DELETE, custom headers, `--expect-status`, `--expect-json`, and `--expect-contains`. |
| **REQ-TOOL-SQL** | SQL Execution & Seeding | CLI tool to run queries, migrations, and seed scripts against SQLite databases. | `run_sql_cmd.py` executes query strings or `.sql` files with table, JSON, and CSV outputs, supporting `--expect-count`. |
| **REQ-TOOL-BLOB** | Blob & Object Storage Query | CLI tool to inspect, put, get, and list objects in local mock directories or blob stores. | `query_blob_storage.py` provides `list`, `exists`, `get`, `put`, and `delete` commands. |
| **REQ-TOOL-WAIT** | Service Readiness Polling | CLI tool to poll HTTP healthcheck endpoints or TCP ports with backoff until service is ready. | `wait_for_service.py` polls `--url` or `--tcp` with timeout and returns exit code 0 on readiness. |

## 3. Traceability Links
- **Implementation**:
  - `03-qa/tools/send_http_req.py` (`@implements REQ-TOOL-HTTP`)
  - `03-qa/tools/run_sql_cmd.py` (`@implements REQ-TOOL-SQL`)
  - `03-qa/tools/query_blob_storage.py` (`@implements REQ-TOOL-BLOB`)
  - `03-qa/tools/wait_for_service.py` (`@implements REQ-TOOL-WAIT`)
- **Workflows**:
  - `03-qa/workflows/smoke-test.md`
  - `03-qa/workflows/integration-test.md`
  - `03-qa/workflows/regression-test.md`
- **Verification**:
  - Verified via CLI executions and automated assertions.
