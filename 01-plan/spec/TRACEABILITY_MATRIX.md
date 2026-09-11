# Requirements Traceability Matrix (RTM) - 01-plan

## Summary Metrics

| Metric | Count | Percentage |
| :--- | :--- | :--- |
| **Total Specifications** | 6 Specs | 100% |
| **Total Functional Requirements** | 22 Requirements | 100% |
| **Implemented in Code & Runbooks** (`@implements`) | 22 / 22 | 100% |
| **Verified by Tests & Runbooks** (`@verifies`) | 22 / 22 | 100% |
| **Overall Complete Traceability** | **22 / 22** | **100%** |

> Verified coverage is machine-checked: `python3 tools/traceability_checker.py --strict`
> (read-only check; pass `--update-matrix` to regenerate this file)

---

## Traceability Matrix Table

| Req ID | Requirement Title | Spec File | Implementation | Verification Artifact | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **REQ-ARCH-01** | Standardized ADR Formulation | [SPEC-PLAN-002-architecture.md](SPEC-PLAN-002-architecture.md) | `templates/ADR_TEMPLATE.md:3` | `workflows/examples/adr-step.md:3` | 🟢 VERIFIED |
| **REQ-ARCH-02** | Component Boundary Definitions | [SPEC-PLAN-002-architecture.md](SPEC-PLAN-002-architecture.md) | `templates/PLAN_TEMPLATE.md:45` | `workflows/examples/adr-step.md:4` | 🟢 VERIFIED |
| **REQ-ARCH-03** | QA Verification Contracts | [SPEC-PLAN-002-architecture.md](SPEC-PLAN-002-architecture.md) | `templates/PLAN_TEMPLATE.md:70` | `tests/test_plan_runner.py:8`, `tests/test_plan_runner.py:52` | 🟢 VERIFIED |
| **REQ-DISC-01** | Stack & Framework Detection | [SPEC-PLAN-001-discovery.md](SPEC-PLAN-001-discovery.md) | `tools/context_discovery.py:11`, `tools/context_discovery.py:63` | `tests/test_context_discovery.py:4`, `tests/test_context_discovery.py:29` | 🟢 VERIFIED |
| **REQ-DISC-02** | Structural Boundary Discovery | [SPEC-PLAN-001-discovery.md](SPEC-PLAN-001-discovery.md) | `tools/context_discovery.py:12`, `tools/context_discovery.py:166` | `tests/test_context_discovery.py:5`, `tests/test_context_discovery.py:37` | 🟢 VERIFIED |
| **REQ-DISC-03** | Interface & Route Discovery | [SPEC-PLAN-001-discovery.md](SPEC-PLAN-001-discovery.md) | `tools/context_discovery.py:13`, `tools/context_discovery.py:191` | `tests/test_context_discovery.py:6`, `tests/test_context_discovery.py:49` | 🟢 VERIFIED |
| **REQ-DISC-04** | Context Snapshotting | [SPEC-PLAN-001-discovery.md](SPEC-PLAN-001-discovery.md) | `tools/context_discovery.py:14`, `tools/context_discovery.py:239` | `tests/test_context_discovery.py:7`, `tests/test_context_discovery.py:73` | 🟢 VERIFIED |
| **REQ-HAND-01** | Git Commitment Automation | [SPEC-PLAN-006-handoff.md](SPEC-PLAN-006-handoff.md) | `tools/plan_runner.py:15`, `tools/plan_runner.py:244` | `workflows/ticketless-plan.md:15`, `workflows/jira-plan.md:16` | 🟢 VERIFIED |
| **REQ-HAND-02** | Provenance & Metadata Injection | [SPEC-PLAN-006-handoff.md](SPEC-PLAN-006-handoff.md) | `tools/plan_runner.py:16`, `tools/plan_runner.py:245` | `workflows/ticketless-plan.md:16`, `workflows/jira-plan.md:17` | 🟢 VERIFIED |
| **REQ-HAND-03** | 02-exe Intake & Pull Protocol | [SPEC-PLAN-006-handoff.md](SPEC-PLAN-006-handoff.md) | `tools/plan_runner.py:17`, `tools/plan_runner.py:368` | `workflows/plan-commit-handoff.md:15`, `tests/test_plan_runner.py:11` | 🟢 VERIFIED |
| **REQ-HAND-04** | Agent Persona Operating Standards | [SPEC-PLAN-006-handoff.md](SPEC-PLAN-006-handoff.md) | `tools/traceability_checker.py:8`, `AGENTS.md:3` | `AGENTS.md:4` | 🟢 VERIFIED |
| **REQ-PACK-01** | Standardized Plan Markdown Schema | [SPEC-PLAN-005-packaging.md](SPEC-PLAN-005-packaging.md) | `tools/plan_runner.py:13`, `tools/plan_runner.py:97` | `tests/test_plan_validator.py:4`, `tests/test_plan_validator.py:72` | 🟢 VERIFIED |
| **REQ-PACK-02** | Deterministic Plan Naming & Storage | [SPEC-PLAN-005-packaging.md](SPEC-PLAN-005-packaging.md) | `tools/plan_runner.py:14`, `tools/plan_runner.py:98` | `tests/test_plan_runner.py:7`, `tests/test_plan_runner.py:51` | 🟢 VERIFIED |
| **REQ-PACK-03** | Automated Plan Completeness Linting | [SPEC-PLAN-005-packaging.md](SPEC-PLAN-005-packaging.md) | `tools/plan_validator.py:8`, `tools/plan_validator.py:39` | `tests/test_plan_validator.py:5`, `tests/test_plan_validator.py:73` | 🟢 VERIFIED |
| **REQ-TASK-01** | Atomic Task Decomposition | [SPEC-PLAN-003-decomposition.md](SPEC-PLAN-003-decomposition.md) | `tools/task_graph.py:7`, `tools/task_graph.py:26` | `workflows/examples/task-breakdown-step.md:3`, `tests/test_task_graph.py:4` | 🟢 VERIFIED |
| **REQ-TASK-02** | Explicit Dependency Declaration | [SPEC-PLAN-003-decomposition.md](SPEC-PLAN-003-decomposition.md) | `tools/task_graph.py:8`, `tools/task_graph.py:27` | `workflows/examples/task-breakdown-step.md:4`, `tests/test_task_graph.py:5` | 🟢 VERIFIED |
| **REQ-TASK-03** | DAG Validation & Cycle Detection | [SPEC-PLAN-003-decomposition.md](SPEC-PLAN-003-decomposition.md) | `tools/task_graph.py:9`, `tools/task_graph.py:113` | `tests/test_plan_runner.py:112`, `tests/test_task_graph.py:6` | 🟢 VERIFIED |
| **REQ-TASK-04** | Topological Wave Batching | [SPEC-PLAN-003-decomposition.md](SPEC-PLAN-003-decomposition.md) | `tools/task_graph.py:10`, `tools/task_graph.py:204` | `workflows/examples/task-breakdown-step.md:5`, `tests/test_plan_runner.py:137` | 🟢 VERIFIED |
| **REQ-WORK-01** | Jira-Driven Planning Workflow | [SPEC-PLAN-004-workflows.md](SPEC-PLAN-004-workflows.md) | `tools/jira_client.py:11`, `tools/jira_client.py:59` | `workflows/jira-plan.md:14`, `workflows/authoring-guide.md:28` | 🟢 VERIFIED |
| **REQ-WORK-02** | Ticketless Planning Workflow | [SPEC-PLAN-004-workflows.md](SPEC-PLAN-004-workflows.md) | `tools/plan_runner.py:49`, `workflows/ticketless-plan.md:13` | `workflows/ticketless-plan.md:14`, `tests/test_plan_runner.py:5` | 🟢 VERIFIED |
| **REQ-WORK-03** | Jira Two-Way Synchronization | [SPEC-PLAN-004-workflows.md](SPEC-PLAN-004-workflows.md) | `tools/jira_client.py:12`, `tools/jira_client.py:120` | `workflows/jira-plan.md:15`, `workflows/examples/jira-sync-step.md:3` | 🟢 VERIFIED |
| **REQ-WORK-04** | Workflow Runbook Schema & Linting | [SPEC-PLAN-004-workflows.md](SPEC-PLAN-004-workflows.md) | `tools/plan_validator.py:9`, `tools/plan_validator.py:104` | `tests/test_plan_validator.py:6`, `tests/test_plan_validator.py:88` | 🟢 VERIFIED |
