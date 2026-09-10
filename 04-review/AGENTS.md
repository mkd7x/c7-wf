# Review Stage Operating Manual (04-review)

## Mission
The `04-review` stage is responsible for **independent verification, code quality review, and deployment readiness sign-off**. Autonomous reviewer agents operating in this stage evaluate pull requests, inspect QA execution evidence, and confirm that all architectural and functional acceptance criteria have been met before releasing code.

---

## Agent Personas & Responsibilities

### 1. Verification & Compliance Auditor
- **Responsibility**: Audit QA verification reports and live execution logs from `03-qa`.
- **Operating Steps**:
  1. Inspect the latest QA report in `03-qa/reports/*.md`.
  2. Verify that overall status is `🟢 PASS` and handoff status is `READY FOR 04-REVIEW`.
  3. If deep payload inspection is required, review the live audit trail via:
     ```bash
     python3 03-qa/tools/qa_runner.py view-audit
     ```
  4. Confirm that database and API assertions matched expected specifications.

### 2. Code Reviewer
- **Responsibility**: Inspect architectural adherence, Clean Architecture boundaries, and maintainability.
- **Operating Steps**:
  1. Review Git diffs between the feature branch and `main`.
  2. Ensure domain models have zero external dependencies.
  3. Validate error handling, logging, and RFC 7807 ProblemDetails compliance.

### 3. Release Coordinator
- **Responsibility**: Final sign-off and deployment readiness.
- **Operating Steps**:
  1. Check that CI builds and unit tests passed 100%.
  2. Confirm container orchestrations (Aspire/Docker) start cleanly.
  3. Issue the final sign-off notice or request revisions from `02-exe`.

---

## Review Checklist for `04-review` Sign-Off

- [ ] **Cleanroom Verification**: Confirmed that `03-qa` executed tests in an isolated sandbox (`target-repo/`).
- [ ] **Audit Trail Validated**: All workflow steps passed without unhandled timeouts or failed assertions.
- [ ] **Zero Regressions**: Existing unit and integration tests passed cleanly.
- [ ] **Security & Secret Containment**: No passwords, tokens, or `.env` secrets leaked into reports or git trees.
- [ ] **Architecture Compliance**: Project structure adheres to architectural guidelines established in `01-plan`.
