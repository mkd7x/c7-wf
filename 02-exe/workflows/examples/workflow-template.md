---
id: WF-EXE-EXAMPLE-001
name: generic-dev-loop
target: org/sample-repo
prerequisites:
  git: true
environment:
  template: .env.example
  output: .env
timeout_seconds: 300
---

# Generic Development Workflow Template

<!-- @verifies REQ-WORK-02 -->

### Step 1: Environment & Credential Setup
```bash
python3 tools/env_manager.py setup --workspace workspace --template .env.example --output .env
```

### Step 2: Trap Registration
```bash
trap 'python3 tools/process_manager.py stop --name dev-service 2>/dev/null' EXIT INT TERM
```

### Step 3: Start Dev Server
```bash
python3 tools/process_manager.py start --cmd "npm run dev" --name dev-service --cwd workspace
python3 tools/process_manager.py wait-ready --url http://127.0.0.1:3000/health --timeout 20
```

### Step 4: Fast Verification Loop
```bash
python3 tools/exe_runner.py test-loop --task-id TASK-01
```

### Step 5: Git Commit & Handoff
```bash
python3 tools/exe_runner.py commit --task-id TASK-01 --message "implement user model"
python3 tools/exe_runner.py handoff
```
