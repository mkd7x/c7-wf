# Execution Agent Operating Manual (02-exe)

## Mission
The `02-exe` stage is dedicated to **active implementation and inner-loop developer workflows**. Autonomous agents operating in this stage take structured execution plans from `01-plan`, configure repository-specific environments and credentials, launch and supervise local development processes, implement feature tasks in waves, execute fast incremental verifications, and produce atomic git commits and handoff manifests for clean-room verification in `03-qa`.

<!-- @implements REQ-HAND-03 -->
<!-- @verifies REQ-HAND-03 -->

---

## Agent Personas & Responsibilities

### 1. Environment & Workspace Specialist
- **Responsibility**: Workspace isolation, credential retrieval, environment variable synthesis, and dependency installation.
- **Rules**:
  - Always verify that destination `.env` files are excluded in `.gitignore` before writing secrets.
  - Use `python3 tools/env_manager.py setup` to safely render environment variables from templates (`.env.example`).
  - Never print unmasked secrets to stdout, terminal logs, or git commits.

### 2. Task Wave Implementer
- **Responsibility**: Intake active task DAGs from `01-plan` and execute coding modifications wave-by-wave.
- **Rules**:
  - Pull execution plans via `python3 tools/exe_runner.py intake`.
  - Implement tasks adhering to the architecture decisions and file scopes defined in `01-plan`.
  - Maintain clean code separation, avoiding cross-task contamination within a wave.

### 3. Dev Loop Verification Specialist
- **Responsibility**: Supervising background dev servers, watchers, and running fast iterative verification checks.
- **Rules**:
  - Always register teardown cleanup traps (`trap 'python3 tools/process_manager.py stop ...' EXIT INT TERM`) before starting background services.
  - Verify server health readiness using `python3 tools/process_manager.py wait-ready` before beginning testing.
  - Run the fast developer inner loop (`python3 tools/exe_runner.py test-loop`) after modifying code to catch lint, typecheck, or test failures immediately.

### 4. Git & Handoff Coordinator
- **Responsibility**: Atomic git commit management and packaging execution handoff evidence for `03-qa`.
- **Rules**:
  - Commit changes cleanly per task using `python3 tools/exe_runner.py commit --task-id <ID> --message "<msg>"`.
  - Compile the execution handoff manifest via `python3 tools/exe_runner.py handoff` to provide `03-qa` with the target commit SHA, branch, and notes.

---

## Standard Operating Procedure (SOP)

```
[01-plan Package] ──> 1. Intake Plan & Task DAG (exe_runner.py intake)
                             │
                             ▼
                      2. Setup Environment & Credentials (env_manager.py setup)
                             │
                             ▼
                      3. Discover Dev Commands (dev_discovery.py)
                             │
                             ▼
                      4. Register Traps & Start Dev Server (process_manager.py)
                             │
                             ▼
                      5. Implement Code by Task Wave (workspace/)
                             │
                             ▼
                      6. Fast Inner-Loop Verification (exe_runner.py test-loop)
                             │
                             ▼
                      7. Atomic Git Commit (exe_runner.py commit)
                             │
                             ▼
                      8. Package Handoff Manifest for 03-qa (exe_runner.py handoff)
```

### Step 1: Intake Plan
```bash
python3 tools/exe_runner.py intake
```

### Step 2: Setup Environment & Fetch Credentials
```bash
python3 tools/env_manager.py setup --workspace workspace --template .env.example --output .env
```

### Step 3: Discover Project Dev Tooling
```bash
python3 tools/exe_runner.py discover --source workspace
```

### Step 4: Register Traps & Start Dev Server
```bash
# 1. Register cleanup trap
trap 'python3 tools/process_manager.py stop --name dev-server 2>/dev/null' EXIT INT TERM

# 2. Launch background dev server
python3 tools/process_manager.py start --cmd "npm run dev" --name dev-server --cwd workspace

# 3. Poll readiness
python3 tools/process_manager.py wait-ready --url http://127.0.0.1:3000/health --timeout 30
```

### Step 5: Implement Task Wave
Make targeted modifications to files in `workspace/` fulfilling the current execution wave.

### Step 6: Fast Inner-Loop Verification
```bash
python3 tools/exe_runner.py test-loop --cmd "npm run lint && npm test" --task-id TASK-101
```

### Step 7: Atomic Git Commit
```bash
python3 tools/exe_runner.py commit --task-id TASK-101 --message "implement user model and service"
```

### Step 8: Package Handoff for 03-qa
```bash
python3 tools/exe_runner.py handoff --notes "Wave 1 completed and verified via fast test loop."
```

---

## Tool Suite Reference Summary

| Tool | Subcommands & Capabilities | Primary Purpose |
|---|---|---|
| [`exe_runner.py`](file:///Users/michaelk/dev/c7-wf/02-exe/tools/exe_runner.py) | `intake`, `discover`, `test-loop`, `lint-workflow`, `commit`, `handoff`, `clear-audit` | Core lifecycle orchestration and execution coordinator |
| [`env_manager.py`](file:///Users/michaelk/dev/c7-wf/02-exe/tools/env_manager.py) | `setup`, `fetch-secret` | Pluggable credential retrieval, safe .env synthesis, secret masking |
| [`dev_discovery.py`](file:///Users/michaelk/dev/c7-wf/02-exe/tools/dev_discovery.py) | `discover` | Inspects package managers, dev commands, fast test scripts, and env templates |
| [`process_manager.py`](file:///Users/michaelk/dev/c7-wf/02-exe/tools/process_manager.py) | `start`, `stop`, `wait-ready`, `generate-trap` | Dev server supervision, background process control, health readiness |
| [`audit_logger.py`](file:///Users/michaelk/dev/c7-wf/02-exe/tools/audit_logger.py) | `record_step`, `get_step_output`, `redact_text` | Live audit logging and automatic in-memory secret masking |
| [`traceability_checker.py`](file:///Users/michaelk/dev/c7-wf/02-exe/tools/traceability_checker.py) | `--strict`, `--json`, `--update-matrix` | Spec-code bidirectional traceability validation |

---

## Safety & Containment Rules
1. **Secret Redaction**: All secrets fetched via `env_manager.py` are registered in memory; values are masked with `***REDACTED***` in audit logs and output streams.
2. **Gitignore Verification**: `.env` and credential files must be confirmed in `.gitignore` before writing to prevent credential leaks to git.
3. **Mandatory Teardown Traps**: Always register shell cleanup traps (`trap '...' EXIT INT TERM`) to kill background processes and containers upon completion or error.
4. **Fast Dev Inner Loop**: Inner-loop testing must remain fast (<30 seconds) using targeted tests and linters, leaving exhaustive multi-subsystem regression verification to `03-qa`.
