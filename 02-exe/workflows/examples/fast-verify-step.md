# Example: Fast Inner-Loop Verification Step

<!-- @verifies REQ-DEV-03 -->

Execute fast incremental checks (linter, typechecker, and scoped unit tests) against modified code:

```bash
# Execute fast test loop for a specific task
python3 tools/exe_runner.py test-loop \
  --cmd "ruff check . && mypy . && pytest -m 'not slow'" \
  --task-id TASK-101 \
  --step-id step-04-task-verify
```
