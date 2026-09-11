#!/usr/bin/env python3
"""Silent post-brief receipt watchdog; emits only actionable failures."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
import os
from zoneinfo import ZoneInfo

TZ = ZoneInfo("America/Mexico_City")
HOME = Path.home()
MORNING_STATE = HOME / ".hermes" / "state" / "alexa-morning-playback"
EVENING_STATE = HOME / ".hermes" / "state" / "alexa-evening"
TARGET = os.getenv("ALEXA_TARGET_DEVICE", "MY ECHO")


def check_receipt(now: datetime, morning_state: Path, evening_state: Path) -> str:
    is_morning = now.hour < 12
    label = "matutino" if is_morning else "nocturno"
    state_dir = morning_state if is_morning else evening_state
    ledger = state_dir / f"{now.date().isoformat()}.json"
    if not ledger.exists():
        return f"⚠️ El brief {label} de Alexa no tiene recibo de reproducción para hoy. Requiere revisión."
    try:
        payload = json.loads(ledger.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return f"⚠️ El recibo del brief {label} de Alexa es inválido. Requiere revisión."
    accepted = (
        payload.get("status") == "accepted"
        and payload.get("target") == TARGET
        and payload.get("http_status") == 200
    )
    if accepted:
        return ""
    return f"⚠️ El brief {label} de Alexa no fue aceptado por Amazon. Requiere revisión."


def main() -> int:
    message = check_receipt(datetime.now(TZ), MORNING_STATE, EVENING_STATE)
    if message:
        print(message)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
