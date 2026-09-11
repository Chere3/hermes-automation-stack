#!/usr/bin/env python3
"""Deterministic one-minute watchdog for one public eBay auction.

Prints only actionable changes or a persistent-source-failure warning. It never
logs in, bids, or modifies the listing/account.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import urlencode

from zoneinfo import ZoneInfo

ITEM_ID = os.getenv("EBAY_ITEM_ID", "YOUR_EBAY_ITEM_ID")
PUBLIC_URL = f"https://www.ebay.com/itm/{ITEM_ID}"
READER_SOURCES = (
    ("us", f"https://r.jina.ai/http://www.ebay.com/itm/{ITEM_ID}"),
    ("de", f"https://r.jina.ai/http://www.ebay.de/itm/{ITEM_ID}"),
)
EXPECTED_TITLE_TOKEN = os.getenv("EBAY_EXPECTED_TITLE_TOKEN", "").strip()
STATE_DIR = Path.home() / ".hermes" / "state" / "ebay" / ITEM_ID
BASELINE = STATE_DIR / "auction.json"
HISTORY = STATE_DIR / "history.jsonl"
FAILURES = STATE_DIR / "failures.json"
HEALTH = STATE_DIR / "health.json"
EVENTS = STATE_DIR / "checks.jsonl"
FAILURE_ALERT_AFTER = 6
TZ = ZoneInfo("America/Mexico_City")


def now_iso() -> str:
    return datetime.now(TZ).isoformat(timespec="seconds")


def _parse_curl_result(source: str, returncode: int, stdout: bytes, stderr: bytes) -> dict[str, object]:
    text = stdout.decode("utf-8", "replace")
    # curl may hit its hard connection deadline after receiving a complete,
    # parseable page. Completeness is decided by the strict parser, not merely
    # by curl's exit code.
    if len(text) < 5_000:
        detail = stderr.decode("utf-8", "replace").strip()[:160]
        raise RuntimeError(
            f"reader response incomplete ({len(text)} bytes, exit {returncode}): {detail}"
        )
    auction = parse_auction(text)
    auction["_source"] = source
    return auction


def fetch_auction() -> dict[str, object]:
    # A minute-scoped query prevents a stale reader cache. Independent US and
    # German marketplace representations provide a bounded fallback.
    minute = int(time.time() // 60)
    errors: list[str] = []
    processes: list[dict[str, object]] = []
    try:
        for source, base in READER_SOURCES:
            url = f"{base}?{urlencode({'monitor_tick': minute})}"
            stdout_file = tempfile.TemporaryFile()
            stderr_file = tempfile.TemporaryFile()
            proc = subprocess.Popen(
                [
                    "curl", "-fsSL", "--compressed", "--max-time", "35",
                    "-A", "Mozilla/5.0 (compatible; HermesAuctionWatch/1.0)",
                    url,
                ],
                stdout=stdout_file,
                stderr=stderr_file,
            )
            processes.append(
                {"source": source, "proc": proc, "stdout": stdout_file, "stderr": stderr_file, "checked": False}
            )

        deadline = time.monotonic() + 38
        while time.monotonic() < deadline:
            unfinished = False
            for entry in processes:
                if entry["checked"]:
                    continue
                proc = entry["proc"]
                assert isinstance(proc, subprocess.Popen)
                if proc.poll() is None:
                    unfinished = True
                    continue
                entry["checked"] = True
                stdout_file = entry["stdout"]
                stderr_file = entry["stderr"]
                stdout_file.seek(0)
                stderr_file.seek(0)
                try:
                    auction = _parse_curl_result(
                        str(entry["source"]),
                        int(proc.returncode),
                        stdout_file.read(),
                        stderr_file.read(),
                    )
                    for other in processes:
                        other_proc = other["proc"]
                        if other_proc is not proc and other_proc.poll() is None:
                            other_proc.terminate()
                    return auction
                except Exception as exc:
                    errors.append(f"{entry['source']}:{type(exc).__name__}:{exc}")
            if not unfinished:
                break
            time.sleep(0.1)
        errors.append("parallel:TimeoutError:hard 38-second deadline")
    finally:
        for entry in processes:
            proc = entry["proc"]
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=1)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait(timeout=1)
            entry["stdout"].close()
            entry["stderr"].close()
    raise RuntimeError("all sources unavailable: " + " | ".join(errors))


def _one(pattern: str, text: str, field: str, flags: int = 0) -> str:
    match = re.search(pattern, text, flags)
    if not match:
        raise RuntimeError(f"missing required field: {field}")
    return " ".join(match.group(1).split())


def parse_auction(text: str) -> dict[str, object]:
    source_match = re.search(
        rf"^URL Source:\s+https?://www\.ebay\.(com|de)/itm/{ITEM_ID}(?:[?\s]|$)",
        text,
        re.MULTILINE,
    )
    if not source_match:
        raise RuntimeError("item identity marker missing")
    locale = source_match.group(1)

    title = _one(r"^#\s+(.+?)\s*$", text, "title", re.MULTILINE)
    if EXPECTED_TITLE_TOKEN and EXPECTED_TITLE_TOKEN.casefold() not in title.casefold():
        raise RuntimeError("unexpected item title/identity")

    item_start = text.find("# " + title)
    end_marker = "About this item" if locale == "com" else "## Ähnliche Artikel"
    item_end = text.find(end_marker, item_start)
    if item_start < 0 or item_end < 0:
        raise RuntimeError("main auction section incomplete")
    main = text[item_start:item_end]

    seller_candidates = re.findall(
        r"\[([^\]]+)\]\(https://www\.ebay\.(?:com|de)/sch/([^/]+)/m\.html[^\n]*\)",
        main,
    )
    seller = next(
        (
            label
            for label, slug in seller_candidates
            if label.casefold() == slug.casefold() and len(label) > 1
        ),
        "",
    )
    if not seller:
        raise RuntimeError("missing required field: seller")
    price_match = re.search(r"\n(EUR)\s+([0-9][0-9.,]*)\s*\n", main)
    if not price_match:
        raise RuntimeError("missing required field: price")
    currency = price_match.group(1)
    raw_price = price_match.group(2)
    if locale == "de":
        price = raw_price.replace(".", "").replace(",", ".")
    else:
        price = raw_price.replace(",", "")

    bids_match = re.search(
        rf"\[([0-9]+) (?:bids?|Gebote?)\]\(https://www\.ebay\.(?:com|de)/bfl/viewbids/{ITEM_ID}",
        main,
        re.IGNORECASE,
    )
    if not bids_match:
        # A zero-bid active auction may render text without a bid-history link.
        zero_bid = re.search(r"\b0 (?:bids?|Gebote?)\b", main, re.IGNORECASE)
        if not zero_bid:
            raise RuntimeError("missing required field: bid_count")
        bid_count = 0
    else:
        bid_count = int(bids_match.group(1))

    ends_match = re.search(r"(?:Ends in|Endet in)\s+([^\n]+)", main)
    ended_markers = (
        "This listing ended",
        "This auction has ended",
        "This listing was ended",
        "The listing you're looking for has ended",
        "Dieses Angebot wurde beendet",
        "Diese Auktion ist beendet",
    )
    ended = any(marker.casefold() in main.casefold() for marker in ended_markers)
    active = bool(ends_match) and ("Place bid" in main or "[Bieten]" in main) and not ended
    if active:
        end_display = " ".join(ends_match.group(1).split())
        # Ignore the volatile leading countdown; retain the stable day/time tail.
        days = {
            "Monday": "Monday", "Tuesday": "Tuesday", "Wednesday": "Wednesday",
            "Thursday": "Thursday", "Friday": "Friday", "Saturday": "Saturday",
            "Sunday": "Sunday", "Montag": "Monday", "Dienstag": "Tuesday",
            "Mittwoch": "Wednesday", "Donnerstag": "Thursday", "Freitag": "Friday",
            "Samstag": "Saturday", "Sonntag": "Sunday",
        }
        stable_match = re.search(
            r"(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday|Montag|Dienstag|Mittwoch|Donnerstag|Freitag|Samstag|Sonntag),\s+(\d{1,2}):(\d{2})(?:\s*([AP]M))?",
            end_display,
            re.IGNORECASE,
        )
        if not stable_match:
            raise RuntimeError("missing stable auction end time")
        day_raw, hour_raw, minute_raw, meridiem = stable_match.groups()
        hour = int(hour_raw)
        if meridiem:
            hour = hour % 12 + (12 if meridiem.upper() == "PM" else 0)
        canonical_day = days[next(k for k in days if k.casefold() == day_raw.casefold())]
        end_label = f"{canonical_day}, {hour:02d}:{minute_raw}"
        status = "active"
    elif ended:
        end_label = "ended"
        status = "ended"
    else:
        raise RuntimeError("auction status is neither active nor explicitly ended")

    return {
        "item_id": ITEM_ID,
        "title": title.rstrip("- "),
        "seller": seller,
        "currency": currency,
        "price": price,
        "bid_count": bid_count,
        "status": status,
        "end_label": end_label,
        "url": PUBLIC_URL,
    }


def load_baseline() -> dict[str, object] | None:
    if not BASELINE.exists():
        return None
    return json.loads(BASELINE.read_text(encoding="utf-8"))["auction"]


def save_baseline(auction: dict[str, object]) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    STATE_DIR.chmod(0o700)
    BASELINE.write_text(
        json.dumps({"checked_at": now_iso(), "auction": auction}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    BASELINE.chmod(0o600)


def clear_failures() -> None:
    FAILURES.unlink(missing_ok=True)


def append_check(event: dict[str, object]) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    with EVENTS.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(event, ensure_ascii=False) + "\n")
    EVENTS.chmod(0o600)


def record_success(auction: dict[str, object]) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    STATE_DIR.chmod(0o700)
    HEALTH.write_text(
        json.dumps(
            {
                "last_success_at": now_iso(),
                "item_id": auction["item_id"],
                "price": auction["price"],
                "currency": auction["currency"],
                "bid_count": auction["bid_count"],
                "status": auction["status"],
                "source": auction.get("_source", "fixture"),
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    HEALTH.chmod(0o600)
    append_check({"at": now_iso(), "result": "success", "source": auction.get("_source", "fixture")})


def record_failure(exc: Exception) -> int:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    STATE_DIR.chmod(0o700)
    count = 0
    if FAILURES.exists():
        try:
            count = int(json.loads(FAILURES.read_text(encoding="utf-8")).get("count", 0))
        except (OSError, ValueError, json.JSONDecodeError):
            count = 0
    count += 1
    FAILURES.write_text(
        json.dumps(
            {
                "count": count,
                "last_failure_at": now_iso(),
                "error_type": type(exc).__name__,
                "error": str(exc)[:300],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    FAILURES.chmod(0o600)
    append_check({"at": now_iso(), "result": "failure", "error": str(exc)[:300]})
    return count


def changed_fields(old: dict[str, object], new: dict[str, object]) -> list[str]:
    watched = ("price", "currency", "bid_count", "status", "title", "seller", "end_label")
    if new.get("_source") == "de":
        watched = tuple(field for field in watched if field != "title")
    return [field for field in watched if old.get(field) != new.get(field)]


def current_report(a: dict[str, object]) -> str:
    return "\n".join(
        [
            "🎯 *Monitor de puja eBay inicializado*",
            "",
            f"- Artículo: {a['title']}",
            f"- Precio actual: *{a['price']} {a['currency']}*",
            f"- Número de pujas: *{a['bid_count']}*",
            f"- Estado: *{a['status']}*",
            f"- Cierre mostrado: {a['end_label']}",
            f"- Vendedor: {a['seller']}",
            "",
            "Tu liderazgo fue informado por ti, pero no puede verificarse desde la vista pública.",
            str(a["url"]),
        ]
    )


def change_report(old: dict[str, object], new: dict[str, object], fields: list[str]) -> str:
    lines = ["🚨 *Cambio en tu puja de eBay*", ""]
    labels = {
        "price": "Precio",
        "currency": "Moneda",
        "bid_count": "Número de pujas",
        "status": "Estado",
        "title": "Título",
        "seller": "Vendedor",
        "end_label": "Cierre",
    }
    paired_price = "price" in fields or "currency" in fields
    if paired_price:
        lines.append(
            f"- Precio: *{old.get('price')} {old.get('currency')}* → *{new.get('price')} {new.get('currency')}*"
        )
    for field in fields:
        if field in {"price", "currency"}:
            continue
        lines.append(f"- {labels[field]}: *{old.get(field)}* → *{new.get(field)}*")
    if "bid_count" in fields or "price" in fields or "status" in fields:
        lines.extend(["", "⚠️ El estado de tu liderazgo no es visible públicamente. Revisa eBay inmediatamente."])
    lines.extend(["", str(new["url"])])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--initialize", action="store_true")
    parser.add_argument("--report-current", action="store_true")
    args = parser.parse_args()

    auction = fetch_auction()
    clear_failures()
    record_success(auction)
    old = load_baseline()

    # The German marketplace translates the title. Keep the verified baseline
    # title so a fallback cannot fabricate a listing-title change.
    if old is not None and auction.get("_source") == "de":
        auction["title"] = old["title"]

    if args.initialize or old is None:
        save_baseline(auction)
        print(current_report(auction))
        return 0
    if args.report_current:
        print(current_report(auction))
        return 0

    fields = changed_fields(old, auction)
    if not fields:
        return 0

    report = change_report(old, auction, fields)
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    with HISTORY.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps({"detected_at": now_iso(), "fields": fields, "report": report}, ensure_ascii=False) + "\n")
    HISTORY.chmod(0o600)
    save_baseline(auction)
    print(report)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        failures = record_failure(exc)
        if failures == FAILURE_ALERT_AFTER:
            print(
                "⚠️ *Monitor de eBay temporalmente sin acceso*\n\n"
                f"Las dos rutas de lectura fallaron durante *{failures} heartbeats consecutivos*. "
                "La línea base permanece intacta y el monitor seguirá reintentando cada minuto."
            )
        raise SystemExit(0)
