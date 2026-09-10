# Code Review Report — `03-qa` Clean Room QA Framework

| Attribute | Value |
| :--- | :--- |
| **Report ID** | CR-QA-001 |
| **Date** | 2026-09-11 |
| **Reviewer** | Autonomous QA Agent (`03-qa`) |
| **Baseline Commit** | `e58be1a` (`main`) |
| **Review Branch** | `qa-framework-code-review` |
| **Scope** | `03-qa/tools/`, `03-qa/workflows/`, `03-qa/spec/`, `03-qa/.gitignore` |
| **Method** | Static source review + live reproduction against `mkd7x/todo-api` on .NET Aspire |
| **Status** | Findings open — remediation recommended before `04-review` sign-off |

All file paths are relative to `03-qa/` unless stated otherwise.

---

## 1. Executive Summary

The framework is functional and well-structured: the tool suite is dependency-free, the audit
schema is consistent, and the clean-room model works end to end. However, the review identified
**19 defects**, of which **10 were reproduced live**. Three are high severity and can produce
**incorrect PASS verdicts or unusable discovery output**, undermining the framework's core
guarantee of trustworthy verification.

| Severity | Count | IDs |
| :--- | :---: | :--- |
| High | 3 | QAF-001, QAF-002, QAF-003 |
| Medium | 10 | QAF-004 … QAF-013 |
| Low | 6 | QAF-014 … QAF-019 |

**Fixed during review (uncommitted):** QAF-002 (`tools/send_http_req.py`).

---

## 2. Severity Definitions

- **High** — Can yield a false verdict, block a workflow, or make discovery unusable.
- **Medium** — Degrades reliability, correctness, or spec conformance; has a workaround.
- **Low** — Cosmetic, ergonomic, or latent; low likelihood or low impact.

---

## 3. Findings Summary

| ID | Severity | Component | Summary | Evidence |
| :--- | :--- | :--- | :--- | :--- |
| QAF-001 | High | `tools/qa_runner.py` | `report` ignores `--status` when audit log is non-empty | Reproduced |
| QAF-002 | High | `tools/send_http_req.py` | Expected 4xx/5xx recorded as `FAIL` in audit | Reproduced / fixed |
| QAF-003 | High | `tools/test_discovery.py` | No .NET detection; junk commands mined from README tree art | Reproduced |
| QAF-004 | Medium | `tools/qa_runner.py` | `exec --cmd "... &"` hangs until timeout (inherited stdout) | Reproduced |
| QAF-005 | Medium | `tools/qa_runner.py` | `lint-workflow` advisory only; accepts non-compliant runbooks | Reproduced |
| QAF-006 | Medium | `tools/qa_runner.py` | `exec` steps are not audited (no `--step-id`) | Source |
| QAF-007 | Medium | `tools/qa_runner.py` | `setup-cleanroom` deletes tracked `target-repo/.gitkeep` | Reproduced |
| QAF-008 | Medium | `tools/wait_for_service.py` | HTTPS polling fails on self-signed certs (no `--insecure`) | Reproduced |
| QAF-009 | Medium | `tools/send_http_req.py` | Redirects are transparent; 3xx cannot be asserted | Reproduced |
| QAF-010 | Medium | `tools/traceability_checker.py` | "Verified" coverage never computed; conflates tags | Reproduced |
| QAF-011 | Medium | `tools/run_sql_cmd.py` | Advertises postgres/mysql; docker path only supports mssql | Source |
| QAF-012 | Medium | `tools/query_blob_storage.py` | `--step-id` must precede subcommand; binary `get` corrupts | Reproduced |
| QAF-013 | Medium | `tools/audit_logger.py` | `runs/latest` reused; no per-run isolation | Reproduced |
| QAF-014 | Low-Med | `tools/qa_runner.py` | Target wiped before clone; failed clone leaves empty sandbox | Source |
| QAF-015 | Low-Med | `tools/qa_runner.py` | Timeout does not kill the process tree (orphans) | Source |
| QAF-016 | Low | `tools/qa_runner.py` | Report always appends `...`; empty tool args rendered | Reproduced |
| QAF-017 | Low | `tools/test_discovery.py` | Keeps inline comments; substring matches prose | Reproduced |
| QAF-018 | Low | `tools/qa_runner.py` | Lint fence regex also captures non-bash fences | Source |
| QAF-019 | Low | `.gitignore` | `workflows/todo-api/` ignored, against per-repo convention | Reproduced |

