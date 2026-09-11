#!/usr/bin/env python3
# Alert once when Whisper Money crosses the 7-day stale threshold.
from __future__ import annotations

import json
import os
from pathlib import Path

from whisper_money_finance_context import collect_finance_context

STATE = Path.home() / ".hermes/state/whisper-money-finance-freshness.json"


def read_state() -> dict:
    try:
        value = json.loads(STATE.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def write_state(value: dict) -> None:
    STATE.parent.mkdir(parents=True, exist_ok=True)
    tmp = STATE.with_suffix(".tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False) + "\n", encoding="utf-8")
    os.chmod(tmp, 0o600)
    tmp.replace(STATE)


def main() -> int:
    finance = collect_finance_context()
    freshness = finance.get("data_freshness") if isinstance(finance, dict) else None
    current = freshness.get("status") if isinstance(freshness, dict) else "unavailable"
    latest = freshness.get("latest_transaction_date") if isinstance(freshness, dict) else None
    age = freshness.get("age_days") if isinstance(freshness, dict) else None
    previous = read_state()

    write_state({"status": current, "latest_transaction_date": latest, "age_days": age})

    # One alert per stale episode. A fresh result rearms the transition.
    if current == "stale" and previous.get("status") != "stale":
        days = f"{age} días" if isinstance(age, int) else "más de 7 días"
        date_text = f" (último movimiento: {latest})" if latest else ""
        print(f"Whisper Money lleva {days} sin movimientos actualizados{date_text}. Importa tus movimientos recientes para que los KPIs de los briefs de Alexa vuelvan a ser confiables.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
