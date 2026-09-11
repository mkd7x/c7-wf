#!/usr/bin/env python3
"""
Unit tests for context_discovery.py
@verifies REQ-DISC-01
@verifies REQ-DISC-02
@verifies REQ-DISC-03
@verifies REQ-DISC-04
"""

import unittest
import tempfile
import json
import sys
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent.parent / "tools"
sys.path.insert(0, str(TOOLS_DIR))
import context_discovery


class TestContextDiscovery(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    # @verifies REQ-DISC-01
    def test_detect_python_manifests(self):
        (self.root / "pyproject.toml").write_text("[project]\ndependencies = ['fastapi', 'pytest']", encoding="utf-8")
        manifest_info = context_discovery.detect_manifests(self.root)
        self.assertEqual(manifest_info["language"], "python")
        self.assertIn("fastapi", manifest_info["frameworks"])
        self.assertIn("pytest", manifest_info["frameworks"])

    # @verifies REQ-DISC-02
    def test_detect_clean_arch_layers_and_adrs(self):
        (self.root / "domain").mkdir()
        (self.root / "infrastructure").mkdir()
        (self.root / "docs" / "adr").mkdir(parents=True)
        (self.root / "docs" / "adr" / "0001-init.md").write_text("# ADR 1", encoding="utf-8")

        boundary_info = context_discovery.detect_boundaries_and_adrs(self.root)
        self.assertIn("domain", boundary_info["architecture_layers"])
        self.assertIn("infrastructure", boundary_info["architecture_layers"])
        self.assertEqual(len(boundary_info["existing_adrs"]), 1)

    # @verifies REQ-DISC-03
    def test_detect_routes_and_schemas(self):
        (self.root / "api.py").write_text("@app.get('/health')\ndef health(): pass", encoding="utf-8")
        (self.root / "migration.sql").write_text("CREATE TABLE users (id INT);", encoding="utf-8")

        route_info = context_discovery.detect_routes_and_schemas(self.root)
        self.assertTrue(any("api.py" in r["file"] for r in route_info["detected_route_files"]))
        self.assertIn("migration.sql", route_info["detected_schema_files"])

    # @verifies REQ-DISC-02
    def test_excluded_dirs_not_scanned(self):
        (self.root / "node_modules" / "domain").mkdir(parents=True)
        (self.root / "real").mkdir()
        boundary_info = context_discovery.detect_boundaries_and_adrs(self.root)
        self.assertNotIn("node_modules/domain", boundary_info["architecture_layers"])

    # @verifies REQ-DISC-03
    def test_oversized_files_skipped_in_route_scan(self):
        big = self.root / "big.py"
        big.write_text("@app.get('/x')\n" + "x" * (context_discovery.MAX_SCAN_FILE_BYTES + 1),
                       encoding="utf-8")
        route_info = context_discovery.detect_routes_and_schemas(self.root)
        self.assertFalse(any("big.py" in r["file"] for r in route_info["detected_route_files"]))

    # @verifies REQ-DISC-04
    def test_context_snapshotting(self):
        (self.root / "pyproject.toml").write_text("dependencies = ['flask']", encoding="utf-8")
        snap_file = self.root / "snapshot.json"
        res = context_discovery.discover_codebase(self.root, output_file=snap_file)
        self.assertTrue(snap_file.exists())
        saved = json.loads(snap_file.read_text(encoding="utf-8"))
        self.assertEqual(saved["language"], "python")


if __name__ == "__main__":
    unittest.main()
