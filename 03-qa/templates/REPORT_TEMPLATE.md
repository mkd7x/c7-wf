# QA Clean Room Verification Report

| Attribute | Value |
| :--- | :--- |
| **Project Name** | {{PROJECT_NAME}} |
| **Source / Target** | `{{PROJECT_SOURCE}}` |
| **Commit / Reference** | `{{COMMIT_REF}}` |
| **Workflow Executed** | `{{WORKFLOW_NAME}}` |
| **Execution Timestamp** | {{TIMESTAMP}} |
| **Operator / Agent** | {{OPERATOR}} |
| **Overall Status** | **{{STATUS_BADGE}}** (`{{OVERALL_STATUS}}`) |

---

## 1. Executive Summary
- **Verdict**: {{EXECUTIVE_VERDICT}}
- **Total Steps Run**: {{TOTAL_STEPS}}
- **Passed**: {{PASSED_STEPS}}
- **Failed**: {{FAILED_STEPS}}
- **Total Duration**: {{TOTAL_DURATION}}s

{{EXECUTIVE_NOTES}}

---

## 2. Discovered Project Context & Documentation
The clean-room test discovery detected the following context and testing instructions:

- **Documentation Files Found**:
{{DISCOVERED_DOCS}}

- **Detected Framework / Project Type**: `{{DETECTED_FRAMEWORK}}`
- **Recommended Test Commands**:
{{RECOMMENDED_COMMANDS}}

---

## 3. Execution Log & Step Results

| Step # | Step Name | Command | Duration | Exit Code | Result |
| :--- | :--- | :--- | :--- | :--- | :--- |
{{STEP_TABLE_ROWS}}

### Step Details

{{STEP_DETAILS}}

---

## 4. Defect Analysis & Reproduction (if applicable)

{{DEFECT_ANALYSIS}}

---

## 5. Handoff Checklist for `04-review`

- [ ] Clean-room workspace was isolated with no dirty state contamination
- [ ] Project test documentation was reviewed and followed
- [ ] All required tests executed successfully
- [ ] No regression or unexpected failure introduced
- [ ] Ready for architectural / code quality sign-off in `04-review`

**Sign-off Status**: `{{HANDOFF_STATUS}}`
