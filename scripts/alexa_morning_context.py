#!/usr/bin/env python3
"""Collect source-grounded context for a morning Alexa executive brief."""

from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

from whisper_money_finance_context import collect_finance_context
from proton_mail_brief_context import collect_mail_context
from google_calendar_brief_context import collect_calendar_context

TZ = ZoneInfo("America/Mexico_City")
NOW = datetime.now(TZ)
REPORT_DATE = (NOW.date() - timedelta(days=1)).isoformat()
HOME = Path.home()
HEALTH_PROJECT = HOME / "proyectos" / "google-health-kpis"


def read_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}


def history_for_date(path: Path, day: str) -> list[dict]:
    events: list[dict] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (FileNotFoundError, OSError):
        return events
    for line in lines:
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if str(event.get("detected_at", "")).startswith(day):
            events.append(event)
    return events


def linkedin_source_context(day: str) -> str:
    """Read durable LinkedIn project sources, never a Claude session or cron output."""
    try:
        from linkedin_daily_context import collect_context

        return collect_context(day)
    except Exception as exc:
        return f"[LinkedIn durable source unavailable: {type(exc).__name__}]"


def health_context(day: str) -> dict:
    try:
        sys.path.insert(0, str(HEALTH_PROJECT))
        from brief_context import collect_health_context

        return collect_health_context(day)
    except Exception as exc:
        return {"status": "unavailable", "reason": type(exc).__name__}


def fetch_weather() -> dict:
    params = {
        "latitude": "20.7211203",
        "longitude": "-103.3913671",
        "current": "temperature_2m,apparent_temperature,weather_code,wind_speed_10m",
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max,weather_code,sunrise,sunset",
        "timezone": "America/Mexico_City",
        "forecast_days": "1",
    }
    url = "https://api.open-meteo.com/v1/forecast?" + urlencode(params)
    with urlopen(Request(url, headers={"User-Agent": "Hermes-Alexa-Brief/1.0"}), timeout=30) as response:
        payload = json.loads(response.read())
    current = payload.get("current", {})
    daily = payload.get("daily", {})
    first = lambda key: (daily.get(key) or [None])[0]
    return {
        "location": "Zapopan, Jalisco",
        "observed_at": current.get("time"),
        "temperature_c": current.get("temperature_2m"),
        "feels_like_c": current.get("apparent_temperature"),
        "weather_code": current.get("weather_code"),
        "wind_kmh": current.get("wind_speed_10m"),
        "max_c": first("temperature_2m_max"),
        "min_c": first("temperature_2m_min"),
        "rain_probability_pct": first("precipitation_probability_max"),
        "daily_weather_code": first("weather_code"),
        "sunrise": first("sunrise"),
        "sunset": first("sunset"),
        "source": "Open-Meteo",
    }



context = {
    "generated_at": NOW.isoformat(timespec="seconds"),
    "timezone": "America/Mexico_City",
    "operations_report_date": REPORT_DATE,
    "weather_now_and_today": weather,
    "calendar_today": collect_calendar_context(NOW.date()),
    "linkedin_previous_day_source_context": linkedin_source_context(REPORT_DATE),
    "health_previous_day": health_context(REPORT_DATE),
    "financial_kpis_month_to_date": collect_finance_context(),
    "email_topics_previous_day": collect_mail_context(REPORT_DATE),
    "speech_constraints": {
        "opening_exact": f"Buenos días, {os.getenv('BRIEF_USER_NAME', 'usuario')}.",
        "target_device_exact": os.getenv("ALEXA_TARGET_DEVICE", "MY ECHO"),
        "language": "es-MX",
        "target_duration_seconds": "60-90",
        "maximum_characters": 1400,
    },
}
print("ALEXA MORNING EXECUTIVE BRIEF SOURCE CONTEXT")
print(json.dumps(context, ensure_ascii=False, indent=2))
