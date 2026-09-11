#!/usr/bin/env python3
"""Read-only Whisper Money KPI collector for Alexa briefs.

Outputs normalized aggregate JSON only. It never emits credentials, account
identifiers/names, transaction narratives, or merchant details.
"""
from __future__ import annotations

import asyncio
import json
import os
import subprocess
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import httpx2
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

TZ = ZoneInfo("America/Mexico_City")
MCP_URL = os.getenv("WHISPER_MONEY_MCP_URL", "http://127.0.0.1:18881/mcp")
OP_BIN = os.getenv("OP_BIN", "op")
OP_TOKEN_FILE = Path.home() / ".config/hermes/credentials/op-service-account-token"
OP_REFERENCE = os.getenv("WHISPER_MONEY_OP_REFERENCE", "op://YOUR_VAULT/YOUR_ITEM/password")
ALLOWED_TOOLS = {"get_cashflow", "get_net_worth", "list_budgets", "search_transactions"}


def _secret() -> str:
    env = os.environ.copy()
    env["OP_SERVICE_ACCOUNT_TOKEN"] = OP_TOKEN_FILE.read_text(encoding="utf-8").strip()
    result = subprocess.run(
        [OP_BIN, "read", OP_REFERENCE], env=env, capture_output=True, text=True,
        timeout=20, check=True,
    )
    env.pop("OP_SERVICE_ACCOUNT_TOKEN", None)
    value = result.stdout.strip()
    if not value:
        raise RuntimeError("credential unavailable")
    return value


def _tool_json(result: Any) -> dict[str, Any]:
    if getattr(result, "is_error", False):
        raise RuntimeError("MCP tool returned an error")
    for item in getattr(result, "content", []):
        text = getattr(item, "text", None)
        if text:
            value = json.loads(text)
            if isinstance(value, dict):
                return value
    raise RuntimeError("MCP tool returned no JSON object")


