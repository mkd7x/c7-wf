# SPEC-EXE-004: Development Execution Loop & Task Scheduling

## 1. Summary
The core implementation loop takes tasks from `01-plan`, coordinates code changes, supervises background dev servers with health polling, executes fast inner-loop verifications, and logs state transitions into an append-only audit log.

## 2. Requirements

| Requirement ID | Title | Description | Acceptance Criteria |
| :--- | :--- | :--- | :--- |
| **REQ-DEV-01** | 01-plan Intake & Task Wave Sequencing | The execution runner must pull active plans from `01-plan` (`get-latest-plan`) and extract task DAGs organized by execution waves. | Intake command parses plan JSON, extracts branch, wave schedules, and individual task details. |
| **REQ-DEV-02** | Background Dev Server Supervision & Health Readiness | The framework must launch dev servers in the background, redirect logs, and poll HTTP/TCP readiness before running interactive or dev-loop steps. | Process manager successfully launches servers, awaits ready port/endpoint, and detects crashes. |
| **REQ-DEV-03** | Incremental Inner-Loop Verification | The framework must provide a fast test loop command that executes linters, typecheckers, and targeted tests scoped to modified files. | `test-loop` runs fast verification checks and returns exit code 0 on pass or formatted errors on failure. |
| **REQ-DEV-04** | Live Audit Logging & Step State Tracking | Every execution step must be logged to append-only `runs/latest/audit.jsonl` and indexed in `runs/latest/execution_state.json`. | Structured records store timestamps, tool names, inputs, outputs, duration, and status. |

## 3. Traceability Links
- **Implementation**:
  - `tools/exe_runner.py`
  - `tools/process_manager.py`
  - `tools/audit_logger.py`
- **Workflows & Examples**:
  - `workflows/examples/fast-verify-step.md`
- **Verification**:
  - `tests/test_exe_runner.py`
