---
id: WF-EXE-SAMPLE-SETUP
name: sample-project-setup
target: sample-project
prerequisites:
  python: ">=3.10"
environment:
  template: .env.example
  output: .env
timeout_seconds: 120
---

# Setup Workflow for Sample Project

<!-- @verifies REQ-ENV-01 -->
<!-- @verifies REQ-ENV-03 -->

### Step 1: Pre-flight Dependencies
Install development dependencies:
```bash
pip install -r workspace/requirements.txt
```

### Step 2: Synthesize Local Environment
Generate local `.env` and verify Git exclusion:
```bash
python3 tools/env_manager.py setup --workspace workspace --template .env.example --output .env
```
