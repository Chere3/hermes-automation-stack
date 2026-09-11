#!/usr/bin/env python3
"""Collect date-scoped evidence for an Alexa executive recap."""
from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
import sys
from datetime import datetime, time, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from whisper_money_finance_context import collect_finance_context
from proton_mail_brief_context import collect_mail_context
from google_calendar_brief_context import collect_calendar_context

TZ = ZoneInfo("America/Mexico_City")
HOME = Path.home()
HERMES_DB = HOME / ".hermes" / "state.db"
HERMES_HOME = HOME / ".hermes"
MAX_HERMES_CHARS = 26000
HEALTH_PROJECT = HOME / "proyectos" / "google-health-kpis"


def read_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def jsonl_for_day(path: Path, day: str, field: str = "detected_at") -> list[dict]:
    rows: list[dict] = []
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return rows
    for line in lines:
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(item, dict) and str(item.get(field, "")).startswith(day):
            rows.append(item)
    return rows


def clean_message(text: str, limit: int = 1200) -> str:
    text = re.sub(r"\[PRIOR CONTEXT.*?END OF CONTEXT SUMMARY.*?---", "", text, flags=re.S)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    return text if len(text) <= limit else text[:limit].rstrip() + "…"


def hermes_day_context(day: str) -> str:
    if not HERMES_DB.exists():
        return "[Hermes session database unavailable]"
    local_date = datetime.strptime(day, "%Y-%m-%d").date()
    start = datetime.combine(local_date, time.min, TZ).astimezone(timezone.utc).timestamp()
    end = datetime.combine(local_date, time.max, TZ).astimezone(timezone.utc).timestamp()
    connection = sqlite3.connect(f"file:{HERMES_DB}?mode=ro", uri=True)
    try:
        rows = connection.execute(
            """
            SELECT m.session_id, s.source, COALESCE(s.title, ''), m.role, m.content, m.timestamp
            FROM messages m
            JOIN sessions s ON s.id = m.session_id
            WHERE m.timestamp BETWEEN ? AND ?
              AND m.role IN ('user', 'assistant')
              AND m.content IS NOT NULL
              AND trim(m.content) != ''
              AND s.parent_session_id IS NULL
            ORDER BY m.timestamp, m.id
            """,
            (start, end),
        ).fetchall()
    finally:
        connection.close()
    if not rows:
        return "[No Hermes messages found for date]"

    session_numbers: dict[str, int] = {}
    output: list[str] = []
    total = 0
    truncated = False
    for session_id, source, title, role, content, stamp in rows:
        if session_id not in session_numbers:
            session_numbers[session_id] = len(session_numbers) + 1
            heading = f"\n--- Hermes session {session_numbers[session_id]} · {source} · {title or 'sin título'} ---"
            output.append(heading)
            total += len(heading)
        text = clean_message(str(content))
        if not text:
            continue
        local = datetime.fromtimestamp(float(stamp), timezone.utc).astimezone(TZ)
        label = os.getenv("BRIEF_USER_NAME", "User") if role == "user" else "Hermes"
        line = f"[{local.strftime('%H:%M')} {label}] {text}"
        if total + len(line) + 1 > MAX_HERMES_CHARS:
            truncated = True
            break
        output.append(line)
        total += len(line) + 1
    if truncated:
        output.append("[Hermes excerpts bounded by context limit]")
    return "\n".join(output)


def linkedin_context(day: str) -> str:
    try:
        from linkedin_daily_context import collect_context
        return collect_context(day)
    except Exception as exc:
        return f"[LinkedIn sources unavailable: {type(exc).__name__}]"


def health_context(day: str) -> dict:
    try:
        sys.path.insert(0, str(HEALTH_PROJECT))
        from brief_context import collect_health_context

        return collect_health_context(day)
    except Exception as exc:
        return {"status": "unavailable", "reason": type(exc).__name__}



def cron_health() -> list[dict]:
    payload = read_json(HERMES_HOME / "cron" / "jobs.json")
    jobs = payload.get("jobs", []) if isinstance(payload, dict) else []
    result = []
    for job in jobs:
        if not isinstance(job, dict) or not job.get("enabled", True):
            continue
        result.append({
            "name": job.get("name"),
            "last_run_at": job.get("last_run_at"),
            "last_status": job.get("last_status"),
        })
    return result


def collect(day: str) -> str:
    now = datetime.now(TZ)
    context = {
        "generated_at": now.isoformat(timespec="seconds"),
        "report_date": day,
        "timezone": "America/Mexico_City",
        "coverage_cutoff": now.isoformat(timespec="minutes"),
        "calendar_tomorrow": collect_calendar_context(now.date() + timedelta(days=1)),
        "google_health_fitbit": health_context(day),
        "financial_kpis_month_to_date": collect_finance_context(day),
        "email_topics_today": collect_mail_context(day),

        "cron_health": cron_health(),
        "speech_contract": {
            "target_exact": os.getenv("ALEXA_TARGET_DEVICE", "MY ECHO"),
            "language": "es-MX",
            "length_characters": "120-1400",
            "style": "fresh executive narrative; no fixed template",
            "must_include": "material work and LinkedIn activity from this date",
            "privacy": "never speak secrets, credentials, internal paths, session IDs, or implementation identifiers",
        },
    }
    return "\n".join([
        "ALEXA EVENING EXECUTIVE RECAP SOURCE CONTEXT",
        json.dumps(context, ensure_ascii=False, indent=2),
        "\n=== ALL ROOT HERMES CONVERSATIONS FOR DATE (SUPPLEMENTARY) ===",
        hermes_day_context(day),
        "\n=== LINKEDIN DURABLE RECORDS + ALL DATE-MATCHED CLAUDE TRANSCRIPTS ===",
        linkedin_context(day),
    ])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date")
    args = parser.parse_args()
    day = args.date or datetime.now(TZ).date().isoformat()
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", day):
        parser.error("--date must use YYYY-MM-DD")
    print(collect(day))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
