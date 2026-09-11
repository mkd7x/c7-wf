# Workflow Authoring Guide (`02-exe`)

## Overview
This guide provides standards and validation rules for authoring agent-executable development runbooks in `02-exe`.

<!-- @verifies REQ-DISC-01 -->
<!-- @verifies REQ-DISC-02 -->
<!-- @verifies REQ-DISC-03 -->
<!-- @verifies REQ-DISC-04 -->

## Core Requirements for Execution Runbooks

### 1. YAML Frontmatter
Every workflow must begin with a YAML frontmatter block declaring target repo, prerequisites, and environment profiles:
```yaml
---
id: WF-EXE-<REPO>-001
name: dev-lifecycle
target: <org>/<repo-name>
prerequisites:
  node: ">=20"
  docker: true
environment:
  profile: local-dev
  template: .env.example
  output: .env
timeout_seconds: 300
---
```

### 2. Mandatory Cleanup Traps
All runbooks that launch background processes or container daemons must include a shell teardown trap:
```bash
trap 'python3 tools/process_manager.py stop --name dev-server 2>/dev/null' EXIT INT TERM
```

### 3. Step Headings & Traceability
Each distinct phase must be structured under an explicit step heading (`### Step N: <Title>`) with optional traceability annotations:
```markdown
<!-- @verifies REQ-DEV-03 -->
### Step 3: Fast Inner-Loop Verification
```

---

## Validating Runbooks with `lint-workflow`

Validate workflow syntax, mandatory fields, and cleanup traps:
```bash
python3 tools/exe_runner.py lint-workflow --file workflows/<repo>/setup.md
```
Enforce strict validation (warnings treated as failures):
```bash
python3 tools/exe_runner.py lint-workflow --file workflows/<repo>/setup.md --strict
```
