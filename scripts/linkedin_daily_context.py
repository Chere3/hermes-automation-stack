#!/usr/bin/env python3
"""Collect date-scoped LinkedIn operations from persistent project sources.

This collector is deliberately independent of Claude Code conversation/session
IDs. New Claude sessions may append to the same durable journal and artifacts.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from career_ops_context import collect_career_ops_brief

ROOT = Path.home() / "linkedin"
CLAUDE_PROJECT = Path(os.getenv("CLAUDE_LINKEDIN_PROJECT", str(Path.home() / ".claude" / "projects" / "linkedin")))
TZ = ZoneInfo("America/Mexico_City")
HEALTH_PROJECT = Path.home() / "proyectos" / "google-health-kpis"


def health_context(day: str) -> dict:
    try:
        sys.path.insert(0, str(HEALTH_PROJECT))
        from brief_context import collect_health_context

        return collect_health_context(day)
    except Exception as exc:
        return {"status": "unavailable", "reason": type(exc).__name__}



def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except FileNotFoundError:
        return "[archivo no encontrado]"


def extract_day_blocks(text: str, day: str) -> str:
    """Return all level-2 journal blocks whose heading begins with the date."""
    matches = list(re.finditer(r"(?m)^## (\d{4}-\d{2}-\d{2})\b.*$", text))
    blocks: list[str] = []
    for idx, match in enumerate(matches):
        if match.group(1) != day:
            continue
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
        blocks.append(text[match.start():end].strip())
    return "\n\n".join(blocks)


def artifacts_today(folder: Path, day: str, timestamp_fields: tuple[str, ...]) -> list[str]:
    results: list[str] = []
    if not folder.exists():
        return results
    field_pattern = "|".join(re.escape(field) for field in timestamp_fields)
    for path in sorted(folder.glob("*.md")):
        text = read_text(path)[:5000]
        m = re.search(
            rf"(?m)^(?:{field_pattern}):\s*[\"']?([^\n\"']+)", text
        )
        if m and m.group(1).strip().startswith(day):
            results.append(path.name)
    return results


def _message_text(entry: dict) -> str:
    message = entry.get("message")
    if not isinstance(message, dict):
        return ""
    content = message.get("content", "")
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        return ""
    return "\n".join(
        block.get("text", "")
        for block in content
        if isinstance(block, dict) and block.get("type") == "text"
    )


def transcript_context(day: str, max_chars: int = 16000) -> str:
    """Aggregate date-matching root Claude transcripts without pinning IDs."""
    if not CLAUDE_PROJECT.exists():
        return "[Directorio de transcripts de Claude no encontrado]"

    sessions: list[list[str]] = []
    for path in sorted(CLAUDE_PROJECT.glob("*.jsonl")):
        excerpts: list[str] = []
        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        for line in lines:
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            if entry.get("type") not in {"user", "assistant"}:
                continue
            stamp = entry.get("timestamp")
            if not isinstance(stamp, str):
                continue
            try:
                local_dt = datetime.fromisoformat(stamp.replace("Z", "+00:00")).astimezone(TZ)
            except ValueError:
                continue
            if local_dt.date().isoformat() != day:
                continue
            text = _message_text(entry).strip()
            if not text:
                continue
            if text.startswith("<command-message>") or text.startswith("# /loop"):
                continue
            text = re.sub(r"\n{3,}", "\n\n", text)
            if len(text) > 1400:
                text = text[:1400].rstrip() + "…"
            role = "usuario" if entry.get("type") == "user" else "Claude"
            excerpts.append(f"[{local_dt.strftime('%H:%M')} {role}] {text}")
        if excerpts:
            sessions.append(excerpts)

    if not sessions:
        return "[No se encontraron mensajes de transcripts para la fecha]"

    output = [f"Sesiones raíz descubiertas dinámicamente para la fecha: {len(sessions)}"]
    truncated = False
    for index, excerpts in enumerate(sessions, 1):
        output.append(f"\n--- Sesión descubierta {index} (sin ID) ---")
        for excerpt in excerpts:
            if len("\n".join(output)) + len(excerpt) + 1 > max_chars:
                truncated = True
                break
            output.append(excerpt)
        if truncated:
            break
    if truncated:
        output.append("[Extractos acotados por límite de contexto; las fuentes persistentes siguen completas]")
    return "\n".join(output)


def collect_context(day: str) -> str:
    """Return durable project evidence for one calendar date."""
    journal = read_text(ROOT / "metrics" / "session_log.md")
    day_blocks = extract_day_blocks(journal, day)
    state = read_text(ROOT / "metrics" / "STATE.md")
    comments = artifacts_today(ROOT / "comments" / "published", day, ("published_at",))
    posts = artifacts_today(ROOT / "posts" / "published", day, ("published_at",))
    invites = artifacts_today(ROOT / "invites" / "pending", day, ("sent_at",))
    transcripts = transcript_context(day)
    career_ops = collect_career_ops_brief()
    lines = [
        f"LINKEDIN DAILY SOURCE CONTEXT — {day} — America/Mexico_City",
        "",
        "=== DURABLE JOURNAL ENTRIES FOR DATE ===",
        day_blocks or "[No hay entradas persistentes para la fecha]",
        "",
        "=== CURRENT GENERATED STATE (may include cumulative metrics) ===",
        state,
        "",
        "=== DATE-SCOPED ARTIFACTS ===",
        "Comments: " + (", ".join(comments) if comments else "none"),
        "Posts: " + (", ".join(posts) if posts else "none"),
        "Invites: " + (", ".join(invites) if invites else "none"),
    ]
    if career_ops.get("status") == "ok":
        lines.extend([
            "",
            "=== CAREER-OPS STAGED APPLICATIONS — EMBED VERBATIM ===",
            career_ops["verbatim"],
        ])
    elif career_ops.get("status") == "unavailable":
        lines.extend([
            "",
            "=== CAREER-OPS STATUS ===",
            json.dumps(career_ops, ensure_ascii=False),
        ])
    lines.extend([
        "",
        "=== MULTI-SESSION CLAUDE TRANSCRIPT EXCERPTS (SUPPLEMENTARY) ===",
        transcripts,
        "",
        "=== GOOGLE HEALTH + FITBIT DAILY KPIS ===",
        json.dumps(health_context(day), ensure_ascii=False, indent=2),
    ])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", help="Calendar date in YYYY-MM-DD; defaults to today in Mexico City")
    args = parser.parse_args()
    day = args.date or datetime.now(TZ).date().isoformat()
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", day):
        parser.error("--date must use YYYY-MM-DD")
    print(collect_context(day))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
