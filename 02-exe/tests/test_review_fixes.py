#!/usr/bin/env python3
"""
Regression tests for 02-exe review fixes.
Covers: setup-env secret resolution, ancestor git detection, Justfile/Taskfile
discovery, plan task/wave extraction, cross-process secret redaction, linter
schema + template headings, handoff manifest semantics.

@verifies REQ-DEV-01
@verifies REQ-HAND-01
@verifies REQ-HAND-02
@verifies REQ-DISC-01
@verifies REQ-WORK-02
@verifies REQ-ENV-04
"""

import json
import os
import subprocess
import sys
import tempfile
import shutil
import unittest
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent.parent / "tools"
sys.path.insert(0, str(TOOLS_DIR))

import audit_logger
import dev_discovery
import env_manager
import exe_runner


_MODULE_REG_DIR = None
_MODULE_REG_OLD = None


def setUpModule():
    """Isolate the persistent secret registry for this test module."""
    global _MODULE_REG_DIR, _MODULE_REG_OLD
    import tempfile
    _MODULE_REG_DIR = tempfile.mkdtemp()
    _MODULE_REG_OLD = os.environ.get(audit_logger.REDACT_REGISTRY_ENV_VAR)
    os.environ[audit_logger.REDACT_REGISTRY_ENV_VAR] = str(
        Path(_MODULE_REG_DIR) / "registry.json"
    )
    audit_logger._SECRET_REGISTRY.clear()
    audit_logger._registry_mtime = None


def tearDownModule():
    global _MODULE_REG_DIR, _MODULE_REG_OLD
    if _MODULE_REG_OLD is None:
        os.environ.pop(audit_logger.REDACT_REGISTRY_ENV_VAR, None)
    else:
        os.environ[audit_logger.REDACT_REGISTRY_ENV_VAR] = _MODULE_REG_OLD
    audit_logger._SECRET_REGISTRY.clear()
    audit_logger._registry_mtime = None
    if _MODULE_REG_DIR:
        shutil.rmtree(_MODULE_REG_DIR, ignore_errors=True)


class TestSetupEnvResolvesConfig(unittest.TestCase):
    # @verifies REQ-DEV-01
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.ws = Path(self.temp_dir)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_config_secrets_and_vars_applied(self):
        os.environ["EXE_FIXTURE_SECRET"] = "fixture-secret-abc"
        try:
            (self.ws / ".env.example").write_text("PORT=3000\nAPI_KEY=\n", encoding="utf-8")
            cfg = {
                "variables": {"PORT": "8080"},
                "secrets": [{
                    "name": "API_KEY",
                    "provider": "env-var",
                    "reference": "EXE_FIXTURE_SECRET",
                }],
            }
            cfg_path = self.ws / "env.json"
            cfg_path.write_text(json.dumps(cfg), encoding="utf-8")
            ok, _ = exe_runner.run_setup_env(
                config=str(cfg_path),
                template=".env.example",
                output=".env",
                workspace=str(self.ws),
            )
            self.assertTrue(ok)
            content = (self.ws / ".env").read_text(encoding="utf-8")
            self.assertIn("PORT=8080", content)
            self.assertIn("API_KEY=fixture-secret-abc", content)
        finally:
            os.environ.pop("EXE_FIXTURE_SECRET", None)


class TestFindGitRepoRoot(unittest.TestCase):
    # @verifies REQ-HAND-01
    def test_nested_workspace_detected(self):
        start = Path(__file__).resolve().parent.parent / "workspace"
        root = exe_runner.find_git_repo_root(start)
        self.assertIsNotNone(root)
        self.assertTrue((root / ".git").exists())

    def test_non_repo_returns_none(self):
        with tempfile.TemporaryDirectory() as td:
            self.assertIsNone(exe_runner.find_git_repo_root(Path(td)))

    def test_commit_rejects_non_repo(self):
        with tempfile.TemporaryDirectory() as td:
            ok, msg = exe_runner.execute_commit(task_id="TASK-01", message="x", cwd=Path(td))
            self.assertFalse(ok)
            self.assertIn("not inside a git repository", msg)

    def test_commit_rejects_missing_workspace(self):
        # @verifies REQ-HAND-01
        with tempfile.TemporaryDirectory() as td:
            missing = Path(td) / "does-not-exist"
            ok, msg = exe_runner.execute_commit(task_id="TASK-01", message="x", cwd=missing)
            self.assertFalse(ok)
            self.assertIn("does not exist", msg)

    def test_commit_rejects_file_workspace(self):
        # @verifies REQ-HAND-01
        with tempfile.TemporaryDirectory() as td:
            f = Path(td) / "file.txt"
            f.write_text("x", encoding="utf-8")
            ok, msg = exe_runner.execute_commit(task_id="TASK-01", message="x", cwd=f)
            self.assertFalse(ok)
            self.assertIn("not a directory", msg)