def _major(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return round(float(value) / 100.0, 2)


def _percent_change(current: float | None, previous: float | None) -> float | None:
    if current is None or previous in (None, 0):
        return None
    return round((current - previous) / abs(previous) * 100.0, 1)


def _category_signals(sankey: dict[str, Any]) -> list[dict[str, Any]]:
    rows = sankey.get("expense_categories")
    if not isinstance(rows, list):
        return []
    safe: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        name = row.get("name") or row.get("category") or row.get("label")
        raw = next((row.get(k) for k in ("amount", "value", "total", "expense") if isinstance(row.get(k), (int, float))), None)
        if isinstance(name, str) and raw is not None:
            safe.append({"category": name[:80], "expense": _major(raw)})
    safe.sort(key=lambda x: abs(x.get("expense") or 0), reverse=True)
    return safe[:3]


def _budget_signals(payload: dict[str, Any]) -> dict[str, Any]:
    rows = payload.get("budgets")
    if not isinstance(rows, list):
        return {"count": 0, "exceptions": []}
    exceptions: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        name = row.get("name") or row.get("category_name")
        allocated = next((row.get(k) for k in ("allocated", "amount", "budgeted") if isinstance(row.get(k), (int, float))), None)
        spent = next((row.get(k) for k in ("spent", "used") if isinstance(row.get(k), (int, float))), None)
        if not isinstance(name, str) or allocated in (None, 0) or spent is None:
            continue
        used_pct = round(float(spent) / float(allocated) * 100.0, 1)
        if used_pct >= 85:
            exceptions.append({"budget": name[:80], "used_pct": used_pct, "status": "exceeded" if used_pct > 100 else "near_limit"})
    exceptions.sort(key=lambda x: x["used_pct"], reverse=True)
    return {"count": len(rows), "exceptions": exceptions[:3]}


async def _collect(reference_day: date) -> dict[str, Any]:
    token = _secret()
    generated = datetime.now(TZ)
    start = reference_day.replace(day=1)
    net_start = reference_day - timedelta(days=90)
    client = httpx2.AsyncClient(headers={"Authorization": f"Bearer {token}"}, timeout=45.0)
    try:
        async with streamable_http_client(MCP_URL, http_client=client) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                discovered = {tool.name for tool in (await session.list_tools()).tools}
                if not ALLOWED_TOOLS.issubset(discovered):
                    raise RuntimeError("required read tools unavailable")
                cashflow = _tool_json(await session.call_tool("get_cashflow", {"from": start.isoformat(), "to": reference_day.isoformat()}))
                networth = _tool_json(await session.call_tool("get_net_worth", {"from": net_start.isoformat(), "to": reference_day.isoformat(), "granularity": "monthly"}))
                budgets = _tool_json(await session.call_tool("list_budgets", {}))
                latest = _tool_json(await session.call_tool("search_transactions", {"to": reference_day.isoformat(), "limit": 1}))
    finally:
        token = ""
        await client.aclose()

    summary = cashflow.get("summary") if isinstance(cashflow.get("summary"), dict) else {}
    current_raw = summary.get("current") if isinstance(summary.get("current"), dict) else {}
    previous_raw = summary.get("previous") if isinstance(summary.get("previous"), dict) else {}
    current = {k: _major(current_raw.get(k)) for k in ("income", "expense", "net", "savings", "investments")}
    current["savings_rate_pct"] = current_raw.get("savings_rate") if isinstance(current_raw.get("savings_rate"), (int, float)) else None
    previous = {k: _major(previous_raw.get(k)) for k in ("income", "expense", "net", "savings", "investments")}
    previous["savings_rate_pct"] = previous_raw.get("savings_rate") if isinstance(previous_raw.get("savings_rate"), (int, float)) else None

    nw = networth.get("current") if isinstance(networth.get("current"), dict) else {}
    nw_current = _major(nw.get("current")); nw_previous = _major(nw.get("previous"))
    delta = None if nw_current is None or nw_previous is None else round(nw_current - nw_previous, 2)
    if delta is None:
        direction = None
    elif delta > 0:
        direction = "up"
    elif delta < 0:
        direction = "down"
    else:
        direction = "flat"

    txs = latest.get("transactions") if isinstance(latest.get("transactions"), list) else []
    latest_date = None
    if txs and isinstance(txs[0], dict):
        candidate = txs[0].get("transaction_date") or txs[0].get("date")
        if isinstance(candidate, str):
            latest_date = candidate[:10]
    age_days = None
    if latest_date:
        try:
            age_days = (reference_day - date.fromisoformat(latest_date)).days
        except ValueError:
            latest_date = None
    freshness = "unknown" if age_days is None else ("fresh" if age_days <= 2 else "delayed" if age_days <= 7 else "stale")

    currency = cashflow.get("currency_code") or networth.get("currency_code") or nw.get("currency_code") or budgets.get("currency")
    return {
        "status": "available",
        "source": "Whisper Money read-only MCP",
        "generated_at": generated.isoformat(timespec="seconds"),
        "timezone": "America/Mexico_City",
        "currency": currency,
        "data_freshness": {"latest_transaction_date": latest_date, "age_days": age_days, "status": freshness, "sync_mode": "manual_import"},
        "period": {"kind": "month_to_date", "from": start.isoformat(), "to": reference_day.isoformat(), "day_open": reference_day == generated.date()},
        "cashflow": {
            "current": current,
            "previous_comparable": previous,
            "change_pct": {k: _percent_change(current.get(k), previous.get(k)) for k in ("income", "expense", "net", "savings")},
        },
        "net_worth": {"direction": direction, "change_pct": _percent_change(nw_current, nw_previous), "currency": nw.get("currency_code") or currency},
        "top_expense_categories": _category_signals(cashflow.get("sankey") if isinstance(cashflow.get("sankey"), dict) else {}),
        "budgets": _budget_signals(budgets),
        "privacy": "Aggregate signals only; exact account balances, account names, IDs, merchants and transaction narratives are intentionally omitted.",
    }


def collect_finance_context(day: str | None = None) -> dict[str, Any]:
    try:
        reference = date.fromisoformat(day) if day else datetime.now(TZ).date()
        return asyncio.run(_collect(reference))
    except Exception as exc:
        return {"status": "unavailable", "reason": type(exc).__name__, "source": "Whisper Money read-only MCP", "fallback_used": False}


if __name__ == "__main__":
    print(json.dumps(collect_finance_context(), ensure_ascii=False, sort_keys=True))
