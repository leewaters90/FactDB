#!/usr/bin/env python3
"""Simple smoke test for Copilot CLI prompt/response on Windows.

Exits with:
0 = success (expected marker found)
1 = copilot executable not found
2 = copilot command failed
3 = command timed out
4 = output did not contain expected marker
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

EXPECTED = "COPILOT_SMOKE_OK"


def find_copilot() -> str | None:
    # Prefer standalone Copilot CLI if installed.
    for candidate in (
        shutil.which("copilot"),
        shutil.which("copilot.exe"),
        shutil.which("gh"),
        shutil.which("gh.exe"),
    ):
        if candidate:
            return candidate

    local = Path(os.getenv("LOCALAPPDATA", "")) / "Programs" / "GitHub Copilot" / "copilot.exe"
    if local.exists():
        return str(local)
    return None


def build_cmd(exe: str, prompt: str) -> list[str]:
    base = os.path.basename(exe).lower()
    if base.startswith("gh"):
        return [exe, "copilot", "suggest", "-t", "shell", prompt]
    return [exe, "suggest", "-t", "shell", prompt]


def main() -> int:
    parser = argparse.ArgumentParser(description="Copilot CLI smoke test")
    parser.add_argument("--timeout", type=int, default=60)
    args = parser.parse_args()

    exe = find_copilot()
    if not exe:
        print("FAIL: Copilot CLI executable not found")
        return 1

    prompt = f"Reply with EXACTLY: {EXPECTED}"
    cmd = build_cmd(exe, prompt)

    print(f"Using executable: {exe}")
    print("Running command:", " ".join(cmd[:4]), "<prompt>")

    try:
        completed = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=max(10, args.timeout),
            env=os.environ.copy(),
        )
    except subprocess.TimeoutExpired:
        print(f"FAIL: Timed out after {args.timeout}s")
        return 3
    except Exception as exc:  # pragma: no cover
        print(f"FAIL: Exception launching Copilot CLI: {exc}")
        return 2

    stdout = completed.stdout or ""
    stderr = completed.stderr or ""

    print(f"Return code: {completed.returncode}")
    if stdout.strip():
        print("--- STDOUT ---")
        print(stdout.strip())
    if stderr.strip():
        print("--- STDERR ---")
        print(stderr.strip())

    if completed.returncode != 0:
        print("FAIL: Copilot CLI command failed")
        return 2

    if EXPECTED in stdout or EXPECTED in stderr:
        print("PASS: Copilot CLI responded with expected marker")
        return 0

    print("FAIL: Expected marker not found in output")
    return 4


if __name__ == "__main__":
    raise SystemExit(main())