---

## 4. Detailed Findings

### QAF-001 — `report` discards the agent-provided verdict (High)

**Location:** `tools/qa_runner.py:258` (status computation), `:488-496` (synthetic step fallback).

**Description:** `generate_report` derives the verdict solely from audit records:

```python
overall_status = "PASS" if (total_steps > 0 and failed_steps == 0) else "FAIL"
```

`args.status` is only consulted when the audit log is empty. A workflow that fails in a step not
captured by an audit-logging tool (e.g. `dotnet test` run via `qa_runner.py exec`) can still be
reported as `PASS`.

**Reproduction:**
```bash
python3 tools/qa_runner.py clear-audit
# record a single PASS step, then:
python3 tools/qa_runner.py report --workflow demo --source demo --status FAIL --notes "agent says FAIL"
# -> reports/..._demo_pass.md  |  Overall Status: PASS
```

**Impact:** False sign-off to `04-review`; violates REQ-HAND-01 ("Explicit Status Verdict").

**Recommendation:** Treat the caller's `--status FAIL` as authoritative (logical OR), and/or fail
the report when audited steps and caller status disagree.

---

### QAF-002 — Negative tests mis-recorded as failures (High) — *fixed in working tree*

**Location:** `tools/send_http_req.py` (audit status block).

**Description:** The audit status was `"FAIL" if failures or not res["success"] else "PASS"`.
`res["success"]` is `False` for every HTTP 4xx/5xx, so intentional negative regression checks were
recorded `FAIL` even when `--expect-status` matched.

**Reproduction:** Running the new endpoint regression suite produced 29 audit failures for tests
that all exited `0` (assertions passed). The aggregate report verdict was therefore `FAIL`.

**Impact:** Every regression suite covering error paths produces a corrupt report. High impact
given error-path coverage is a core regression objective.

**Recommendation (applied):** Base audit status on assertion results, treating undeclared HTTP
errors as failures:
```python
assertions_provided = bool(expected_statuses or args.expect_contains or args.expect_json)
step_status = "FAIL" if failures or (not assertions_provided and not res["success"]) else "PASS"
```
**Follow-up:** add a regression test for this tool behavior.

---

### QAF-003 — Discovery is blind to .NET and mines README diagrams (High)

**Location:** `tools/test_discovery.py:71` (substring command extraction), `:188-261` (no .NET
inspector), `:244-255` (doc commands prioritized over heuristics).

**Description:** For the .NET 10 `todo-api` solution the engine reported
`detected_frameworks: ["Generic / Unknown"]` and recommended non-executable commands mined from the
README's ASCII tree:

```
smoke = "└── tests/"
unit  = "└── TodoApi.Application.UnitTests/  # Comprehensive unit tests for CQRS handlers & validators"
```

`extract_markdown_commands` treats any code-block line containing `test` as a runnable command and
does not strip inline comments. The real `dotnet test` line was extracted but deprioritized.

**Impact:** The framework cannot guide testing for its primary ecosystem; agents receive invalid
commands. Violates REQ-DISC-02, REQ-DISC-03, REQ-DISC-04.

**Recommendation:**
1. Add `inspect_dotnet()` keyed on `*.sln` / `*.slnx` / `*.csproj` recommending
   `dotnet build <solution> -c Release` and `dotnet test`.
