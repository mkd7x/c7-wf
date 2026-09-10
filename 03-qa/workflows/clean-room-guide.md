# Clean Room Testing Standard Operating Procedure (SOP)

## What is Clean Room Testing?
Clean Room Testing ensures that software is evaluated in an isolated, pristine environment that mirrors a fresh developer machine or CI runner. It guarantees that tests pass because the code and its dependencies are correct, not because of leftover build artifacts, uncommitted changes, global cache leaks, or local environment quirks.

---

## Core Isolation Principles

### 1. Dedicated Target Directory (`target-repo/`)
- All target code under test must reside strictly inside `03-qa/target-repo/`.
- The `target-repo/` directory is excluded from `c7-wf`'s version control.
- Before running any new test suite or verification workflow, the previous contents of `target-repo/` must be completely cleaned or verified clean.

### 2. Source Provenance
- The target repository must come from a designated Git URL, branch, or a clean export of local changes.
- Never test against an active, dirty working directory directly. Always clone or rsync/copy into `target-repo/`.

### 3. Dependency Hermeticity
- Dependencies must be installed freshly in isolated virtual environments or project-local dependency folders (e.g. `.venv/` for Python, `node_modules/` for Node.js).
- Never depend on globally installed project libraries.

### 4. Instruction Discovery First
- **Never guess** test commands if documentation exists.
- The clean-room runner scans for `TESTING.md`, `README.md`, `Makefile`, and package manager descriptors to discover the intended build and test commands.

### 5. Deterministic Reporting & Teardown
- All commands, logs, durations, and return codes must be captured.
- Output a timestamped Markdown report into `reports/`.
- Post-test cleanup removes temporary sockets, databases, and background processes.

---

## Agent Clean Room Protocol Checklist

When an agent executes clean-room testing, it must follow these rules:
1. **Prepare Workspace**:
   ```bash
   python3 tools/qa_runner.py setup-cleanroom --source <URL_OR_PATH>
   ```
2. **Inspect Project Instructions**:
   ```bash
   python3 tools/qa_runner.py discover
   ```
3. **Execute the Workflow Steps**:
   Execute the required test steps according to the relevant workflow document (`smoke-test.md`, `unit-test.md`, etc.).
4. **Compile Report**:
   Ensure results are written to `reports/` following `templates/REPORT_TEMPLATE.md`.
5. **Verify Handoff**:
   Check if the overall status is `PASS` before approving handoff to `04-review`.
