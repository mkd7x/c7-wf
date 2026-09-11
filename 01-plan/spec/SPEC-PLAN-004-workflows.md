# SPEC-PLAN-004: Planning Workflows & Integrations

## 1. Purpose & Scope
This specification defines the functional requirements for standardized planning workflows. It covers both Jira-driven planning (external ticketing in the loop) and ticketless/autonomous planning (local briefs and prompts), as well as workflow linting and schema validation.

---

## 2. Functional Requirements

| Req ID | Requirement Title | Specification Description |
| :--- | :--- | :--- |
| **REQ-WORK-01** | Jira-Driven Planning Workflow | The framework must provide a step-by-step runbook (`workflows/jira-plan.md`) and CLI integration to intake Jira issues, fetch summary, description, acceptance criteria, components, and format plan tasks with Jira keys. |
| **REQ-WORK-02** | Ticketless Planning Workflow | The framework must provide a step-by-step runbook (`workflows/ticketless-plan.md`) and CLI integration to intake ad-hoc natural-language briefs or local specifications with zero external API dependencies. |
| **REQ-WORK-03** | Jira Two-Way Synchronization | For Jira workflows, the framework must provide capabilities to post structured plan summary comments, transition issue status, and optionally generate Jira child subtasks from task DAGs. |
| **REQ-WORK-04** | Workflow Runbook Schema & Linting | All planning runbooks must adhere to standardized markdown schema (YAML frontmatter, prerequisite checks, numbered steps, unique `--step-id` tracking) and be lintable via `plan_runner.py lint-workflow`. |

---

## 3. Acceptance Criteria
1. Running `plan_runner.py intake --workflow jira --ticket <KEY>` retrieves issue details in real or mock/dry-run mode.
2. Running `plan_runner.py intake --workflow adhoc --brief <TEXT>` initializes a valid local session.
3. Running `plan_runner.py sync-jira` posts a formatted markdown comment to Jira or writes a dry-run sync log.
4. `plan_runner.py lint-workflow` verifies runbook syntax, frontmatter metadata, and step conventions.
