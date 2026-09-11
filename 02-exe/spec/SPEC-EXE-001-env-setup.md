# SPEC-EXE-001: Environment Configuration & Credential Retrieval

## 1. Summary
Different repositories require different local setup protocols, including fetching credentials from secure vaults, synthesizing local `.env` configuration files from templates, and verifying toolchain readiness. This specification defines the environment setup contracts, provider abstractions, and secret redaction guarantees.

## 2. Requirements

| Requirement ID | Title | Description | Acceptance Criteria |
| :--- | :--- | :--- | :--- |
| **REQ-ENV-01** | Declarative Environment Profile Schema | The framework must support declarative environment profiles in workflow frontmatter or configuration files defining needed variables, template paths, and credential sources. | Workflows parse environment profiles specifying variables, sources, and paths without hardcoded credentials. |
| **REQ-ENV-02** | Pluggable Credential Provider Adapters | The environment manager must provide an extensible adapter layer supporting multiple secret backends (environment variables, local files/mocks, 1Password CLI `op`, AWS Secrets Manager, Doppler, Vault). | Credential manager resolves secrets through configured provider adapters with graceful fallbacks. |
| **REQ-ENV-03** | Safe `.env` Synthesis & Gitignore Enforcement | The framework must synthesize target `.env` files from templates (`.env.example`) and verify that target `.env` is ignored by Git before writing. | Generation creates local `.env` and aborts or warns if the destination file is tracked by git. |
| **REQ-ENV-04** | In-Memory Secret Redaction & Log Masking | All resolved credentials and secret values must be registered in an in-memory redaction registry and replaced with `***REDACTED***` across all audit logs, execution state files, and console streams. | Secret values never appear in plaintext in `runs/latest/audit.jsonl` or stdout/stderr logs. |

## 3. Traceability Links
- **Implementation**:
  - `tools/env_manager.py`
  - `tools/audit_logger.py`
- **Workflows & Examples**:
  - `workflows/examples/credential-step.md`
  - `workflows/examples/env-setup-step.md`
- **Verification**:
  - `tests/test_env_manager.py`