class TestTaskRunnerDiscovery(unittest.TestCase):
    # @verifies REQ-DISC-01
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.src = Path(self.temp_dir)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_lowercase_justfile_detected(self):
        (self.src / "justfile").write_text("dev:\n  npm run dev\n", encoding="utf-8")
        res = dev_discovery.discover_scripts_and_taskrunners(self.src)
        self.assertIn("just dev", res["recommended_dev_commands"])

    def test_capital_justfile_detected(self):
        (self.src / "Justfile").write_text("dev:\n  npm run dev\n", encoding="utf-8")
        res = dev_discovery.discover_scripts_and_taskrunners(self.src)
        self.assertIn("just dev", res["recommended_dev_commands"])

    def test_taskfile_detected(self):
        (self.src / "Taskfile.yml").write_text(
            "version: '3'\ntasks:\n  dev:\n    cmds:\n      - npm run dev\n",
            encoding="utf-8",
        )
        res = dev_discovery.discover_scripts_and_taskrunners(self.src)
        self.assertIn("task", res["task_targets"])
        self.assertIn("dev", res["task_targets"]["task"])
        self.assertIn("task dev", res["recommended_dev_commands"])


class TestIntakeTaskWaves(unittest.TestCase):
    # @verifies REQ-DEV-01
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.ws = Path(self.temp_dir)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_parses_tasks_waves_branch_sha(self):
        plan = self.ws / "plan.md"
        plan.write_text(
            "# Plan\n"
            "| **Target Branch** | `feature/demo` |\n"
            "| **Git Commit SHA** | `abc123` |\n"
            "### [TASK-01] First\n- Wave: 1\n- Dependencies: []\n"
            "### [TASK-02] Second\n- Wave: 2\n- Dependencies: [TASK-01]\n",
            encoding="utf-8",
        )
        res = exe_runner.intake_plan_from_01_plan(plan)
        self.assertEqual(res["target_branch"], "feature/demo")
        self.assertEqual(res["commit_sha"], "abc123")
        self.assertEqual(res["task_count"], 2)
        self.assertEqual(res["waves_count"], 2)
        self.assertEqual(res["waves"], [["TASK-01"], ["TASK-02"]])
        self.assertEqual(res["tasks"][1]["dependencies"], ["TASK-01"])

    def test_intake_preserves_01plan_failure_payload(self):
        # Simulate 01-plan exiting 2 with JSON on stdout + reasons on stderr.
        import subprocess as sp

        real_run = sp.run

        def fake_run(cmd, **kwargs):
            raise sp.CalledProcessError(
                2, cmd,
                output=json.dumps({
                    "status": "PLAN_NOT_READY",
                    "reasons": ["Plan status is 'DRAFT', not 'READY FOR 02-EXE'."],
                }),
                stderr="[!] No READY plan available for 02-exe:\n"
                       "    - Plan status is 'DRAFT', not 'READY FOR 02-EXE'.\n",
            )

        sp.run = fake_run
        try:
            res = exe_runner.intake_plan_from_01_plan(None)
        finally:
            sp.run = real_run
        self.assertEqual(res.get("status"), "PLAN_NOT_READY")
        self.assertIn("Plan status is 'DRAFT'", json.dumps(res))

    def test_intake_reports_stderr_when_no_payload(self):
        import subprocess as sp

        real_run = sp.run

        def fake_run(cmd, **kwargs):
            raise sp.CalledProcessError(2, cmd, output="", stderr="boom-detail")

        sp.run = fake_run
        try:
            res = exe_runner.intake_plan_from_01_plan(None)
        finally:
            sp.run = real_run
        self.assertIn("error", res)
        self.assertIn("boom-detail", res["error"])