2. Require extracted lines to begin with a known runner or `$`, and strip trailing `#` comments.
3. Exclude lines containing box-drawing glyphs (`└`, `├`, `─`).

---

### QAF-004 — `exec` hangs on backgrounded commands (Medium-High)

**Location:** `tools/qa_runner.py:112-119`.

**Description:** `execute_step` uses `subprocess.run(..., capture_output=True)`. A background child
spawned with `&` inherits the stdout/stderr pipes, so `communicate()` blocks until the child exits
— the direct shell returns immediately, but the call does not.

**Reproduction:**
```bash
python3 tools/qa_runner.py exec --cmd "sleep 8 &" --timeout 3
# -> [TIMEOUT] Command exceeded 3s
```

**Impact:** The canonical pattern documented in `AGENTS.md` and the workflow template
(`qa_runner.py exec --cmd "npm start &"`) always times out unless the caller redirects output to a
file. Silent foot-gun for workflow authors.

**Recommendation:** Detach background execution (`stdin=DEVNULL`, `start_new_session=True`, redirect
to a log) or document/enforce `> /tmp/<svc>.log 2>&1 &`.

---

### QAF-005 — Workflow linter is advisory only (Medium)

**Location:** `tools/qa_runner.py:169-228`; claim in `workflows/authoring-guide.md:99-103`.

**Description:** Missing frontmatter, missing `--step-id`, and missing teardown are emitted as
*warnings*; `is_valid = len(errors) == 0`, so the command exits `0`. The authoring guide claims the
linter verifies "valid CLI options", but no CLI flag validation is implemented.

**Reproduction:** a bare runbook with no frontmatter, no `--step-id`, and no cleanup returns exit 0.

**Impact:** Non-compliant runbooks pass CI; REQ-WORK-01..04 compliance is unenforced.

**Recommendation:** Promote structural checks to errors, parse frontmatter YAML, and validate tool
flags against a per-tool allow-list.

---

### QAF-006 — `exec` steps are invisible to the audit/report (Medium)

**Location:** `tools/qa_runner.py:360-364` (subparser), `:419-421` (handler).

**Description:** `exec` neither accepts `--step-id` nor calls `audit_logger`. Build and test
commands therefore never appear in audit-driven reports. The `unit-test.md` workflow required a
custom Python block invoking `audit_logger.record_step` to make test results visible.

**Impact:** Reports omit the most important verification steps; combined with QAF-001 this can mask
failures entirely.

**Recommendation:** Add `--step-id` to `exec` and record command, exit code, duration, and a
truncated stdout/stderr.

---

### QAF-007 — `setup-cleanroom` deletes tracked `.gitkeep` (Medium)

**Location:** `tools/qa_runner.py:85` (`clean_directory_contents(target, preserve_gitkeep=False)`),
`:37-60`.

**Description:** The git-clone path passes `preserve_gitkeep=False`, removing `target-repo/.gitkeep`
and never recreating it. The file is tracked by the parent repository.

**Reproduction:** after `setup-cleanroom`, `git status` shows ` D target-repo/.gitkeep`.

**Impact:** Every clean-room setup dirties the parent repository, conflicting with REQ-ISO-03
("`git status` remains clean").

**Recommendation:** Always preserve/recreate `.gitkeep`, including the clone path.

---

### QAF-008 — HTTPS readiness polling is unusable (Medium)

**Location:** `tools/wait_for_service.py:40-62`.

**Description:** `wait_for_http` uses `urllib.request.urlopen` with default TLS verification and
exposes no insecure option. The Aspire dashboard serves a self-signed certificate and redirects
HTTP→HTTPS (307), so `--url` polling always times out. Only `--tcp` worked during review.

**Impact:** Agents cannot poll HTTPS health endpoints (Aspire dashboard, local dev certs), forcing
TCP workarounds that verify less.

**Recommendation:** Add `--insecure` (or `--ca-cert`) building a custom `ssl.SSLContext`.

