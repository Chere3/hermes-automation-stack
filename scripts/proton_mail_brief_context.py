#!/usr/bin/env python3
"""Read-only, metadata-only Proton Mail context for Alexa briefs."""

from __future__ import annotations

import json
import subprocess
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

TZ = ZoneInfo("America/Mexico_City")
HIMALAYA = Path.home() / ".local" / "bin" / "himalaya"
MAX_MESSAGES = 40


def _sender_name(envelope: dict) -> str:
    senders = envelope.get("from")
    if not isinstance(senders, list) or not senders:
        return "Remitente no disponible"
    sender = senders[0] if isinstance(senders[0], dict) else {}
    name = str(sender.get("name") or "").strip()
    if name:
        return name[:120]
    email = str(sender.get("email") or "").strip()
    if "@" in email:
        return email.rsplit("@", 1)[1][:120]
    return "Remitente no disponible"


def _is_seen(envelope: dict) -> bool:
    flags = envelope.get("flags")
    if not isinstance(flags, list):
        return False
    return any(
        isinstance(flag, dict)
        and str(flag.get("iana") or flag.get("raw") or "").lower().strip("\\") == "seen"
        for flag in flags
    )


def collect_mail_context(day: str) -> dict:
    """Return bounded envelope metadata for one calendar date; never read bodies."""
    try:
        datetime.strptime(day, "%Y-%m-%d")
    except ValueError:
        return {"status": "unavailable", "reason": "invalid_date"}

    command = [
        str(HIMALAYA), "--json", "--account", "proton",
        "envelope", "search", "--mailbox", "Inbox",
        "--page-size", str(MAX_MESSAGES),
        "date", day, "order", "by", "date", "desc",
    ]
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"status": "unavailable", "reason": type(exc).__name__}
    if result.returncode != 0:
        return {"status": "unavailable", "reason": "mail_backend_error"}
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError:
        return {"status": "unavailable", "reason": "invalid_backend_response"}

    raw = payload.get("envelopes", []) if isinstance(payload, dict) else []
    envelopes = raw if isinstance(raw, list) else []
    messages = []
    for envelope in envelopes[:MAX_MESSAGES]:
        if not isinstance(envelope, dict):
            continue
        messages.append({
            "received_at": envelope.get("date"),
            "sender": _sender_name(envelope),
            "subject": str(envelope.get("subject") or "(sin asunto)")[:240],
            "unread": not _is_seen(envelope),
        })

    return {
        "status": "available",
        "report_date": day,
        "scope": "Inbox envelope metadata only; no message bodies were read and no flags were changed",
        "message_count_returned": len(messages),
        "unread_count_returned": sum(message["unread"] for message in messages),
        "truncated_at": MAX_MESSAGES if len(messages) == MAX_MESSAGES else None,
        "messages": messages,
    }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--date", default=datetime.now(TZ).date().isoformat())
    args = parser.parse_args()
    print(json.dumps(collect_mail_context(args.date), ensure_ascii=False, indent=2))
