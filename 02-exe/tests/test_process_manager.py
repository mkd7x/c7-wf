#!/usr/bin/env python3
"""
Unit tests for 02-exe process_manager.py.
Validates background process supervision, readiness polling, and cleanup trap generation.

@verifies REQ-WORK-03
@verifies REQ-DEV-02
"""

import sys
import unittest
import time
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent.parent / "tools"
sys.path.insert(0, str(TOOLS_DIR))

import process_manager


class TestProcessManager(unittest.TestCase):
    def test_trap_generation(self):
        # @verifies REQ-WORK-03
        trap_cmd = process_manager.generate_shell_trap(process_names=["api-server", "worker"])
        self.assertIn("trap '", trap_cmd)
        self.assertIn("EXIT INT TERM", trap_cmd)
        self.assertIn("api-server", trap_cmd)
        self.assertIn("worker", trap_cmd)

    def test_background_start_and_stop(self):
        # @verifies REQ-DEV-02
        res = process_manager.start_background_process(
            cmd="python3 -c 'import time; time.sleep(10)'",
            name="test-sleep-proc"
        )
        self.assertIn("pid", res)
        self.assertEqual(res["name"], "test-sleep-proc")

        stopped = process_manager.stop_process("test-sleep-proc")
        self.assertTrue(stopped)


if __name__ == "__main__":
    unittest.main()
