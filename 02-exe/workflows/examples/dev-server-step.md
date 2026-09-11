# Example: Dev Server & Readiness Step

<!-- @verifies REQ-WORK-03 -->
<!-- @verifies REQ-DEV-02 -->

Launch background dev server or watch daemon, poll health endpoint, and register teardown traps:

```bash
# 1. Register cleanup trap
trap 'python3 tools/process_manager.py stop --name dev-server 2>/dev/null' EXIT INT TERM

# 2. Start dev server in background
python3 tools/process_manager.py start \
  --cmd "npm run dev" \
  --name dev-server \
  --cwd workspace

# 3. Poll readiness endpoint
python3 tools/process_manager.py wait-ready \
  --url http://127.0.0.1:3000/health \
  --timeout 30
```
