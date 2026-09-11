# Example: Jira Two-Way Synchronization Step

<!-- @verifies REQ-WORK-03 -->

This example demonstrates how an agent posts the completed plan back to Jira and transitions the issue.

```bash
# Sync plan metadata and comment to Jira
python3 tools/plan_runner.py sync-jira \
  --ticket PROJ-1024 \
  --file plans/20260911_PROJ-1024_auth_jwt.md \
  --transition "In Progress" \
  --create-subtasks \
  --step-id step-06-sync-jira
```

### Expected Agent Output:
```
=== Jira Synchronization: PROJ-1024 ===
[✓] Fetched issue PROJ-1024: "Implement JWT Authentication"
[✓] Posted execution plan summary comment to PROJ-1024
[✓] Created 3 child subtasks:
    - PROJ-1025: [TASK-01] Database Schema Migration
    - PROJ-1026: [TASK-02] Core JWT Token Service
    - PROJ-1027: [TASK-03] Authentication Middleware & Endpoints
[✓] Transitioned PROJ-1024 status: "To Do" -> "In Progress"
[✓] Jira synchronization complete.
```
