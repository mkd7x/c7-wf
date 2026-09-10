# SPEC-QA-001: Workspace Isolation & Target Containment

## 1. Summary
The clean-room testing environment must ensure hermetic execution by completely isolating target repositories under test from the parent workspace, preventing contaminated local state or unintentional git commits.

## 2. Requirements

| Requirement ID | Title | Description | Acceptance Criteria |
| :--- | :--- | :--- | :--- |
| **REQ-ISO-01** | Sandbox Wiping | Target workspace must be wiped clean before each test execution, preserving only structural `.gitkeep`. | All non-gitkeep files/directories in `target-repo/` are deleted on setup. |
| **REQ-ISO-02** | Multi-Source Import | Support fetching from either remote Git repositories (`git clone`) or local file trees (clean copy). | Successfully clones remote URLs or copies local paths excluding `.git` and cached dependencies. |
| **REQ-ISO-03** | Git Exclusion | All target repository files must be excluded from version control in `c7-wf`. | `git status` in parent repository remains clean even when target repo is populated. |
| **REQ-ISO-04** | Execution Containment | All commands executed against the target code must run with working directory set to `target-repo/`. | Subprocesses cannot mutate parent directories. |

## 3. Traceability Links
- **Implementation**:
  - `clean_directory_contents` in `03-qa/tools/qa_runner.py`
  - `setup_cleanroom` in `03-qa/tools/qa_runner.py`
  - `03-qa/.gitignore`
- **Workflows**:
  - `03-qa/workflows/clean-room-guide.md`
- **Verification**:
  - `tests/fixtures/sample-project/`
