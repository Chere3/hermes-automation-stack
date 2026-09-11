#!/usr/bin/env python3
import subprocess
import unittest
from unittest.mock import patch

from career_ops_context import collect_career_ops_brief


class CareerOpsContextTests(unittest.TestCase):
    @patch("career_ops_context.subprocess.run")
    def test_preserves_stdout_verbatim_except_console_newline(self, run):
        block = "## Vacantes montadas\n\n**1. Company — Role** · 4.6/5\n   ⚠ warning"
        run.return_value = subprocess.CompletedProcess([], 0, stdout=block + "\n", stderr="")
        result = collect_career_ops_brief()
        self.assertEqual(result, {"status": "ok", "verbatim": block})
        args, kwargs = run.call_args
        self.assertEqual(args[0], ["node", "brief.mjs", "--quiet"])
        self.assertTrue(kwargs["capture_output"])
        self.assertFalse(kwargs["check"])

    @patch("career_ops_context.subprocess.run")
    def test_empty_stdout_stays_silent(self, run):
        run.return_value = subprocess.CompletedProcess([], 0, stdout="", stderr="")
        self.assertEqual(
            collect_career_ops_brief(),
            {"status": "empty", "verbatim": ""},
        )

    @patch("career_ops_context.subprocess.run")
    def test_failure_does_not_leak_stderr(self, run):
        run.return_value = subprocess.CompletedProcess([], 1, stdout="", stderr="secret detail")
        result = collect_career_ops_brief()
        self.assertEqual(result, {"status": "unavailable", "reason": "nonzero_exit"})
        self.assertNotIn("secret", repr(result))


if __name__ == "__main__":
    unittest.main()
