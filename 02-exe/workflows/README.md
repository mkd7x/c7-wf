# Workflows Catalog (`02-exe/workflows`)

## Overview
The `workflows/` directory contains machine-executable development runbooks designed for autonomous agents. Each repository has a dedicated subdirectory specifying its setup, background dev server lifecycle, and fast inner-loop verification routines.

<!-- @verifies REQ-WORK-01 -->

## Directory Structure

```
workflows/
├── README.md                      # Catalog & directory conventions
├── authoring-guide.md             # Standards, YAML frontmatter, and linter rules
├── examples/                      # Reusable modular step definitions
│   ├── credential-step.md         # Secret resolution & provider integration
│   ├── env-setup-step.md          # Safe .env synthesis from templates
│   ├── dev-server-step.md         # Launching background dev servers & healthchecks
│   ├── fast-verify-step.md        # Fast inner-loop test & lint execution
│   └── workflow-template.md       # Standard scaffold for new project workflows
└── <repo-name>/                   # Concrete project execution runbooks
    ├── setup.md                   # Environment setup & dependency installation
    ├── start-dev.md               # Dev server startup & supervision
    └── test-loop.md               # Iterative fast test & typecheck loop
```

---

## Workflow Execution SOP for Agents

1. **Intake Plan**:
   ```bash
   python3 tools/exe_runner.py intake
   ```
2. **Setup Local Environment**:
   ```bash
   python3 tools/env_manager.py setup --workspace workspace --template .env.example
   ```
3. **Start Dev Server**:
   ```bash
   python3 tools/process_manager.py start --cmd "npm run dev" --name app-dev
   python3 tools/process_manager.py wait-ready --url http://127.0.0.1:3000/health
   ```
4. **Implement Task Wave**:
   Edit files in `workspace/`.
5. **Execute Fast Verification**:
   ```bash
   python3 tools/exe_runner.py test-loop --task-id TASK-001
   ```
6. **Commit Atomic Changes**:
   ```bash
   python3 tools/exe_runner.py commit --task-id TASK-001 --message "add user validation"
   ```
7. **Package Handoff for QA**:
   ```bash
   python3 tools/exe_runner.py handoff
   ```
