#!/usr/bin/env python3
"""Read-only Google Calendar context for Alexa briefs."""

from __future__ import annotations

import argparse
import json
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

TZ = ZoneInfo("America/Mexico_City")
TOKEN_PATH = Path.home() / ".hermes" / "google_token.json"


def _parse_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _self_response_status(event: dict) -> str | None:
    for attendee in event.get("attendees", []):
        if attendee.get("self"):
            return attendee.get("responseStatus")
    return None


def normalize_event(event: dict, calendar_name: str, tz: ZoneInfo = TZ) -> dict | None:
    """Return a bounded, speech-safe event record or exclude non-commitments."""
    if event.get("status") == "cancelled" or _self_response_status(event) == "declined":
        return None

    start_value = event.get("start", {})
    end_value = event.get("end", {})
    all_day = "date" in start_value
    if all_day:
        start = start_value.get("date")
        end = end_value.get("date")
    else:
        if not start_value.get("dateTime") or not end_value.get("dateTime"):
            return None
        start = _parse_datetime(start_value["dateTime"]).astimezone(tz).isoformat(timespec="seconds")
        end = _parse_datetime(end_value["dateTime"]).astimezone(tz).isoformat(timespec="seconds")

    if not start or not end:
        return None

    summary = str(event.get("summary") or "Sin título").strip()[:180]
    location = str(event.get("location") or "").strip()[:180] or None
    return {
        "summary": summary,
        "start": start,
        "end": end,
        "all_day": all_day,
        "location": location,
        "calendar": calendar_name,
        "status": event.get("status", "confirmed"),
        "response_status": _self_response_status(event),
    }


def find_schedule_issues(events: list[dict]) -> dict:
    """Detect timed overlaps and sub-30-minute consecutive transitions."""
    timed = sorted(
        (event for event in events if not event.get("all_day")),
        key=lambda event: _parse_datetime(event["start"]),
    )
    conflicts: list[dict] = []
    for index, first in enumerate(timed):
        first_end = _parse_datetime(first["end"])
        for second in timed[index + 1 :]:
            second_start = _parse_datetime(second["start"])
            if second_start >= first_end:
                break
            overlap = min(first_end, _parse_datetime(second["end"])) - second_start
            conflicts.append(
                {
                    "first": first["summary"],
                    "second": second["summary"],
                    "overlap_minutes": int(overlap.total_seconds() // 60),
                }
            )

    tight_transitions: list[dict] = []
    for first, second in zip(timed, timed[1:]):
        gap = _parse_datetime(second["start"]) - _parse_datetime(first["end"])
        gap_minutes = int(gap.total_seconds() // 60)
        if 0 <= gap_minutes < 30:
            first_location = first.get("location")
            second_location = second.get("location")
            tight_transitions.append(
                {
                    "first": first["summary"],
                    "second": second["summary"],
                    "gap_minutes": gap_minutes,
                    "locations_differ": bool(
                        first_location
                        and second_location
                        and first_location.casefold() != second_location.casefold()
                    ),
                }
            )

    return {"conflicts": conflicts, "tight_transitions": tight_transitions}


def _calendar_name(calendar: dict) -> str:
    override = str(calendar.get("summaryOverride") or "").strip()
    summary = override or str(calendar.get("summary") or "").strip()
    if calendar.get("primary"):
        return "Principal"
    if "@" in summary:
        return "Calendario compartido"
    return summary[:100] or "Calendario"


def _load_credentials():
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials

    credentials = Credentials.from_authorized_user_file(str(TOKEN_PATH))
    if credentials.expired and credentials.refresh_token:
        credentials.refresh(Request())
        TOKEN_PATH.write_text(credentials.to_json(), encoding="utf-8")
        TOKEN_PATH.chmod(0o600)
    if not credentials.valid:
        raise RuntimeError("Google Calendar credentials are invalid")
    return credentials


def collect_calendar_context(day: str | date, days: int = 1) -> dict:
    """Fetch every visible calendar for a half-open local date window."""
    local_day = date.fromisoformat(day) if isinstance(day, str) else day
    start_local = datetime.combine(local_day, time.min, TZ)
    end_local = start_local + timedelta(days=days)
    generated_at = datetime.now(TZ).isoformat(timespec="seconds")

    try:
        from googleapiclient.discovery import build

        service = build("calendar", "v3", credentials=_load_credentials(), cache_discovery=False)
        calendars: list[dict] = []
        page_token = None
        while True:
            response = service.calendarList().list(pageToken=page_token).execute()
            calendars.extend(response.get("items", []))
            page_token = response.get("nextPageToken")
            if not page_token:
                break

        events: list[dict] = []
        for calendar in calendars:
            event_page_token = None
            while True:
                response = service.events().list(
                    calendarId=calendar["id"],
                    timeMin=start_local.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
                    timeMax=end_local.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
                    singleEvents=True,
                    orderBy="startTime",
                    showDeleted=False,
                    pageToken=event_page_token,
                ).execute()
                for raw_event in response.get("items", []):
                    event = normalize_event(raw_event, _calendar_name(calendar), TZ)
                    if event is not None:
                        events.append(event)
                event_page_token = response.get("nextPageToken")
                if not event_page_token:
                    break

        events.sort(key=lambda event: (not event["all_day"], event["start"], event["summary"].casefold()))
        return {
            "status": "available",
            "generated_at": generated_at,
            "timezone": str(TZ),
            "window_start": start_local.isoformat(timespec="seconds"),
            "window_end_exclusive": end_local.isoformat(timespec="seconds"),
            "calendar_count": len(calendars),
            "event_count": len(events),
            "all_day_count": sum(event["all_day"] for event in events),
            "events": events,
            "schedule_issues": find_schedule_issues(events),
        }
    except Exception as error:
        return {
            "status": "unavailable",
            "generated_at": generated_at,
            "timezone": str(TZ),
            "window_start": start_local.isoformat(timespec="seconds"),
            "window_end_exclusive": end_local.isoformat(timespec="seconds"),
            "reason": type(error).__name__,
        }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", default=datetime.now(TZ).date().isoformat())
    parser.add_argument("--days", type=int, default=1)
    args = parser.parse_args()
    if args.days < 1 or args.days > 7:
        parser.error("--days must be between 1 and 7")
    print(json.dumps(collect_calendar_context(args.date, args.days), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
