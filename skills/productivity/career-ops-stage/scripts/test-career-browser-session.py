#!/usr/bin/env python3
import os
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).with_name("career-browser-session.sh")


class CareerBrowserSessionTests(unittest.TestCase):
    def run_script(self, command: str, home: str):
        env = os.environ.copy()
        env["HOME"] = home
        return subprocess.run(
            [str(SCRIPT), command],
            env=env,
            text=True,
            capture_output=True,
            check=True,
        )

    def test_launcher_exists_and_is_executable(self):
        self.assertTrue(SCRIPT.is_file())
        self.assertTrue(os.access(SCRIPT, os.X_OK))

    def test_profile_is_persistent_private_and_not_under_cache(self):
        with tempfile.TemporaryDirectory() as home:
            result = self.run_script("prepare", home)
            expected = Path(home) / ".local/share/hermes/career-ops/chrome-profile"
            self.assertEqual(result.stdout.strip(), str(expected))
            self.assertTrue(expected.is_dir())
            self.assertEqual(stat.S_IMODE(expected.stat().st_mode), 0o700)
            self.assertNotIn("/.cache/", result.stdout)

    def test_launcher_is_loopback_only_and_contains_no_evasion_or_submit_fallbacks(self):
        text = SCRIPT.read_text()
        self.assertIn("--remote-debugging-address=127.0.0.1", text)
        self.assertIn("--remote-debugging-port=9333", text)
        self.assertIn("--user-data-dir=$PROFILE_DIR", text)
        for forbidden in (
            "rm -rf",
            "dom_event",
            "playwright",
            "ApiSubmitSingleApplicationFormAction",
            "--headless",
            "--disable-blink-features",
            "--no-sandbox",
        ):
            self.assertNotIn(forbidden, text)

    def test_launch_execs_chrome_in_foreground_for_process_tracking(self):
        text = SCRIPT.read_text()
        self.assertIn('exec env -u WAYLAND_DISPLAY "$CHROME_BIN"', text)
        self.assertNotIn("nohup", text)
        self.assertNotIn("disown", text)


if __name__ == "__main__":
    unittest.main()
