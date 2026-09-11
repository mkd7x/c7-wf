# Execution Stage Handoff to QA (02-exe ➔ 03-qa)

**Handoff Timestamp**: `{{ timestamp }}`  
**Target Repository**: `{{ target }}`  
**Feature Branch**: `{{ target_branch }}`  
**Commit SHA**: `{{ commit_sha }}`  
**Overall Status**: `{{ status }}`  

---

## 1. Implementation Summary
- **Plan Reference**: `{{ plan_file }}`
- **Completed Tasks**:
  - `{{ task_list }}`

---

## 2. Fast Verification Results (Inner Dev Loop)
| Step ID | Command | Duration | Status |
| :--- | :--- | :--- | :--- |
| `{{ step_id }}` | `{{ command }}` | `{{ duration_ms }}ms` | `{{ status }}` |

---

## 3. QA Execution Instructions
To verify this build in clean room isolation:
```bash
python3 tools/qa_runner.py setup-cleanroom --source {{ target_branch }}
python3 tools/qa_runner.py report --workflow smoke --status PASS --notes "Verified handoff from 02-exe"
```
