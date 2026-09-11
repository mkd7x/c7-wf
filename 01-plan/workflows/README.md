# Planning Workflows (`01-plan/workflows`)

## Overview
This directory houses standardized, executable planning runbooks for autonomous agents. Just like `03-qa` runbooks, planning runbooks are **not static prose**—they are step-by-step operating procedures that agents execute sequentially using the `01-plan/tools` CLI suite.

---

## Workflow Catalog

| Workflow | File | Ingestion Mode | Primary Use Case |
| :--- | :--- | :--- | :--- |
| **Jira-Driven Planning** | [`jira-plan.md`](jira-plan.md) | Jira REST API / Webhooks | Sprint tasks, customer bugs, backlog tickets with Jira issue keys |
| **Ticketless / Autonomous** | [`ticketless-plan.md`](ticketless-plan.md) | Local brief / User prompt / PR | Ad-hoc features, local refactorings, research spikes, offline dev |
| **Commit & Handoff** | [`plan-commit-handoff.md`](plan-commit-handoff.md) | Git repository | Committing plan to git and gating handoff to `02-exe` |

---

## Authoring New Workflows
See [authoring-guide.md](authoring-guide.md) for runbook authoring standards, frontmatter requirements, and linting procedures.
