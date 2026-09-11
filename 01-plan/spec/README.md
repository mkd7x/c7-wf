# Specification & Traceability Framework (`01-plan/spec`)

## Overview
This directory contains formal functional specifications for the `01-plan` planning and scoping framework. It enforces bidirectional **Spec-Code Traceability** across:
1. **Specifications (`spec/SPEC-PLAN-*.md`)**: Functional requirements, acceptance criteria, and constraints.
2. **Implementation Tools (`tools/`)**: Python CLI tools fulfilling each requirement.
3. **Planning Runbooks (`workflows/`)**: Standard operating runbooks executing the specifications.
4. **Verification Tests (`tests/`)**: Automated unit tests validating the planning tools.

---

## Traceability Schema

Every specification requirement uses the standardized identifier format:
`REQ-<CATEGORY>-<INDEX>`

| Category | Prefix | Scope | Spec Document |
| :--- | :--- | :--- | :--- |
| **Discovery** | `REQ-DISC` | Context inspection, stack detection, schema & route discovery | [SPEC-PLAN-001-discovery.md](SPEC-PLAN-001-discovery.md) |
| **Architecture** | `REQ-ARCH` | Architectural decision records (ADRs), boundaries & QA contracts | [SPEC-PLAN-002-architecture.md](SPEC-PLAN-002-architecture.md) |
| **Decomposition** | `REQ-TASK` | Task decomposition, atomic sizing, DAG dependencies & topological waves | [SPEC-PLAN-003-decomposition.md](SPEC-PLAN-003-decomposition.md) |
| **Workflows** | `REQ-WORK` | Jira ticket intake, ticketless/adhoc planning, Jira sync & workflow linting | [SPEC-PLAN-004-workflows.md](SPEC-PLAN-004-workflows.md) |
| **Packaging** | `REQ-PACK` | Standardized plan template, schema enforcement, deterministic naming | [SPEC-PLAN-005-packaging.md](SPEC-PLAN-005-packaging.md) |
| **Handoff** | `REQ-HAND` | Git plan commitment, SHA provenance, and `02-exe` pull protocol | [SPEC-PLAN-006-handoff.md](SPEC-PLAN-006-handoff.md) |

---

## Code & Test Annotation Conventions

To guarantee automated verification of traceability, source code, runbooks, and test suites must include traceability annotations:

### In Implementation Code (`tools/`):
```python
# @implements REQ-DISC-01 (Stack & framework detection)
# @implements REQ-DISC-02 (Boundary & directory discovery)
def discover_codebase_context(source_path: Path) -> dict:
    ...
```

### In Workflows & Test Suites (`workflows/`, `tests/`):
```markdown
<!-- @verifies REQ-WORK-01 -->
### Step 1: Intake Jira Ticket
Fetch ticket details from Jira REST API...
```

```python
# @verifies REQ-TASK-03
def test_circular_dependency_detection():
    ...
```

---

## Traceability Verification Tool

Verify 100% spec-code traceability coverage:
```bash
python3 tools/traceability_checker.py
```
Or enforce strict verification with zero gaps:
```bash
python3 tools/traceability_checker.py --strict
```
See [TRACEABILITY_MATRIX.md](TRACEABILITY_MATRIX.md) for live mapping details.
