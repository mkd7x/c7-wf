# Execution Plan: {{PLAN_TITLE}}

| Attribute | Value |
| :--- | :--- |
| **Plan ID** | `{{PLAN_ID}}` |
| **Workflow Mode** | `{{WORKFLOW_MODE}}` |
| **Source Ticket / Ref** | `{{SOURCE_REF}}` |
| **Target Repository** | `{{TARGET_REPO}}` |
| **Target Branch** | `{{TARGET_BRANCH}}` |
| **Generated Timestamp** | {{TIMESTAMP}} |
| **Git Commit SHA** | `{{COMMIT_SHA}}` |
| **Overall Status** | **{{STATUS_BADGE}}** (`{{OVERALL_STATUS}}`) |

---

## 1. Executive Summary & Problem Statement

### 1.1 Objective
{{OBJECTIVE_DESCRIPTION}}

### 1.2 Scope Boundaries
- **In-Scope**:
{{IN_SCOPE_ITEMS}}
- **Out-of-Scope**:
{{OUT_OF_SCOPE_ITEMS}}

---

## 2. Discovered Codebase Context

- **Detected Stack / Language**: `{{DETECTED_STACK}}`
- **Frameworks & Libraries**: `{{DETECTED_FRAMEWORKS}}`
- **Architectural Patterns**: `{{ARCHITECTURAL_PATTERNS}}`
- **Relevant Directories**:
{{RELEVANT_DIRECTORIES}}

---

## 3. Architectural Design & ADRs

### 3.1 Architectural Decisions
{{ARCHITECTURAL_DECISIONS}}

### 3.2 Component Boundaries & Interfaces
<!-- @implements REQ-ARCH-02 -->
{{COMPONENT_BOUNDARIES}}

### 3.3 Data Models & Migrations
{{DATA_MODELS_SECTION}}

---

## 4. Work Breakdown Structure & Task DAG

<!-- @implements REQ-TASK-01 -->
<!-- @implements REQ-TASK-02 -->

### 4.1 Execution Waves Summary

{{EXECUTION_WAVES_SUMMARY}}

### 4.2 Task Specifications

{{TASK_SPECIFICATIONS}}

---

## 5. QA Verification Contract for `03-qa`

<!-- @implements REQ-ARCH-03 -->

The following verification criteria must be confirmed by `03-qa` before handoff to `04-review`:

| Verification ID | Category | Target / Endpoint | Expected Result / Contract |
| :--- | :--- | :--- | :--- |
{{QA_CONTRACT_TABLE}}

---

## 6. Handoff Checklist for `02-exe`

<!-- @implements REQ-HAND-03 -->

- [ ] Target branch `{{TARGET_BRANCH}}` checked out or prepared
- [ ] Dependencies and prerequisites verified
- [ ] Task DAG validated with zero circular dependencies
- [ ] Plan committed to Git (`{{COMMIT_SHA}}`)
- [ ] Ready for execution by `02-exe`

**Handoff Gate Status**: `{{HANDOFF_STATUS}}`
