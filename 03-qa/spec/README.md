# Specification & Traceability Framework (`03-qa/spec`)

## Overview
This directory contains formal functional specifications for the `03-qa` clean-room testing system and maintains bidirectional **Spec-Code Traceability** across:
1. **Specifications (`spec/SPEC-QA-*.md`)**: The functional requirements and acceptance criteria.
2. **Implementation Code (`tools/`)**: The source code fulfilling each requirement.
3. **Workflow Runbooks (`workflows/`)**: Standard operating procedures executing the specifications.
4. **Verification Tests (`tests/`)**: Automated tests and fixtures validating the implementation.

---

## Traceability Schema

Every specification requirement uses the following identifier format:
`REQ-<CATEGORY>-<INDEX>`

| Category | Prefix | Scope | Spec Document |
| :--- | :--- | :--- | :--- |
| **Isolation** | `REQ-ISO` | Sandbox containment, clean checkouts, git isolation | [SPEC-QA-001-isolation.md](SPEC-QA-001-isolation.md) |
| **Discovery** | `REQ-DISC` | Instruction & test doc discovery, framework detection | [SPEC-QA-002-discovery.md](SPEC-QA-002-discovery.md) |
| **Workflows** | `REQ-WORK` | Multi-workflow orchestration (smoke, unit, integration) | [SPEC-QA-003-workflows.md](SPEC-QA-003-workflows.md) |
| **Reporting** | `REQ-REP` | Report generation, execution logs, stdout/stderr metrics | [SPEC-QA-004-reporting.md](SPEC-QA-004-reporting.md) |
| **Handoff** | `REQ-HAND` | Sign-off checklist and handoff gating to `04-review` | [SPEC-QA-005-handoff.md](SPEC-QA-005-handoff.md) |

---

## Code & Test Annotation Conventions

To guarantee automated verification of traceability, code and tests must include traceability docstrings/comments:

### In Implementation Code (`tools/`):
```python
# @implements REQ-ISO-01 (Clean-room directory wiping)
# @implements REQ-ISO-02 (Local copy & git clone containment)
def setup_cleanroom(source: str, target: Path = DEFAULT_TARGET):
    ...
```

### In Workflows & Test Fixtures (`workflows/`, `tests/`):
```markdown
<!-- @verifies REQ-WORK-01 -->
### Step 3: Smoke Test Suite
Run the smoke command or fast test suite...
```

---

## Traceability Verification Tool

Verify 100% traceability coverage across specs, source code, and workflows using the traceability checker:

```bash
# Check spec-code coverage and print report
python3 ../tools/traceability_checker.py

# Check with strict exit-on-gap mode
python3 ../tools/traceability_checker.py --strict
```

See [TRACEABILITY_MATRIX.md](TRACEABILITY_MATRIX.md) for the complete live matrix.
