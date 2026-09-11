import sys
import unittest
from datetime import date
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path.home() / ".hermes" / "scripts"))

from google_calendar_brief_context import find_schedule_issues, normalize_event


TZ = ZoneInfo("America/Mexico_City")


class CalendarNormalizationTests(unittest.TestCase):
    def test_normalizes_timed_and_all_day_events(self):
        timed = normalize_event(
            {
                "summary": "Dentista",
                "start": {"dateTime": "2026-09-05T10:00:00-06:00"},
                "end": {"dateTime": "2026-09-05T11:00:00-06:00"},
                "location": "Zapopan",
                "status": "confirmed",
            },
            "Personal",
            TZ,
        )
        all_day = normalize_event(
            {
                "summary": "Cumpleaños",
                "start": {"date": "2026-09-05"},
                "end": {"date": "2026-09-06"},
                "status": "confirmed",
            },
            "Personal",
            TZ,
        )

        self.assertEqual(timed["start"], "2026-09-05T10:00:00-06:00")
        self.assertEqual(timed["location"], "Zapopan")
        self.assertFalse(timed["all_day"])
        self.assertEqual(all_day["start"], "2026-09-05")
        self.assertEqual(all_day["end"], "2026-09-06")
        self.assertTrue(all_day["all_day"])

    def test_filters_cancelled_and_self_declined_events(self):
        cancelled = normalize_event(
            {"summary": "Cancelada", "status": "cancelled", "start": {"date": "2026-09-05"}, "end": {"date": "2026-09-06"}},
            "Personal",
            TZ,
        )
        declined = normalize_event(
            {
                "summary": "Rechazada",
                "status": "confirmed",
                "start": {"dateTime": "2026-09-05T12:00:00-06:00"},
                "end": {"dateTime": "2026-09-05T13:00:00-06:00"},
                "attendees": [{"self": True, "responseStatus": "declined"}],
            },
            "Personal",
            TZ,
        )

        self.assertIsNone(cancelled)
        self.assertIsNone(declined)

    def test_detects_overlap_and_tight_transition(self):
        events = [
            {"summary": "A", "start": "2026-09-05T10:00:00-06:00", "end": "2026-09-05T11:00:00-06:00", "all_day": False, "location": "Centro"},
            {"summary": "B", "start": "2026-09-05T10:30:00-06:00", "end": "2026-09-05T11:30:00-06:00", "all_day": False, "location": "Casa"},
            {"summary": "C", "start": "2026-09-05T11:45:00-06:00", "end": "2026-09-05T12:30:00-06:00", "all_day": False, "location": "Oficina"},
        ]

        issues = find_schedule_issues(events)

        self.assertEqual(issues["conflicts"], [{"first": "A", "second": "B", "overlap_minutes": 30}])
        self.assertEqual(issues["tight_transitions"], [{"first": "B", "second": "C", "gap_minutes": 15, "locations_differ": True}])


if __name__ == "__main__":
    unittest.main()
