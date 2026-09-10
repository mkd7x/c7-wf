# 03-qa: Clean Room Testing Framework

A generic, multi-workflow clean room testing system designed for automated agent pair-programming and CI verification.

## Directory Structure

```
03-qa/
├── AGENTS.md                  # Autonomous agent operating instructions & personas
├── README.md                  # This documentation
├── .gitignore                 # Excludes target checkouts and temp test logs
├── workflows/                 # Standardized testing runbooks
│   ├── README.md              # Workflow overview & conventions
│   ├── clean-room-guide.md    # Core isolation SOP
│   ├── smoke-test.md          # Fast sanity/smoke testing
│   ├── unit-test.md           # Unit testing and coverage
│   ├── integration-test.md    # Integration and mock subsystem tests
│   └── regression-test.md     # Bugfix and regression verification
├── spec/                      # Formal functional specs & traceability matrix
│   ├── README.md              # Traceability schema & annotation conventions
│   ├── TRACEABILITY_MATRIX.md # Complete live requirements traceability matrix
│   ├── SPEC-QA-001-isolation.md
│   ├── SPEC-QA-002-discovery.md
│   ├── SPEC-QA-003-workflows.md
│   ├── SPEC-QA-004-reporting.md
│   └── SPEC-QA-005-handoff.md
├── target-repo/               # Dedicated sandbox checkout directory (.gitignored)
│   └── .gitkeep
├── tools/                     # Generic CLI automation utilities
│   ├── qa_runner.py           # Clean room setup, exec, and report compilation
│   ├── test_discovery.py      # Project inspection & heuristic command discovery
│   ├── send_http_req.py       # HTTP client with assertions & latency measurement
│   ├── run_sql_cmd.py         # Database query & seed tool (SQLite, Postgres, MySQL)
│   ├── query_blob_storage.py  # Blob/object storage query & verification tool
│   ├── wait_for_service.py    # Healthcheck & TCP readiness polling tool
│   └── traceability_checker.py # Automated spec-code traceability validator
├── templates/                 # Reusable templates
│   └── REPORT_TEMPLATE.md     # Standardized Markdown QA report template
└── reports/                   # Generated test verification reports (.gitignored raw logs)
    └── .gitkeep
```

---

## Agentic Workflow Execution

Workflows in `03-qa` are **executable runbooks for AI agents**, not static shell scripts. When an agent tests a project, it follows the runbook step-by-step:

1. **Setup Cleanroom**:
   ```bash
   python3 tools/qa_runner.py setup-cleanroom --source <URL_OR_PATH>
   ```
2. **Discover Instructions**:
   ```bash
   python3 tools/qa_runner.py discover
   ```
3. **Seed Database State**:
   ```bash
   python3 tools/run_sql_cmd.py --db target-repo/test.db --file fixtures/seed.sql
   ```
4. **Start Service & Poll Readiness**:
   ```bash
   python3 tools/wait_for_service.py --url http://127.0.0.1:8080/health --expect-status 200
   ```
5. **Execute Assertions & Synthetic Requests**:
   ```bash
   python3 tools/send_http_req.py http://127.0.0.1:8080/api/v1/items -X POST -d '{"name": "test"}' --expect-status 201
   ```
6. **Compile Audit Report**:
   ```bash
   python3 tools/qa_runner.py report --workflow smoke --status PASS --notes "Verification passed."
   ```

---

## Supported Workflows
- **`smoke`**: Fast verification (seeding, service startup, health polling, core routes).
- **`integration`**: Multi-subsystem tests across APIs, SQL databases, and blob storage.
- **`unit`**: Comprehensive unit tests and coverage verification.
- **`regression`**: Full regression test suites and defect verification.

---

## Spec-Code Traceability

All functional specifications are defined under `spec/` and cross-referenced with code annotations (`@implements REQ-xxx`).

Verify 100% spec-code traceability:
```bash
python3 tools/traceability_checker.py
```
Or enforce strict verification in CI:
```bash
python3 tools/traceability_checker.py --strict
```
See [spec/TRACEABILITY_MATRIX.md](spec/TRACEABILITY_MATRIX.md) for full mapping details.