---

### QAF-009 — Redirects cannot be asserted (Medium)

**Location:** `tools/send_http_req.py` (request send via `urlopen`).

**Description:** `urlopen` follows redirects transparently; neither the final URL nor the `Location`
chain is exposed, and there is no `--no-redirect`. `GET /` (302 → `/scalar/v1`) can only be asserted
as a terminal `200`.

**Impact:** Redirect contracts (REQ-API-003) cannot be verified directly.

**Recommendation:** Add `--no-redirect` and record `redirected_url`/`Location` in the audit output.

---

### QAF-010 — Traceability "verified" claim is unbacked (Medium)

**Location:** `tools/traceability_checker.py:115` (`verified_count = verified_by or implemented_by`),
`:159-171` (reporting), `spec/TRACEABILITY_MATRIX.md`.

**Description:** The checker reports only implementation coverage. `verified_count` conflates
`@verifies` with `@implements`, is never printed, and is not part of `--strict`. The matrix still
claims "Verified by Automated Tests/Reports: 24/24".

**Impact:** The 100% verified claim is not machine-validated; traceability can regress unnoticed.

**Recommendation:** Compute verified coverage separately (require `@verifies`), print it, and fail
`--strict` when either coverage is below 100%.

---

### QAF-011 — SQL tool advertises unsupported engines (Medium)

**Location:** `tools/run_sql_cmd.py:184-185`; module docstring and `--engine` choices.

**Description:** The docstring promises containerized SQL Server, PostgreSQL, and MySQL, and the CLI
accepts `--engine postgres`, but the docker path raises `NotImplementedError` for anything but
`mssql`.

**Impact:** Agents following docs hit an immediate hard failure.

**Recommendation:** Implement postgres (and mysql) or narrow the docstring and `--engine` choices.

---

### QAF-012 — Blob tool CLI ordering and binary safety (Medium)

**Location:** `tools/query_blob_storage.py:47-49` (global args), `:121` (text-only `get`).

**Description:** `--step-id`/`--audit-file` live on the root parser, so they must appear *before* the
subcommand; `... list --dir X --step-id Y` errors. This is inconsistent with every other tool and
with `AGENTS.md` examples. `get` also decodes content as UTF-8, corrupting binary blobs.

**Reproduction:**
```bash
python3 tools/query_blob_storage.py list --dir /tmp --step-id x      # error: unrecognized arguments
python3 tools/query_blob_storage.py --step-id x list --dir /tmp      # works
```

**Recommendation:** Add the global args to each subparser (or use `parents=[common]`); stream bytes
for `get`.

---

### QAF-013 — Audit log has no per-run isolation (Medium)

**Location:** `tools/audit_logger.py:17` (`runs/latest`), `:20-32`.

**Description:** All runs share `runs/latest/audit.jsonl`. Reports aggregate whatever is present
unless `clear-audit` is explicitly called first.

**Reproduction:** a regression report absorbed steps from a prior unit-test run because the audit
was not cleared.

**Impact:** Cross-contamination of reports; misleading step counts and verdicts.

**Recommendation:** Create a timestamped run directory per invocation (and symlink `latest`), or
auto-clear at workflow start.

---

### QAF-014 — Destructive setup ordering (Low-Medium)

**Location:** `tools/qa_runner.py:85-97`.

**Description:** `target-repo/` is wiped before the clone is attempted. If the clone fails (bad URL,
network), the sandbox is left empty with no rollback.

**Recommendation:** Clone/copy to a temporary sibling directory, verify success, then atomically
replace `target-repo/`.

---

### QAF-015 — Timeout does not kill the process tree (Low-Medium)

**Location:** `tools/qa_runner.py:100-153`.

**Description:** `subprocess.run(..., timeout=...)` terminates only the direct shell child. Grandchild
processes (`dotnet`, `npm`, containers) can survive and leak resources.

