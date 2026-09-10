# SPEC-QA-002: Test Instruction & Configuration Discovery

## 1. Summary
The clean-room testing environment must automatically inspect target projects to discover existing documentation (such as `TESTING.md`, `README.md`), project configurations (`package.json`, `pytest`, `Makefile`), and extract valid test commands.

## 2. Requirements

| Requirement ID | Title | Description | Acceptance Criteria |
| :--- | :--- | :--- | :--- |
| **REQ-DISC-01** | Documentation Discovery | Scan target directory for markdown testing guides (`TESTING.md`, `README.md`, `CONTRIBUTING.md`, `docs/`). | Detects documentation files regardless of filesystem casing without duplicates. |
| **REQ-DISC-02** | Markdown Command Extraction | Extract shell code blocks containing test invocations from discovered markdown files. | Accurately extracts runnable test commands. |
| **REQ-DISC-03** | Framework Heuristics | Identify standard project configurations: Node.js, Python, Rust, Go, and Makefiles. | Parses `package.json` scripts, `pytest.ini`, `Cargo.toml`, `go.mod`, and `Makefile` targets. |
| **REQ-DISC-04** | Command Prioritization | Prefer explicit commands found in `TESTING.md` over generic fallback heuristics. | Discovered document commands are prioritized for `smoke` and `unit` test recommendations. |

## 3. Traceability Links
- **Implementation**:
  - `find_documentation_files` in `03-qa/tools/test_discovery.py`
  - `extract_markdown_commands` in `03-qa/tools/test_discovery.py`
  - `inspect_package_json`, `inspect_python_project`, `inspect_makefile` in `03-qa/tools/test_discovery.py`
  - `discover_project_tests` in `03-qa/tools/test_discovery.py`
- **Workflows**:
  - `03-qa/workflows/clean-room-guide.md`
  - `03-qa/workflows/smoke-test.md`
- **Verification**:
  - Tested on `tests/fixtures/sample-project/TESTING.md`
