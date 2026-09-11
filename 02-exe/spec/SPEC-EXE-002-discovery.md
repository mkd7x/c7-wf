# SPEC-EXE-002: Project Dev & Toolchain Discovery

## 1. Summary
Autonomous execution agents working on unfamiliar repositories must inspect project files to discover how to install dependencies, run development servers, launch background watchers, and execute fast developer verification tests.

## 2. Requirements

| Requirement ID | Title | Description | Acceptance Criteria |
| :--- | :--- | :--- | :--- |
| **REQ-DISC-01** | Dev Script & Task Runner Discovery | The framework must scan workspaces for task runners and build scripts defined in `package.json`, `Makefile`, `Justfile`, and `Taskfile.yml`. | Extracts available script names, dev server targets, and build targets. |
| **REQ-DISC-02** | Runtime & Package Manager Detection | The discovery engine must detect the underlying project runtime (Node, Python/Poetry/uv, .NET, Rust/Cargo, Go) and provide package installation commands. | Correctly identifies runtime environment and emits recommended restore/install commands. |
| **REQ-DISC-03** | Fast Dev Test & Lint Command Discovery | The engine must identify fast feedback commands for the inner dev loop, including linters (`eslint`, `ruff`), typecheckers (`tsc`, `mypy`), and targeted test commands. | Recommends fast checks separated from long-running comprehensive regression suites. |
| **REQ-DISC-04** | Environment Template & Container Detection | The engine must detect configuration templates (`.env.example`, `.env.template`) and container orchestration definitions (`docker-compose.yml`, `compose.yaml`). | Outputs list of template files and container services required for local development. |

## 3. Traceability Links
- **Implementation**:
  - `tools/dev_discovery.py`
- **Workflows & Examples**:
  - `workflows/authoring-guide.md`
- **Verification**:
  - `tests/test_dev_discovery.py`
