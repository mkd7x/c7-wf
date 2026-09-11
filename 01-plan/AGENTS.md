# Planning Agent Operating Manual (01-plan)

<!-- @implements REQ-HAND-04 -->
<!-- @verifies REQ-HAND-04 -->

## Mission
The `01-plan` framework is dedicated to **rigorous, machine-verifiable software architecture, requirements scoping, and task decomposition**. Autonomous agents operating in this stage transform Jira tickets or ad-hoc technical briefs into unambiguous, dependency-ordered **Execution Plan Packages** committed to Git for consumption by `02-exe`, along with explicit verification contracts for `03-qa`.

---

## Agent Personas & Responsibilities

### 1. Requirements & Discovery Specialist
- **Responsibility**: Requirements intake, target codebase inspection, and scope containment.
- **Operating Rules**:
  - Run `python3 tools/plan_runner.py intake --workflow [jira|adhoc] ...` to initialize session context.
  - Scan the target repository via `python3 tools/plan_runner.py discover --source target-repo/`.
  - Always enforce explicit boundaries: list both **In-Scope** and **Out-of-Scope** items.
  - Never allow ambiguous requirements to propagate downstream into architecture or execution.

### 2. System & Solution Architect
- **Responsibility**: Architectural Decision Records (ADRs), interface design, and QA contract definition.
- **Operating Rules**:
  - Author formal decisions using `templates/ADR_TEMPLATE.md` (Context, Decision, Consequences, Alternatives).
  - Enforce Clean Architecture boundary rules: domain models must have zero external framework dependencies.
  - Define concrete verification contracts for `03-qa` (HTTP routes, expected status codes, JSON payload schemas, database table/column assertions).

### 3. Work Breakdown & Packaging Specialist
- **Responsibility**: Task decomposition, DAG scheduling, plan linting, and Git handoff.
- **Operating Rules**:
  - Decompose implementation into atomic tasks (`TASK-01` or `[KEY-T1]`) with explicit `Files to Touch` and `Definition of Done`.
  - Declare all prerequisite task dependencies using `depends_on: [TASK-XX]`. Root tasks declare `depends_on: []`.
  - Validate the task graph using `python3 tools/plan_runner.py graph-tasks --file <plan>` to ensure zero circular dependencies and verify execution waves.
  - Lint the plan document using `python3 tools/plan_runner.py lint-plan --file <plan> --strict`.
  - If operating with Jira in the loop, execute `python3 tools/plan_runner.py sync-jira --ticket <KEY> --file <plan>`.
  - Stage and commit the plan using `python3 tools/plan_runner.py commit-plan --file <plan> --branch <branch>`.

---

## Standard Operating Procedure (SOP)

```
[Requirement / Jira Ticket] ──> 1. Intake Requirement (intake.json)
                                        │
                                        ▼
                                2. Discover Codebase (context.json)
                                        │
                                        ▼
                                3. Author ADR & Interfaces (templates/ADR_TEMPLATE.md)
                                        │
                                        ▼
                                4. Decompose Tasks into DAG (task_graph.py)
                                        │
                                        ▼
                                5. Validate Schema & Lint (plan_validator.py)
                                        │
                                        ▼
                                6. Jira Two-Way Sync (if Jira workflow)
                                        │
                                        ▼
                                7. Commit Plan to Git (commit-plan)
                                        │
                                        ▼
                                8. Handoff to 02-exe & QA Contract to 03-qa
```

---

## Step-by-Step Operating Execution

### Step 1: Intake Requirement
- **Workflow A (Jira in the loop)**:
  ```bash
  python3 tools/plan_runner.py intake --workflow jira --ticket PROJ-1024 --step-id step-01-intake
  ```
- **Workflow B (Ticketless / Ad-hoc)**:
  ```bash
  python3 tools/plan_runner.py intake --workflow adhoc --title "sqlite-wal" --brief "Enable SQLite WAL mode" --step-id step-01-intake
  ```

### Step 2: Discover Target Codebase Context
```bash
python3 tools/plan_runner.py discover --source target-repo/ --step-id step-02-discover
```
Inspect discovered runtime, frameworks, layered directories, and existing ADRs.

### Step 3: Package & Draft Execution Plan
Assemble the plan from templates:
```bash
python3 tools/plan_runner.py package \
  --title "sqlite-wal-migration" \
  --workflow adhoc \
  --branch feature/sqlite-wal \
  --target target-repo/ \
  --step-id step-03-package
```

### Step 4: Validate Task Dependencies & Cycles
```bash
python3 tools/plan_runner.py graph-tasks --file plans/<PLAN_NAME>.md --format-waves --step-id step-04-dag
```
Verify that all execution waves (Wave 1, Wave 2, etc.) are strictly acyclic.

### Step 5: Lint Plan Markdown Schema
```bash
python3 tools/plan_runner.py lint-plan --file plans/<PLAN_NAME>.md --strict --step-id step-05-lint
```
Ensure required sections, DoD checklists, and QA assertions are populated.

### Step 6: Sync to Jira (If in the loop)
```bash
python3 tools/plan_runner.py sync-jira \
  --ticket PROJ-1024 \
  --file plans/<PLAN_NAME>.md \
  --transition "In Progress" \
  --create-subtasks \
  --step-id step-06-jira-sync
```

### Step 7: Commit Plan to Git & Handoff
```bash
python3 tools/plan_runner.py commit-plan \
  --file plans/<PLAN_NAME>.md \
  --branch feature/sqlite-wal \
  --push \
  --step-id step-07-commit
```
The plan is now versioned in Git and marked `READY FOR 02-EXE`.

---

## Tool Suite Reference Summary

| Tool | Key Subcommands & Flags | Primary Use Case |
| :--- | :--- | :--- |
| [`plan_runner.py`](file:///Users/michaelk/dev/c7-wf/01-plan/tools/plan_runner.py) | `intake`, `discover`, `package`, `lint-plan`, `graph-tasks`, `sync-jira`, `commit-plan`, `get-latest-plan` | Orchestration hub & CLI lifecycle manager |
| [`context_discovery.py`](file:///Users/michaelk/dev/c7-wf/01-plan/tools/context_discovery.py) | `--source`, `--json`, `--output` | Codebase stack, boundary & route discovery |
| [`task_graph.py`](file:///Users/michaelk/dev/c7-wf/01-plan/tools/task_graph.py) | `--file`, `--format-waves`, `--json` | DAG dependency validation & wave batching |
| [`plan_validator.py`](file:///Users/michaelk/dev/c7-wf/01-plan/tools/plan_validator.py) | `lint-plan`, `lint-workflow`, `--strict` | Schema & completeness validation |
| [`jira_client.py`](file:///Users/michaelk/dev/c7-wf/01-plan/tools/jira_client.py) | `fetch`, `comment`, `transition`, `--dry-run` | Jira REST API two-way synchronization |
| [`traceability_checker.py`](file:///Users/michaelk/dev/c7-wf/01-plan/tools/traceability_checker.py) | `--strict`, `--update-matrix`, `--json` | Spec-code traceability verification |

---

## Safety & Governance Rules
1. **Immutable Plans**: Once committed with `commit-plan`, plans are versioned artifacts. Any scope changes require a new revision or amendment plan.
2. **Deterministic Handoff**: `02-exe` must never begin work on an unvalidated plan or one containing circular dependencies.
3. **No Secret Leakage**: Jira tokens and sensitive credentials must never be committed to Git or embedded in generated plan files.
4. **Hermetic Testing**: Planning tools must execute cleanly in offline environments without mandatory external network access.
