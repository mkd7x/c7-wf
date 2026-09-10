# SPEC-QA-004: Audit Logging & Markdown Report Generation

## 1. Summary
The framework must generate consistent, human-readable, and machine-parseable test audit reports for every workflow execution, preserving stdout, stderr, timestamps, and pass/fail metrics.

## 2. Requirements

| Requirement ID | Title | Description | Acceptance Criteria |
| :--- | :--- | :--- | :--- |
| **REQ-REP-01** | Template-Driven Reports | Reports must be generated using `templates/REPORT_TEMPLATE.md` with standardized placeholders. | Markdown output contains metadata header, execution summary, step tables, and details. |
| **REQ-REP-02** | Execution Metrics | Capture exact duration, exit code, and stdout/stderr for every executed step. | Detailed step section in report includes code blocks for output and error logs. |
| **REQ-REP-03** | Deterministic Naming | Saved reports must follow the format `YYYYMMDD_HHMMSS_<workflow>_<status>.md` in `reports/`. | Files are timestamped and marked with workflow name and status. |
| **REQ-REP-04** | Defect Diagnostics | In the event of a failure, the report must aggregate defect analysis and reproduction snippets. | Failed steps generate actionable diagnostic sections with commands and error messages. |

## 3. Traceability Links
- **Implementation**:
  - `generate_report` in `03-qa/tools/qa_runner.py`
  - `03-qa/templates/REPORT_TEMPLATE.md`
- **Workflows**:
  - All workflows in `03-qa/workflows/`
- **Verification**:
  - Validated with generated report `reports/20260910_231710_smoke_pass.md`
