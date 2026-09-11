#!/usr/bin/env python3
"""Watch AstraZeneca Eightfold jobs returned for the Zapopan search."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from zoneinfo import ZoneInfo

API_ROOT = "https://astrazeneca.eightfold.ai/api/pcsx/search"
API_URL = f"{API_ROOT}?domain=astrazeneca.com&query=&location=zapopan&start=0&"
SEARCH_URL = "https://astrazeneca.eightfold.ai/careers?domain=astrazeneca.com&start=0&location=zapopan"
JOB_BASE = "https://astrazeneca.eightfold.ai"
MAX_RESULTS = 1000
MAX_PAGES = 100
MAX_RESPONSE_BYTES = 2 * 1024 * 1024
SNAPSHOT_RETRIES = 3
STATE_DIR = Path.home() / ".hermes" / "state" / "astrazeneca-zapopan-jobs"
BASELINE = STATE_DIR / "jobs.json"
HISTORY = STATE_DIR / "history.jsonl"
TZ = ZoneInfo("America/Mexico_City")


def posted_date(timestamp: int | float | None) -> str | None:
    if not timestamp:
        return None
    return datetime.fromtimestamp(timestamp, timezone.utc).date().isoformat()


class IncompleteSnapshot(RuntimeError):
    """The API response was valid JSON but not one coherent full snapshot."""


def page_url(start: int) -> str:
    return f"{API_ROOT}?domain=astrazeneca.com&query=&location=zapopan&start={start}&"


def normalized_job_id(value: object, *, start: int) -> str:
    if isinstance(value, bool) or not isinstance(value, (str, int)):
        raise IncompleteSnapshot(f"id inválido {value!r} en start={start}")
    job_id = str(value).strip()
    if not job_id:
        raise IncompleteSnapshot(f"id inválido vacío en start={start}")
    return job_id


def fetch_page(start: int) -> tuple[int, list[dict[str, object]]]:
    command = [
        "curl",
        "--http1.1",
        "--compressed",
        "--connect-timeout", "15",
        "--max-time", "45",
        "--max-filesize", str(MAX_RESPONSE_BYTES),
        "--retry", "3",
        "--retry-delay", "2",
        "--fail-with-body",
        "--silent",
        "--show-error",
        "--user-agent", "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/126 Safari/537.36",
        "--header", "Accept: application/json",
        "--header", "Accept-Language: en-US,en;q=0.9",
        page_url(start),
    ]
    try:
        completed = subprocess.run(command, check=True, capture_output=True, timeout=180)
    except subprocess.CalledProcessError as exc:
        detail = exc.stderr.decode("utf-8", "replace").strip()
        raise RuntimeError(f"Eightfold no respondió después de los reintentos: {detail}") from exc
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError("Eightfold excedió el límite global de 180 segundos") from exc

    if len(completed.stdout) > MAX_RESPONSE_BYTES:
        raise RuntimeError(
            f"Eightfold excedió el límite de respuesta de {MAX_RESPONSE_BYTES} bytes en start={start}"
        )
    try:
        payload = json.loads(completed.stdout)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise RuntimeError(f"Eightfold devolvió JSON inválido en start={start}") from exc
    if not isinstance(payload, dict):
        raise RuntimeError(f"Eightfold devolvió un esquema JSON inválido en start={start}: payload no es objeto")
    if payload.get("status") != 200:
        raise RuntimeError(f"API status {payload.get('status')}: {payload.get('error')}")
    data = payload.get("data")
    if not isinstance(data, dict):
        raise RuntimeError(f"Eightfold devolvió un esquema JSON inválido en start={start}: data no es objeto")
    positions = data.get("positions")
    if not isinstance(positions, list) or not all(isinstance(item, dict) for item in positions):
        raise RuntimeError(f"La API no devolvió una lista válida de vacantes en start={start}")
    declared_count = data.get("count")
    if isinstance(declared_count, bool) or not isinstance(declared_count, int) or declared_count < 0:
        raise RuntimeError(f"La API devolvió un total inválido en start={start}: {declared_count!r}")
    if declared_count > MAX_RESULTS:
        raise RuntimeError(f"La API declaró {declared_count} vacantes; excede el límite seguro de {MAX_RESULTS}")
    return declared_count, positions


def fetch_complete_positions() -> list[dict[str, object]]:
    expected_count: int | None = None
    positions: list[dict[str, object]] = []
    seen_ids: set[str] = set()
    start = 0

    for _ in range(MAX_PAGES):
        declared_count, page = fetch_page(start)
        if expected_count is None:
            expected_count = declared_count
        elif declared_count != expected_count:
            raise IncompleteSnapshot(
                f"el total cambió durante la paginación: {expected_count} a {declared_count}"
            )

        if expected_count == 0:
            if page:
                raise IncompleteSnapshot("la API declaró 0 vacantes pero devolvió resultados")
            return []
        if not page:
            raise IncompleteSnapshot(
                f"página vacía en start={start}: reunidas {len(positions)} de {expected_count}"
            )

        for position in page:
            job_id = normalized_job_id(position.get("id"), start=start)
            if job_id in seen_ids:
                raise IncompleteSnapshot(f"id duplicado {job_id} en start={start}")
            seen_ids.add(job_id)
            positions.append(position)

        if len(positions) == expected_count:
            return positions
        if len(positions) > expected_count:
            raise IncompleteSnapshot(
                f"se reunieron {len(positions)} resultados, más que el total declarado {expected_count}"
            )
        start += len(page)

    raise IncompleteSnapshot(f"se excedió el límite de {MAX_PAGES} páginas")


def fetch_jobs() -> dict[str, dict[str, object]]:
    last_incomplete: IncompleteSnapshot | None = None
    positions: list[dict[str, object]] | None = None
    for attempt in range(1, SNAPSHOT_RETRIES + 1):
        try:
            positions = fetch_complete_positions()
            break
        except IncompleteSnapshot as exc:
            last_incomplete = exc
            if attempt < SNAPSHOT_RETRIES:
                time.sleep(1)
    if positions is None:
        raise RuntimeError(
            f"Respuesta paginada inconsistente después de {SNAPSHOT_RETRIES} intentos: {last_incomplete}"
        )

    jobs: dict[str, dict[str, object]] = {}
    for position in positions:
        job_id = str(position["id"]).strip()
        path = position.get("positionUrl") or f"/careers/job/{job_id}"
        jobs[job_id] = {
            "id": job_id,
            "reference": position.get("displayJobId") or position.get("atsJobId"),
            "title": position.get("name"),
            "locations": position.get("locations") or [],
            "department": position.get("department"),
            "work_mode": position.get("workLocationOption") or position.get("locationFlexibility"),
            "posted_date": posted_date(position.get("postedTs")),
            "url": f"{JOB_BASE}{path}?{urlencode({'domain': 'astrazeneca.com'})}",
        }
    return dict(sorted(jobs.items(), key=lambda item: (str(item[1]["title"]).lower(), item[0])))


def save_snapshot(jobs: dict[str, dict[str, object]]) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "checked_at": datetime.now(TZ).isoformat(timespec="seconds"),
        "source": API_URL,
        "jobs": jobs,
    }
    serialized = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=STATE_DIR,
            prefix=f".{BASELINE.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temp_path = Path(handle.name)
            handle.write(serialized)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, BASELINE)
        temp_path = None
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)


def load_snapshot() -> dict[str, dict[str, object]] | None:
    if not BASELINE.exists():
        return None
    return json.loads(BASELINE.read_text(encoding="utf-8"))["jobs"]


def mode_counts(jobs: dict[str, dict[str, object]]) -> tuple[int, int, int, int]:
    onsite = sum(str(job.get("work_mode", "")).lower() == "onsite" for job in jobs.values())
    hybrid = sum(str(job.get("work_mode", "")).lower() == "hybrid" for job in jobs.values())
    remote = sum(str(job.get("work_mode", "")).lower() == "remote" for job in jobs.values())
    other = len(jobs) - onsite - hybrid - remote
    return onsite, hybrid, remote, other


def mode_label(value: object) -> str:
    labels = {"onsite": "presencial", "hybrid": "híbrido", "remote": "remoto"}
    return labels.get(str(value).lower(), str(value or "sin especificar"))


def current_report(jobs: dict[str, dict[str, object]]) -> str:
    onsite, hybrid, remote, other = mode_counts(jobs)
    lines = [
        "💼 *Línea base — Vacantes AstraZeneca en Zapopan*",
        "",
        f"- Vacantes activas: *{len(jobs)}*",
        f"- Presenciales: *{onsite}*",
        f"- Híbridas: *{hybrid}*",
        f"- Remotas: *{remote}*",
    ]
    if other:
        lines.append(f"- Sin modalidad especificada: *{other}*")
    lines.extend(["", "*Vacantes actuales*"])
    for job in jobs.values():
        location = ", ".join(str(x) for x in job["locations"])
        lines.extend([
            f"- *{job['title']}* ({job['reference']})",
            f"  {job['department']} · {mode_label(job['work_mode'])} · {location}",
            f"  Publicada: {job['posted_date']}",
            f"  {job['url']}",
        ])
    lines.extend(["", SEARCH_URL])
    return "\n".join(lines)


def no_change_report(jobs: dict[str, dict[str, object]]) -> str:
    onsite, hybrid, remote, other = mode_counts(jobs)
    now = datetime.now(TZ).strftime("%d/%m/%Y %H:%M")
    lines = [
        "✅ *Vacantes AstraZeneca Zapopan — sin cambios*",
        "",
        f"Revisión: {now}",
        f"- Vacantes activas: *{len(jobs)}*",
        f"- Presenciales: *{onsite}*",
        f"- Híbridas: *{hybrid}*",
        f"- Remotas: *{remote}*",
    ]
    if other:
        lines.append(f"- Sin modalidad especificada: *{other}*")
    return "\n".join(lines)


def change_report(old: dict[str, dict[str, object]], new: dict[str, dict[str, object]]) -> str:
    added_ids = sorted(set(new) - set(old), key=lambda job_id: str(new[job_id]["title"]).lower())
    removed_ids = sorted(set(old) - set(new), key=lambda job_id: str(old[job_id]["title"]).lower())
    tracked_fields = ("reference", "title", "locations", "department", "work_mode", "posted_date")
    changed: list[tuple[dict[str, object], dict[str, object], list[str]]] = []
    for job_id in sorted(set(old) & set(new), key=lambda value: str(new[value]["title"]).lower()):
        before, after = old[job_id], new[job_id]
        fields = [field for field in tracked_fields if before.get(field) != after.get(field)]
        if fields:
            changed.append((before, after, fields))

    if not added_ids and not removed_ids and not changed:
        return ""

    now = datetime.now(TZ).strftime("%d/%m/%Y %H:%M")
    lines = [f"🚨 *Cambio en vacantes AstraZeneca Zapopan — {now}*", ""]

    if added_ids:
        lines.append("*Vacantes nuevas*")
        for job_id in added_ids:
            job = new[job_id]
            lines.extend([
                f"- *{job['title']}* ({job['reference']})",
                f"  {job['department']} · {mode_label(job['work_mode'])}",
                f"  {job['url']}",
            ])
        lines.append("")

    if removed_ids:
        lines.append("*Vacantes retiradas o cerradas*")
        for job_id in removed_ids:
            job = old[job_id]
            lines.append(f"- {job['title']} ({job['reference']})")
        lines.append("")

    if changed:
        lines.append("*Vacantes modificadas*")
        field_names = {
            "reference": "referencia",
            "title": "título",
            "locations": "ubicación",
            "department": "área",
            "work_mode": "modalidad",
            "posted_date": "fecha de publicación",
        }
        for before, after, fields in changed:
            lines.append(f"- *{after['title']}*: " + ", ".join(field_names[f] for f in fields))
            lines.append(f"  {after['url']}")
        lines.append("")

    onsite, hybrid, remote, _ = mode_counts(new)
    lines.append(
        f"Estado actual: *{len(new)} activas* · *{onsite} presenciales* · *{hybrid} híbridas* · *{remote} remotas*"
    )
    lines.append(SEARCH_URL)
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--initialize", action="store_true")
    parser.add_argument("--report-current", action="store_true")
    args = parser.parse_args()

    jobs = fetch_jobs()
    if args.report_current:
        print(current_report(jobs))
        return 0

    old = load_snapshot()
    if args.initialize or old is None:
        save_snapshot(jobs)
        if args.initialize:
            print(current_report(jobs))
        return 0

    report = change_report(old, jobs)
    if report:
        event = {"detected_at": datetime.now(TZ).isoformat(timespec="seconds"), "report": report}
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        with HISTORY.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, ensure_ascii=False) + "\n")
        save_snapshot(jobs)
        print(report)
    else:
        print(no_change_report(jobs))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"Error al revisar vacantes AstraZeneca Zapopan: {exc}", file=sys.stderr)
        raise SystemExit(1)
