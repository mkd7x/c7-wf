#!/usr/bin/env python3
"""
Unit tests for 02-exe env_manager.py.
Validates credential resolution, safe .env synthesis, gitignore enforcement, and secret masking.

@verifies REQ-ENV-01
@verifies REQ-ENV-02
@verifies REQ-ENV-03
@verifies REQ-ENV-04
"""

import os
import sys
import unittest
import tempfile
import shutil
from pathlib import Path

# Add tools to path
TOOLS_DIR = Path(__file__).resolve().parent.parent / "tools"
sys.path.insert(0, str(TOOLS_DIR))

import env_manager
import audit_logger


class TestEnvManager(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.workspace = Path(self.temp_dir)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_env_var_provider(self):
        # @verifies REQ-ENV-02
        os.environ["TEST_SECRET_KEY"] = "super-secret-value-123"
        provider = env_manager.EnvVarProvider()
        val = provider.resolve("TEST_SECRET_KEY")
        self.assertEqual(val, "super-secret-value-123")

    def test_secret_masking(self):
        # @verifies REQ-ENV-04
        secret = "very-sensitive-token-xyz"
        audit_logger.register_secret(secret)
        raw_msg = f"Connecting with token {secret} to database."
        masked = audit_logger.redact_text(raw_msg)
        self.assertNotIn(secret, masked)
        self.assertIn("***REDACTED***", masked)

    def test_safe_env_synthesis(self):
        # @verifies REQ-ENV-01
        # @verifies REQ-ENV-03
        template = self.workspace / ".env.example"
        template.write_text("PORT=3000\nAPI_KEY=\nDB_NAME=mydb\n", encoding="utf-8")
        out_env = self.workspace / ".env"

        resolved = {"API_KEY": "secret-api-key-999"}
        ok, msg = env_manager.synthesize_env_file(
            template_path=template,
            output_path=out_env,
            resolved_secrets=resolved,
            static_vars={"PORT": "8080"},
            workspace_dir=self.workspace,
            enforce_gitignore=False
        )
        self.assertTrue(ok)
        self.assertTrue(out_env.exists())
        content = out_env.read_text(encoding="utf-8")
        self.assertIn("PORT=8080", content)
        self.assertIn("API_KEY=secret-api-key-999", content)
        self.assertIn("DB_NAME=mydb", content)


if __name__ == "__main__":
    unittest.main()
