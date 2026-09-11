# 01-plan: Architectural Planning & Task Scheduling Framework

A generic, multi-workflow planning framework designed for autonomous agent pair-programming and machine-verifiable task breakdown.

---

## Directory Structure

```
01-plan/
├── AGENTS.md                  # Autonomous agent operating instructions & personas
├── README.md                  # This documentation
├── .gitignore                 # Excludes ephemeral session runs and cache
├── workflows/                 # Standardized planning runbooks
│   ├── README.md              # Workflow overview & conventions
│   ├── authoring-guide.md     # Authoring standards & linter rules
│   ├── jira-plan.md           # Jira-driven planning runbook (Jira in the loop)
│   ├── ticketless-plan.md     # Ticketless / autonomous planning runbook
│   ├── plan-commit-handoff.md # Git plan commitment and 02-exe handoff protocol
│   └── examples/              # Reusable step definitions & patterns
│       ├── adr-step.md        # Architecture Decision Record pattern
│       ├── jira-sync-step.md  # Two-way Jira synchronization pattern
│       └── task-breakdown-step.md # Task decomposition and DAG pattern
├── spec/                      # Formal functional specs & live traceability matrix
│   ├── README.md              # Traceability schema & annotation conventions
│   ├── TRACEABILITY_MATRIX.md # Complete live requirements traceability matrix (100%)
│   ├── SPEC-PLAN-001-discovery.md     # Codebase inspection & context extraction
│   ├── SPEC-PLAN-002-architecture.md  # ADRs, boundaries & QA contracts
│   ├── SPEC-PLAN-003-decomposition.md # Task DAG, granularity & dependencies
│   ├── SPEC-PLAN-004-workflows.md     # Specifications for Jira & Ticketless workflows
│   ├── SPEC-PLAN-005-packaging.md     # Plan compilation, schemas & linter
│   └── SPEC-PLAN-006-handoff.md       # Git commitment & 02-exe pull gating
├── tools/                     # Generic Python CLI automation utilities
│   ├── plan_runner.py         # Main CLI hub (intake, discover, package, commit)
│   ├── context_discovery.py   # Target repo stack, boundaries, and route discovery
│   ├── task_graph.py          # Validates task DAG, cycle detector, execution waves
│   ├── plan_validator.py      # Schema linter for plans and workflow runbooks
│   ├── jira_client.py         # Jira REST API client (supports live & mock modes)
│   └── traceability_checker.py # Automated spec-code traceability validator
├── templates/                 # Reusable Markdown planning templates
│   ├── PLAN_TEMPLATE.md       # Standardized Execution Plan bundle
│   ├── ADR_TEMPLATE.md        # Architecture Decision Record template
│   ├── TASK_TEMPLATE.md       # Atomic task template
│   └── JIRA_COMMENT_TEMPLATE.md # Standard markdown sync comment for Jira
├── plans/                     # Generated immutable plan packages (handed off to 02-exe)
│   └── .gitkeep
├── runs/                      # Ephemeral session runs & audit logs (.gitignored)
│   └── latest/
└── tests/                     # Unit test suite verifying planning tools
    ├── test_plan_runner.py
    ├── test_task_graph.py
    ├── test_context_discovery.py
    ├── test_plan_validator.py
    └── test_jira_client.py
```

---

## Agentic Workflow Execution

Workflows in `01-plan` are **executable runbooks for AI agents**, not static text documents. When an agent plans an initiative, it follows the runbook step-by-step:

### 1. Requirements Intake
```bash
# Workflow A: Jira in the loop
python3 tools/plan_runner.py intake --workflow jira --ticket PROJ-1024

# Workflow B: Ticketless / Ad-hoc brief
python3 tools/plan_runner.py intake --workflow adhoc --title "sqlite-wal" --brief "Enable SQLite WAL mode"
```

### 2. Codebase Context Discovery
```bash
python3 tools/plan_runner.py discover --source target-repo/
```

### 3. Package Draft Execution Plan
```bash
python3 tools/plan_runner.py package \
  --title "sqlite-wal-migration" \
  --workflow adhoc \
  --branch feature/sqlite-wal \
  --target target-repo/
```

### 4. Validate Task DAG & Wave Scheduling
```bash
python3 tools/plan_runner.py graph-tasks --file plans/<PLAN_FILE>.md --format-waves
```

### 5. Lint Plan Completeness
```bash
python3 tools/plan_runner.py lint-plan --file plans/<PLAN_FILE>.md --strict
```

### 6. Jira Two-Way Synchronization (if Jira in the loop)
```bash
python3 tools/plan_runner.py sync-jira \
  --ticket PROJ-1024 \
  --file plans/<PLAN_FILE>.md \
  --transition "In Progress" \
  --create-subtasks
```

### 7. Commit Plan to Git & Gate Handoff for `02-exe`
```bash
python3 tools/plan_runner.py commit-plan \
  --file plans/<PLAN_FILE>.md \
  --branch feature/sqlite-wal \
  --push
```

---

## The Downstream Bridge: Pulling into `02-exe`

When the execution agent wakes up in `02-exe`, it queries the active plan directly:
```bash
python3 01-plan/tools/plan_runner.py get-latest-plan --json
```
The returned payload includes:
- Path to the committed plan
- Verified Git Commit SHA
- Target Git Branch
- Extracted execution waves (Wave 1 parallel tasks -> Wave 2 -> Wave 3)

---

## Supported Workflows
- **`jira`**: Full integration with Jira issues, syncing comments, status transitions, and child subtasks.
- **`adhoc`**: Hermetic, ticketless planning from local briefs or prompts with zero external API dependencies.
- **`handoff`**: Pre-commit validation, provenance tracking, and deterministic `02-exe` intake.

---

## Spec-Code Traceability

All specifications are strictly defined under `spec/` and cross-referenced with code annotations (`@implements REQ-xxx` and `@verifies REQ-xxx`).

Verify 100% spec-code traceability:
```bash
python3 tools/traceability_checker.py --strict
```
See [spec/TRACEABILITY_MATRIX.md](spec/TRACEABILITY_MATRIX.md) for full mapping details.
