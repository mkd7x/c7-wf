---
id: WF-EXE-SAMPLE-DEV
name: sample-project-dev-server
target: sample-project
prerequisites:
  python: ">=3.10"
timeout_seconds: 180
---

# Dev Server Workflow for Sample Project

<!-- @verifies REQ-WORK-03 -->
<!-- @verifies REQ-DEV-02 -->

### Step 1: Register Teardown Cleanup Trap
Ensure server process terminates cleanly on exit:
```bash
trap 'python3 tools/process_manager.py stop --name sample-api 2>/dev/null' EXIT INT TERM
```

### Step 2: Start Background Service & Await Health
```bash
python3 tools/process_manager.py start --cmd "python3 -m http.server 8080" --name sample-api --cwd workspace
python3 tools/process_manager.py wait-ready --tcp 8080 --timeout 15
```