class TestCrossProcessRedaction(unittest.TestCase):
    # @verifies REQ-ENV-04
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.reg = Path(self.temp_dir) / "registry.json"
        self.old = os.environ.get(audit_logger.REDACT_REGISTRY_ENV_VAR)
        os.environ[audit_logger.REDACT_REGISTRY_ENV_VAR] = str(self.reg)
        audit_logger._SECRET_REGISTRY.clear()
        audit_logger._registry_mtime = None

    def tearDown(self):
        if self.old is None:
            os.environ.pop(audit_logger.REDACT_REGISTRY_ENV_VAR, None)
        else:
            os.environ[audit_logger.REDACT_REGISTRY_ENV_VAR] = self.old
        audit_logger._SECRET_REGISTRY.clear()
        audit_logger._registry_mtime = None
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_secret_masked_in_fresh_process(self):
        secret = "xproc-secret-token-12345"
        audit_logger.register_secret(secret)
        # Simulate a fresh process: drop in-memory state, keep persisted file.
        audit_logger._SECRET_REGISTRY.clear()
        audit_logger._registry_mtime = None
        masked = audit_logger.redact_text(f"token={secret}")
        self.assertNotIn(secret, masked)
        self.assertIn("***REDACTED***", masked)

    def test_registry_file_permissions(self):
        audit_logger.register_secret("perm-check-secret-xyz")
        mode = oct(self.reg.stat().st_mode & 0o777)
        self.assertEqual(mode, "0o600")


class TestLinterSchema(unittest.TestCase):
    # @verifies REQ-WORK-02
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.ws = Path(self.temp_dir)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_recommended_fields_are_warnings_not_errors(self):
        wf = self.ws / "wf.md"
        wf.write_text(
            "---\nid: WF-001\nname: t\ntarget: r\n---\n"
            "trap 'x' EXIT INT TERM\n### Step 1: Run\n",
            encoding="utf-8",
        )
        ok, errs, warns = exe_runner.lint_workflow_runbook(wf)
        self.assertTrue(ok)
        self.assertEqual(errs, [])
        self.assertTrue(any("prerequisites" in w for w in warns))

    def test_missing_required_field_fails(self):
        wf = self.ws / "wf.md"
        wf.write_text("---\nid: WF-001\nname: t\n---\n### Step 1: Run\n", encoding="utf-8")
        ok, errs, _ = exe_runner.lint_workflow_runbook(wf)
        self.assertFalse(ok)
        self.assertTrue(any("target:" in e for e in errs))

    def test_bundled_template_lints_clean(self):
        tpl = Path(__file__).resolve().parent.parent / "templates" / "WORKFLOW_TEMPLATE.md"
        ok, errs, _ = exe_runner.lint_workflow_runbook(tpl)
        self.assertTrue(ok, f"template errors: {errs}")


