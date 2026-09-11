# SPEC-EXE-005: Git Commitment & QA Handoff Gating

## 1. Summary
Once development tasks and dev loop verifications are complete, changes must be committed atomically to Git with traceable references to the planning tasks. The framework then compiles an execution summary and handoff manifest to gate transfer to `03-qa`.

## 2. Requirements

| Requirement ID | Title | Description | Acceptance Criteria |
| :--- | :--- | :--- | :--- |
| **REQ-HAND-01** | Task-Referenced Atomic Git Commits | The execution runner must create structured Git commits referencing plan task IDs and descriptions (e.g. `feat(TASK-001): ...`). | Commit command stages changes and verifies commit message formatting with valid task ID reference. |
| **REQ-HAND-02** | Machine-Readable 03-qa Handoff Manifest | The runner must package a JSON handoff manifest containing the Git commit SHA, branch name, touched files, and verification summary for `03-qa`. | Emits `runs/latest/handoff_manifest.json` and human-readable Markdown summary. |
| **REQ-HAND-03** | Agent Persona Operating Protocols | Autonomous agents operating in `02-exe` must follow designated persona roles (Setup Specialist, Implementer, Dev Loop Specialist, Handoff Coordinator). | Personas and SOP steps documented and enforced via `02-exe/AGENTS.md`. |

## 3. Traceability Links
- **Implementation**:
  - `tools/exe_runner.py`
  - `AGENTS.md`
- **Workflows & Examples**:
  - `templates/HANDOFF_TEMPLATE.md`
- **Verification**:
  - `tests/test_exe_runner.py`
