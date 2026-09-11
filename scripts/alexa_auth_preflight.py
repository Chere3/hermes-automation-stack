#!/usr/bin/env python3
"""Silent read-only Alexa preflight for scheduled briefs."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

HOME = Path.home()
PROJECT = HOME / "proyectos" / "alexa-mcp-server-secure"
OP_RUNNER = HOME / ".local" / "bin" / "op-run-alexa-mcp"
CHECKER = PROJECT / "scripts" / "check_alexa_auth.py"


def run_preflight(
    *,
    op_runner: Path = OP_RUNNER,
    checker: Path = CHECKER,
    project: Path = PROJECT,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(op_runner), sys.executable, str(checker)],
        cwd=project,
        capture_output=True,
        text=True,
        timeout=90,
    )


def message_for(result: subprocess.CompletedProcess[str]) -> str:
    if result.returncode == 0:
        return ""
    return "⚠️ Alexa no superó la verificación read-only. Revisa la sesión guardada en 1Password antes del próximo brief."


def main() -> int:
    result = run_preflight()
    message = message_for(result)
    if message:
        print(message)
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