class TestHandoffSemantics(unittest.TestCase):
    # @verifies REQ-HAND-02
    def test_empty_audit_is_not_verified(self):
        with tempfile.TemporaryDirectory() as td:
            os.environ["EXE_AUDIT_LOG"] = str(Path(td) / "audit.jsonl")
            audit_logger._SECRET_REGISTRY.clear()
            try:
                m = exe_runner.generate_qa_handoff(branch="b", commit_sha="sha")
                self.assertEqual(m["status"], "NOT_VERIFIED")
                self.assertIn("touched_files", m)
                self.assertIn("03-qa/tools/qa_runner.py", m["qa_instructions"])
            finally:
                os.environ.pop("EXE_AUDIT_LOG", None)

    def test_pass_audit_is_ready(self):
        with tempfile.TemporaryDirectory() as td:
            os.environ["EXE_AUDIT_LOG"] = str(Path(td) / "audit.jsonl")
            try:
                audit_logger.record_step(
                    tool="t", step_id="s1", input_data={}, output_data={},
                    assertions={}, duration_ms=1.0, status="PASS",
                )
                m = exe_runner.generate_qa_handoff(branch="b", commit_sha="sha")
                self.assertEqual(m["status"], "READY_FOR_QA")
            finally:
                os.environ.pop("EXE_AUDIT_LOG", None)

    def test_fail_audit_is_failures_present(self):
        with tempfile.TemporaryDirectory() as td:
            os.environ["EXE_AUDIT_LOG"] = str(Path(td) / "audit.jsonl")
            try:
                audit_logger.record_step(
                    tool="t", step_id="s1", input_data={}, output_data={},
                    assertions={}, duration_ms=1.0, status="FAIL",
                )
                m = exe_runner.generate_qa_handoff(branch="b", commit_sha="sha")
                self.assertEqual(m["status"], "FAILURES_PRESENT")
            finally:
                os.environ.pop("EXE_AUDIT_LOG", None)

    def test_non_pass_records_are_not_ready(self):
        # Records exist but none PASSed (e.g. SKIPPED-only): must not promote.
        with tempfile.TemporaryDirectory() as td:
            os.environ["EXE_AUDIT_LOG"] = str(Path(td) / "audit.jsonl")
            try:
                audit_logger.record_step(
                    tool="t", step_id="s1", input_data={}, output_data={},
                    assertions={}, duration_ms=1.0, status="SKIPPED",
                )
                m = exe_runner.generate_qa_handoff(branch="b", commit_sha="sha")
                self.assertEqual(m["status"], "NOT_VERIFIED")
            finally:
                os.environ.pop("EXE_AUDIT_LOG", None)

    def test_handoff_lists_latest_commit_files_when_tree_clean(self):
        # Per SOP, handoff runs post-commit when `git status` is empty;
        # touched_files must then fall back to the commit's file list.
        import subprocess as sp

        with tempfile.TemporaryDirectory() as td:
            repo = Path(td) / "repo"
            repo.mkdir()
            sp.run(["git", "init", "-q"], cwd=repo, check=True)
            sp.run(["git", "config", "user.email", "t@t.t"], cwd=repo, check=True)
            sp.run(["git", "config", "user.name", "t"], cwd=repo, check=True)
            (repo / "seed.txt").write_text("seed", encoding="utf-8")
            sp.run(["git", "add", "-A"], cwd=repo, check=True)
            sp.run(["git", "commit", "-qm", "seed"], cwd=repo, check=True)
            (repo / "touched.txt").write_text("x", encoding="utf-8")
            sp.run(["git", "add", "-A"], cwd=repo, check=True)
            sp.run(["git", "commit", "-qm", "init"], cwd=repo, check=True)
            sha = sp.run(
                ["git", "rev-parse", "HEAD"], cwd=repo,
                capture_output=True, text=True, check=True,
            ).stdout.strip()
            with tempfile.TemporaryDirectory() as ad:
                os.environ["EXE_AUDIT_LOG"] = str(Path(ad) / "audit.jsonl")
                try:
                    audit_logger.record_step(
                        tool="t", step_id="s1", input_data={}, output_data={},
                        assertions={}, duration_ms=1.0, status="PASS",
                    )
                    m = exe_runner.generate_qa_handoff(
                        branch="main", commit_sha=sha, cwd=repo,
                    )
                    self.assertEqual(m["status"], "READY_FOR_QA")
                    self.assertIn("touched.txt", m["touched_files"])
                finally:
                    os.environ.pop("EXE_AUDIT_LOG", None)


class TestEnvManagerHardening(unittest.TestCase):
    def test_gitignore_remediation_reported(self):
        with tempfile.TemporaryDirectory() as td:
            ws = Path(td)
            tpl = ws / ".env.example"
            tpl.write_text("A=1\n", encoding="utf-8")
            out = ws / ".env"
            ok, msg = env_manager.synthesize_env_file(
                template_path=tpl, output_path=out,
                resolved_secrets={"A": "2"}, workspace_dir=ws,
            )
            self.assertTrue(ok)
            self.assertIn("WARNING", msg)
            self.assertTrue((ws / ".gitignore").exists())

    def test_resolve_skips_nameless_entries(self):
        resolved = env_manager.resolve_credentials([{"provider": "env-var"}])
        self.assertEqual(resolved, {})


class TestReadinessHelpers(unittest.TestCase):
    # @verifies REQ-DEV-02
    def test_http_poll_detects_server(self):
        import threading
        from http.server import BaseHTTPRequestHandler, HTTPServer

        class H(BaseHTTPRequestHandler):
            def do_GET(self):  # noqa: N802
                self.send_response(200)
                self.end_headers()

            def log_message(self, format, *args):  # noqa: A002 - stdlib signature
                pass

        srv = HTTPServer(("127.0.0.1", 0), H)
        port = srv.server_address[1]
        t = threading.Thread(target=srv.serve_forever, daemon=True)
        t.start()
        try:
            import process_manager
            self.assertFalse(process_manager.is_port_open("127.0.0.1", 1))
            self.assertTrue(
                process_manager.poll_http_url(
                    f"http://127.0.0.1:{port}/", timeout_seconds=5.0, interval=0.2
                )
            )
        finally:
            srv.shutdown()
            srv.server_close()

    def test_stop_without_pid_file(self):
        import process_manager
        self.assertFalse(process_manager.stop_process("no-such-proc-xyz"))


if __name__ == "__main__":
    unittest.main()
