---
id: WF-EXE-SAMPLE-001
name: sample-dev-lifecycle
target: mkd7x/sample-repo
prerequisites:
  node: ">=20.0"
  docker: false
environment:
  profile: local-dev
  env_file: .env
  template: .env.example
  secrets:
    - name: API_KEY
      provider: env-var
      reference: SAMPLE_API_KEY
      fallback: mock-key-123
timeout_seconds: 300
---

# Development Execution Runbook: {{ target }}

## Step 1: Initialize Workspace & Environment
<!-- @verifies REQ-ENV-01 -->
<!-- @verifies REQ-ENV-03 -->
Synthesize local `.env` configuration file from template and verify credentials:
```bash
python3 tools/env_manager.py setup --workspace workspace --template .env.example --output .env
```

## Step 2: Register Process Teardown Trap
<!-- @verifies REQ-WORK-03 -->
Ensure all background watchers or dev servers terminate cleanly upon script exit or cancellation:
```bash
trap 'python3 tools/process_manager.py stop --name sample-dev-server 2>/dev/null' EXIT INT TERM
```

## Step 3: Start Development Server & Poll Readiness
<!-- @verifies REQ-DEV-02 -->
Start the local application dev server in background and await health status:
```bash
# Launch background dev server
python3 tools/process_manager.py start --cmd "npm run dev" --name sample-dev-server --cwd workspace

# Poll health readiness
python3 tools/process_manager.py wait-ready --url http://127.0.0.1:3000/health --timeout 30
```

## Step 4: Execute Implementation Task Wave
<!-- @verifies REQ-DEV-01 -->
Implement changes according to active task DAG from `01-plan`.

## Step 5: Fast Inner-Loop Verification
<!-- @verifies REQ-DEV-03 -->
Verify local modifications with fast linter, typechecker, and scoped tests before committing:
```bash
python3 tools/exe_runner.py test-loop --cmd "npm run lint && npm test -- --changedSince=HEAD~1" --task-id TASK-001
```

## Step 6: Atomic Task Git Commit
<!-- @verifies REQ-HAND-01 -->
Commit the completed wave changes referencing the plan task ID:
```bash
python3 tools/exe_runner.py commit --task-id TASK-001 --message "add user validation logic"
```

## Step 7: Packaging QA Handoff Manifest
<!-- @verifies REQ-HAND-02 -->
Compile execution evidence and notify `03-qa`:
```bash
python3 tools/exe_runner.py handoff --notes "Task wave 1 verified with fast test-loop."
```
