# SPEC-PLAN-006: Version Control Handoff & Exe Protocol

## 1. Purpose & Scope
This specification defines the functional requirements for committing execution plans to Git and providing a standardized pull protocol for the downstream `02-exe` stage. Regardless of workflow origin, plans must be committed to Git with full provenance.

---

## 2. Functional Requirements

| Req ID | Requirement Title | Specification Description |
| :--- | :--- | :--- |
| **REQ-HAND-01** | Git Commitment Automation | The framework must provide a CLI command (`plan_runner.py commit-plan`) that stages the validated plan file, generates a standardized commit message, and commits to the current or designated git branch. |
| **REQ-HAND-02** | Provenance & Metadata Injection | The plan header must record provenance metadata including Git Commit SHA, branch name, workflow mode (`JIRA` vs `ADHOC`), source ticket/brief reference, and handoff timestamp. |
| **REQ-HAND-03** | 02-exe Intake & Pull Protocol | The framework must expose a machine-readable query interface (`plan_runner.py get-latest-plan` or `get-plan --ticket <KEY>`) allowing `02-exe` to pull the active plan, read target branch details, and extract the execution task DAG. |
| **REQ-HAND-04** | Agent Persona Operating Standards | Operating personas (Context Analyst, System Architect, Work Breakdown Specialist), standard operating procedures, and safety rules must be formally documented and enforced in `AGENTS.md`. |

---

## 3. Acceptance Criteria
1. `plan_runner.py commit-plan --file <plan> [--push]` verifies git status, stages the file, creates a commit, and updates the plan header with the resulting Git commit hash.
2. `plan_runner.py get-latest-plan --json` outputs the plan path, commit hash, target branch, and extracted task DAG.
3. `AGENTS.md` defines clear roles, step-by-step SOP, and safety constraints.
