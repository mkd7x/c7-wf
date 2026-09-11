# 02-exe: Implementation & Development Execution Framework

A generic, multi-workflow development execution system designed for autonomous agent pair-programming, dynamic credential fetching, and inner-loop developer workflows.

---

## Directory Structure

```
02-exe/
├── AGENTS.md                  # Autonomous agent operating instructions & personas
├── README.md                  # This documentation
├── .gitignore                 # Excludes local .env, secrets, workspace checkouts, and ephemeral runs
├── workspace/                 # Active development checkout / git worktree (.gitignored)
│   └── .gitkeep
├── workflows/                 # Per-repository dev runbooks & reusable patterns
│   ├── README.md              # Workflow catalog & naming conventions
│   ├── authoring-guide.md     # Standards and validation rules for exe runbooks
│   ├── examples/              # Reusable modular execution step patterns
│   │   ├── credential-step.md # Secret fetching (1Password, AWS, Doppler, Vault, Env)
│   │   ├── env-setup-step.md  # Safe .env synthesis from templates
│   │   ├── dev-server-step.md # Launching dev servers / background watchers with traps
│   │   ├── fast-verify-step.md# Incremental test/lint loop for modified files
│   │   └── workflow-template.md # Generic scaffold for new project runbooks
│   └── sample-project/        # Example concrete repository workflows
│       ├── setup.md           # Toolchain pre-flight, credentials, .env
│       ├── start-dev.md       # Dev server startup, background daemons, watch mode
│       └── test-loop.md       # Fast inner-loop test & lint verification
├── spec/                      # Formal functional specs & live traceability matrix
│   ├── README.md              # Traceability schema & annotation conventions
│   ├── TRACEABILITY_MATRIX.md # 100% live requirement-to-code mapping
│   ├── SPEC-EXE-001-env-setup.md  # Credential fetching, .env synthesis & secret redaction
│   ├── SPEC-EXE-002-discovery.md  # Dev commands, package managers, and env discovery
│   ├── SPEC-EXE-003-workflows.md  # Workflow runbook schema & lifecycle
│   ├── SPEC-EXE-004-devloop.md    # Task wave execution, watchers & fast verification
│   └── SPEC-EXE-005-handoff.md    # Git commit protocol & packaging handoff to 03-qa
├── tools/                     # Generic Python CLI automation utilities
│   ├── exe_runner.py          # Main CLI hub (intake, setup, start, test, commit, handoff)
│   ├── env_manager.py         # Credential fetching & safe .env synthesis (with secret masking)
│   ├── dev_discovery.py       # Inspects scripts, package managers, .env templates, test runners
│   ├── process_manager.py     # Background dev server supervision, health readiness & traps
│   ├── audit_logger.py        # Append-only audit logging & step output tracking
│   └── traceability_checker.py # Automated spec-code traceability validator
├── templates/                 # Reusable Markdown & configuration templates
│   ├── WORKFLOW_TEMPLATE.md   # Scaffold for new repo execution runbooks
│   ├── ENV_CONFIG_TEMPLATE.md # Declarative credential & variable mapping schema
│   └── HANDOFF_TEMPLATE.md    # Execution summary handed off to 03-qa
├── runs/                      # Ephemeral session runs & audit logs (.gitignored)
│   └── latest/
│       ├── audit.jsonl
│       └── execution_state.json
└── tests/                     # Unit test suite verifying 02-exe tools
    ├── test_exe_runner.py
    ├── test_env_manager.py
    ├── test_dev_discovery.py
    └── test_process_manager.py
```

---

## Agentic Workflow Execution

Workflows in `02-exe` are **executable runbooks for AI agents**, not static shell scripts. When an agent executes an initiative, it follows the runbook step-by-step:

### 1. Intake Plan from `01-plan`
```bash
python3 tools/exe_runner.py intake
```

### 2. Setup Local Environment & Fetch Credentials
```bash
python3 tools/env_manager.py setup --workspace workspace --template .env.example --output .env
```

### 3. Discover Project Dev Commands
```bash
python3 tools/exe_runner.py discover --source workspace
```

### 4. Register Cleanup Trap & Start Dev Server
```bash
trap 'python3 tools/process_manager.py stop --name dev-server 2>/dev/null' EXIT INT TERM
python3 tools/process_manager.py start --cmd "npm run dev" --name dev-server --cwd workspace
python3 tools/process_manager.py wait-ready --url http://127.0.0.1:3000/health --timeout 30
```

### 5. Execute Fast Inner-Loop Verification
```bash
python3 tools/exe_runner.py test-loop --cmd "npm run lint && npm test" --task-id TASK-01
```

### 6. Atomic Task Git Commit
```bash
python3 tools/exe_runner.py commit --task-id TASK-01 --message "add authentication middleware"
```

### 7. Compile Handoff Manifest for `03-qa`
```bash
python3 tools/exe_runner.py handoff --notes "All Wave 1 tasks implemented and verified."
```

---

## The Downstream Bridge: Gating Handoff to `03-qa`

When implementation is complete, `02-exe` generates a machine-readable manifest at `runs/latest/handoff_manifest.json`. The verification agent in `03-qa` consumes this payload:
```bash
python3 03-qa/tools/qa_runner.py setup-cleanroom --source <COMMIT_SHA_OR_BRANCH>
```

---

## Spec-Code Traceability

All specifications are strictly defined under `spec/` and cross-referenced with code annotations (`@implements REQ-xxx` and `@verifies REQ-xxx`).

Verify 100% spec-code traceability:
```bash
python3 tools/traceability_checker.py --strict
```
See [spec/TRACEABILITY_MATRIX.md](spec/TRACEABILITY_MATRIX.md) for full mapping details.
