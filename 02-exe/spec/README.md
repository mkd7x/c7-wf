# Specification & Traceability Framework (`02-exe/spec`)

## Overview
This directory contains formal functional specifications for the `02-exe` development execution and dev-loop framework, maintaining bidirectional **Spec-Code Traceability** across:
1. **Specifications (`spec/SPEC-EXE-*.md`)**: The functional requirements and acceptance criteria.
2. **Implementation Code (`tools/`)**: The CLI utilities fulfilling each requirement.
3. **Workflow Runbooks (`workflows/`)**: Standard operating procedures executing the specifications.
4. **Verification Tests (`tests/`)**: Automated test suites validating the implementation.

---

## Traceability Schema

Every specification requirement uses the following identifier format:
`REQ-<CATEGORY>-<INDEX>`

| Category | Prefix | Scope | Spec Document |
| :--- | :--- | :--- | :--- |
| **Environment** | `REQ-ENV` | Credential fetching, env synthesis, secret redaction | [SPEC-EXE-001-env-setup.md](SPEC-EXE-001-env-setup.md) |
| **Discovery** | `REQ-DISC` | Dev script discovery, toolchains, templates, test runners | [SPEC-EXE-002-discovery.md](SPEC-EXE-002-discovery.md) |
| **Workflows** | `REQ-WORK` | Multi-workflow orchestration, frontmatter, teardown traps | [SPEC-EXE-003-workflows.md](SPEC-EXE-003-workflows.md) |
| **Dev Loop** | `REQ-DEV` | Plan intake, process supervision, fast testing, audit logs | [SPEC-EXE-004-devloop.md](SPEC-EXE-004-devloop.md) |
| **Handoff** | `REQ-HAND` | Atomic git commits, QA manifest packaging, persona protocols | [SPEC-EXE-005-handoff.md](SPEC-EXE-005-handoff.md) |

---

## Code & Test Annotation Conventions

To guarantee automated verification of traceability, code and tests must include traceability docstrings/comments:

### In Implementation Code (`tools/`):
```python
# @implements REQ-ENV-02 (Pluggable credential providers)
# @implements REQ-ENV-03 (Safe .env synthesis)
def synthesize_env(...):
    ...
```

### In Workflows & Test Suites (`workflows/`, `tests/`):
```markdown
<!-- @verifies REQ-WORK-01 -->
### Step 1: Initialize Development Environment
```
```python
# @verifies REQ-ENV-04
def test_secret_masking(self):
    ...
```

---

## Traceability Verification Tool

Verify 100% traceability coverage across specs, source code, workflows, and tests using the traceability checker:

```bash
# Check spec-code coverage and regenerate matrix
python3 tools/traceability_checker.py

# Check with strict exit-on-gap mode
python3 tools/traceability_checker.py --strict
```

See [TRACEABILITY_MATRIX.md](TRACEABILITY_MATRIX.md) for the live matrix.
