#!/usr/bin/env python3
"""Cron entry point for the Google Health KPI synchronizer."""

import sys
from pathlib import Path

PROJECT = Path.home() / "proyectos" / "google-health-kpis"
sys.path.insert(0, str(PROJECT))

from sync_google_health import main


if __name__ == "__main__":
    raise SystemExit(main())
