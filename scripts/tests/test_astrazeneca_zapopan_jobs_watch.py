#!/usr/bin/env python3
"""Isolated pagination tests for the AstraZeneca Eightfold watcher."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

SCRIPT = Path(__file__).parents[1] / "astrazeneca_zapopan_jobs_watch.py"
spec = importlib.util.spec_from_file_location("astrazeneca_watch", SCRIPT)
watch = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules[spec.name] = watch
spec.loader.exec_module(watch)


def position(number: int) -> dict[str, object]:
    return {
        "id": str(number),
        "displayJobId": f"R-{number}",
        "name": f"Job {number}",
        "locations": ["Zapopan, Jalisco, Mexico"],
        "department": "IT Engineering",
        "workLocationOption": "onsite",
        "postedTs": 1_700_000_000,
        "positionUrl": f"/careers/job/{number}",
    }


def response(count: int, positions: list[dict[str, object]]) -> subprocess.CompletedProcess[bytes]:
    payload = {"status": 200, "data": {"count": count, "positions": positions}}
    return subprocess.CompletedProcess([], 0, stdout=json.dumps(payload).encode(), stderr=b"")


def start_from_command(command: list[str]) -> int:
    return int(parse_qs(urlparse(command[-1]).query).get("start", ["0"])[0])


class PaginationTests(unittest.TestCase):
    def test_fetches_all_pages_10_plus_1(self) -> None:
        pages = {0: list(map(position, range(1, 11))), 10: [position(11)]}

        def fake_run(command, **kwargs):
            start = start_from_command(command)
            return response(11, pages[start])

        with patch.object(watch.subprocess, "run", side_effect=fake_run):
            jobs = watch.fetch_jobs()
        self.assertEqual(set(jobs), {str(n) for n in range(1, 12)})

    def test_retries_full_snapshot_when_declared_total_changes(self) -> None:
        calls: list[int] = []

        def fake_run(command, **kwargs):
            start = start_from_command(command)
            calls.append(start)
            if calls == [0]:
                return response(11, list(map(position, range(1, 11))))
            if calls == [0, 10]:
                return response(12, [position(11)])
            if start == 0:
                return response(12, list(map(position, range(1, 11))))
            return response(12, [position(11), position(12)])

        with patch.object(watch.subprocess, "run", side_effect=fake_run), patch.object(watch.time, "sleep"):
            jobs = watch.fetch_jobs()
        self.assertEqual(len(jobs), 12)
        self.assertEqual(calls, [0, 10, 0, 10])

    def test_duplicate_id_across_pages_is_rejected(self) -> None:
        pages = {0: list(map(position, range(1, 11))), 10: [position(10)]}

        def fake_run(command, **kwargs):
            return response(11, pages[start_from_command(command)])

        with patch.object(watch.subprocess, "run", side_effect=fake_run), patch.object(watch.time, "sleep"):
            with self.assertRaisesRegex(RuntimeError, "duplicado"):
                watch.fetch_jobs()

    def test_empty_page_before_declared_total_is_rejected(self) -> None:
        pages = {0: list(map(position, range(1, 11))), 10: []}

        def fake_run(command, **kwargs):
            return response(11, pages[start_from_command(command)])

        with patch.object(watch.subprocess, "run", side_effect=fake_run), patch.object(watch.time, "sleep"):
            with self.assertRaisesRegex(RuntimeError, "vacía"):
                watch.fetch_jobs()

    def test_zero_results_is_a_complete_snapshot(self) -> None:
        with patch.object(watch.subprocess, "run", return_value=response(0, [])):
            self.assertEqual(watch.fetch_jobs(), {})

    def test_invalid_ids_are_rejected(self) -> None:
        for invalid in (None, "", "   ", True, {}, []):
            bad = position(1)
            bad["id"] = invalid
            with self.subTest(invalid=invalid), patch.object(
                watch.subprocess, "run", return_value=response(1, [bad])
            ), patch.object(watch.time, "sleep"):
                with self.assertRaisesRegex(RuntimeError, "id inválido"):
                    watch.fetch_jobs()

    def test_payload_and_data_must_be_objects(self) -> None:
        cases = [
            [],
            {"status": 200, "data": []},
        ]
        for payload in cases:
            completed = subprocess.CompletedProcess([], 0, stdout=json.dumps(payload).encode(), stderr=b"")
            with self.subTest(payload=payload), patch.object(watch.subprocess, "run", return_value=completed):
                with self.assertRaisesRegex(RuntimeError, "esquema JSON inválido"):
                    watch.fetch_jobs()

    def test_curl_has_a_response_size_limit(self) -> None:
        commands: list[list[str]] = []

        def fake_run(command, **kwargs):
            commands.append(command)
            return response(0, [])

        with patch.object(watch.subprocess, "run", side_effect=fake_run):
            watch.fetch_jobs()
        self.assertIn("--max-filesize", commands[0])
        index = commands[0].index("--max-filesize")
        self.assertEqual(commands[0][index + 1], str(watch.MAX_RESPONSE_BYTES))

    def test_post_capture_size_limit_is_enforced(self) -> None:
        completed = subprocess.CompletedProcess([], 0, stdout=b"x" * 17, stderr=b"")
        with patch.object(watch, "MAX_RESPONSE_BYTES", 16), patch.object(
            watch.subprocess, "run", return_value=completed
        ):
            with self.assertRaisesRegex(RuntimeError, "límite de respuesta"):
                watch.fetch_jobs()

    def test_text_id_is_saved_in_normalized_form(self) -> None:
        item = position(1)
        item["id"] = "  1  "
        with patch.object(watch.subprocess, "run", return_value=response(1, [item])):
            jobs = watch.fetch_jobs()
        self.assertEqual(set(jobs), {"1"})
        self.assertEqual(jobs["1"]["id"], "1")

    def test_atomic_save_preserves_baseline_if_replace_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            state_dir = Path(temp)
            baseline = state_dir / "jobs.json"
            history = state_dir / "history.jsonl"
            original = '{"sentinel": true}\n'
            baseline.write_text(original, encoding="utf-8")
            with patch.object(watch, "STATE_DIR", state_dir), patch.object(
                watch, "BASELINE", baseline
            ), patch.object(watch, "HISTORY", history), patch.object(
                watch.os, "replace", side_effect=OSError("simulated replace failure")
            ):
                with self.assertRaises(OSError):
                    watch.save_snapshot({"1": {"id": "1"}})
            self.assertEqual(baseline.read_text(encoding="utf-8"), original)
            self.assertEqual(list(state_dir.glob(".jobs.json.*.tmp")), [])

    def test_failed_fetch_does_not_touch_baseline_or_history(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            state_dir = Path(temp)
            baseline = state_dir / "jobs.json"
            history = state_dir / "history.jsonl"
            original_baseline = '{"jobs": {"old": {"id": "old"}}}\n'
            original_history = '{"old": true}\n'
            baseline.write_text(original_baseline, encoding="utf-8")
            history.write_text(original_history, encoding="utf-8")
            with patch.object(watch, "STATE_DIR", state_dir), patch.object(
                watch, "BASELINE", baseline
            ), patch.object(watch, "HISTORY", history), patch.object(
                watch, "fetch_jobs", side_effect=RuntimeError("incomplete")
            ), patch.object(sys, "argv", [str(SCRIPT)]):
                with self.assertRaisesRegex(RuntimeError, "incomplete"):
                    watch.main()
            self.assertEqual(baseline.read_text(encoding="utf-8"), original_baseline)
            self.assertEqual(history.read_text(encoding="utf-8"), original_history)


if __name__ == "__main__":
    unittest.main(verbosity=2)