**Recommendation:** Launch in a new session/process group and kill the whole group on timeout.

---

### QAF-016 — Report rendering defects (Low)

**Location:** `tools/qa_runner.py:282` (unconditional `...` truncation), `:266` (command description).

**Description:** Output snippets always end with `...` even when short, and non-HTTP tool steps render
as `wait_for_service ( )` / `dotnet-test ( )` because only `input.method`/`input.url` are inspected.

**Recommendation:** Append `...` only when truncation occurs; render a tool-specific description
from `input.target`/`input.project`.

---

### QAF-017 — Discovery command hygiene (Low)

**Location:** `tools/test_discovery.py:71`.

**Description:** Extracted commands retain inline comments (e.g. `... # Comprehensive unit tests ...`)
and match keywords as bare substrings anywhere in a line (`python`, `make`), yielding false positives
from prose.

**Recommendation:** Strip trailing comments and match command prefixes (`pytest`, `dotnet test`,
`npm test`, `make `, …) at line start.

---

### QAF-018 — Lint fence parsing is loose (Low)

**Location:** `tools/qa_runner.py:210`.

**Description:** `re.findall(r'```(?:bash|sh)?(.*?)```', ...)` also captures ` ```json ` blocks and can
mis-associate tool references across unrelated blocks.

**Recommendation:** Parse fences with a language tag allow-list and track block boundaries.

---

### QAF-019 — `.gitignore` blocks per-repo runbooks (Low)

**Location:** `.gitignore:33` (`workflows/todo-api/`).

**Description:** The ignore rule prevents committing the per-repository workflows that the framework's
own convention (`workflows/<repo-name>/`) defines. Work generated for `todo-api` (unit + regression
suites) cannot be version-controlled without overriding the rule.

**Recommendation:** Remove the rule (or narrow it to transient artifacts) so runbooks are reviewable
and traceable.

---

## 5. Positive Observations

- Zero third-party runtime dependencies; tools run on a stock Python 3 install.
- Consistent audit schema (`timestamp`, `step_id`, `tool`, `status`, `duration_ms`, `input`,
  `output`, `assertions`) across all four specialized tools.
- Clean-room isolation model and `--step-id` chaining via `get-step-output` are sound in principle
  and worked well once negative-test audit status was fixed.
- Template-driven report generation with deterministic filenames satisfies REQ-REP-01/03.
- Traceability annotations (`@implements` / `@verifies`) are present and self-documenting.

---

## 6. Recommended Remediation Order

1. **QAF-001** — verdict integrity (blocker for trustworthy sign-off).
2. **QAF-003** — discovery correctness for .NET targets.
3. **QAF-002** — land the negative-test audit fix with a tool regression test.
4. **QAF-006 / QAF-013** — make `exec` auditable and isolate runs; removes the need for ad-hoc
   Python audit blocks.
5. **QAF-004 / QAF-007 / QAF-008** — workflow execution robustness (backgrounding, `.gitkeep`, TLS).
6. **QAF-005 / QAF-010** — enforce lint and traceability gates in CI.
7. Remaining Medium/Low items.

---

## 7. Appendix — Verification Environment

- Target under test: `https://github.com/mkd7x/todo-api` (`.NET 10`, Aspire AppHost `13.5.3`).
- Orchestration: Aspire AppHost → SQL Server 2022 container + `TodoApi.ApiService` at
  `http://localhost:5105`.
- Harness: markdown `bash` blocks extracted and executed sequentially; 53/54 blocks passed, the one
  failure being the downstream `REQ-API-002` contract check.
- Key reproduction commands are embedded in each finding above.

**Out of scope note:** while exercising the framework, a downstream defect was observed in the
target repository (400 `ValidationProblemDetails` omits the `errors` dictionary). It is not counted
in this framework review but is documented in `workflows/todo-api/regression-errors.md`.

---

*End of report.*
