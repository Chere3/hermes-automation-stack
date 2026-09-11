#!/usr/bin/env python3
"""Cron wrapper: print a renewal link only when Google Health is due."""

import sys
from pathlib import Path

PROJECT = Path.home() / "proyectos" / "google-health-kpis"
sys.path.insert(0, str(PROJECT))

from google_health_reauth import prepare


if __name__ == "__main__":
    raise SystemExit(prepare(force=False))
