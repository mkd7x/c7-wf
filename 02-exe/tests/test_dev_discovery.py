#!/usr/bin/env python3
"""
Unit tests for 02-exe dev_discovery.py.
Validates detection of runtimes, dev server scripts, fast testing/linting commands, and templates.

@verifies REQ-DISC-01
@verifies REQ-DISC-02
@verifies REQ-DISC-03
@verifies REQ-DISC-04
"""

import sys
import json
import unittest
import tempfile
import shutil
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent.parent / "tools"
sys.path.insert(0, str(TOOLS_DIR))

import dev_discovery


class TestDevDiscovery(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.source_dir = Path(self.temp_dir)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_node_discovery(self):
        # @verifies REQ-DISC-01
        # @verifies REQ-DISC-02
        pkg = {
            "name": "my-app",
            "scripts": {
                "dev": "vite",
                "build": "vite build",
                "lint": "eslint .",
                "test": "vitest"
            }
        }
        (self.source_dir / "package.json").write_text(json.dumps(pkg), encoding="utf-8")
        (self.source_dir / "pnpm-lock.yaml").write_text("", encoding="utf-8")

        res = dev_discovery.run_discovery(self.source_dir)
        self.assertEqual(res["runtime"]["runtime"], "Node.js")
        self.assertEqual(res["runtime"]["package_manager"], "pnpm")
        self.assertIn("npm run dev", res["scripts"]["recommended_dev_commands"])

    def test_fast_test_and_lint_discovery(self):
        # @verifies REQ-DISC-03
        (self.source_dir / "pyproject.toml").write_text("[tool.poetry]\nname = 'test'\n", encoding="utf-8")
        res = dev_discovery.run_discovery(self.source_dir)
        self.assertEqual(res["runtime"]["runtime"], "Python")
        self.assertIn("ruff check .", res["fast_verification"]["linters"])
        self.assertIn("mypy .", res["fast_verification"]["typecheckers"])

    def test_env_and_compose_discovery(self):
        # @verifies REQ-DISC-04
        (self.source_dir / ".env.example").write_text("API_KEY=test\n", encoding="utf-8")
        (self.source_dir / "docker-compose.yml").write_text("version: '3'\n", encoding="utf-8")
        res = dev_discovery.run_discovery(self.source_dir)
        self.assertIn(".env.example", res["environment"]["env_templates"])
        self.assertIn("docker-compose.yml", res["environment"]["compose_files"])
        self.assertTrue(res["environment"]["has_docker"])


if __name__ == "__main__":
    unittest.main()
