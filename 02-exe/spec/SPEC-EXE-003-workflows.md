# SPEC-EXE-003: Workflow Runbook Orchestration

## 1. Summary
Repositories follow distinct development workflows. In `02-exe`, workflows are organized per repository as machine-executable Markdown runbooks containing YAML frontmatter metadata, structured setup routines, dev server lifecycle steps, and process teardown traps.

## 2. Requirements

| Requirement ID | Title | Description | Acceptance Criteria |
| :--- | :--- | :--- | :--- |
| **REQ-WORK-01** | Per-Repository Workflow Organization | Workflows must be organized under `workflows/<repo-name>/` with standardized runbooks (`setup.md`, `start-dev.md`, `test-loop.md`). | Workflows are grouped by repository with clear separation between setup, dev server, and testing. |
| **REQ-WORK-02** | YAML Frontmatter Schema & Validation | Workflows must declare YAML frontmatter metadata defining id, target repo, prerequisites, dev server ports, and timeout settings. | Runbook validator (`lint-workflow`) validates metadata schema and flags missing or invalid fields. |
| **REQ-WORK-03** | Process Teardown & Shell Cleanup Traps | Execution runbooks and tools must register shell cleanup traps (`trap '...' EXIT INT TERM`) ensuring all background dev servers and containers are terminated on exit. | No dangling server processes or orphaned containers remain active after workflow termination or failure. |

## 3. Traceability Links
- **Implementation**:
  - `tools/exe_runner.py`
  - `tools/process_manager.py`
- **Workflows & Examples**:
  - `workflows/README.md`
  - `workflows/examples/dev-server-step.md`
  - `workflows/examples/workflow-template.md`
- **Verification**:
  - `tests/test_process_manager.py`
