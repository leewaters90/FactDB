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


def build_cmds(exe: str, prompt: str) -> list[list[str]]:
    base = os.path.basename(exe).lower()
    if base.startswith("gh"):
        # New Copilot CLI prompt mode (supported by current releases).
        return [
            [exe, "copilot", "--", "-p", prompt, "--allow-all", "--no-ask-user"],
            # Legacy fallback retained for older installations.
            [exe, "copilot", "suggest", "-t", "shell", prompt],
        ]
    return [
        # New Copilot CLI prompt mode (supported by current releases).
        [exe, "-p", prompt, "--allow-all", "--no-ask-user"],
        # Legacy fallback retained for older installations.
        [exe, "suggest", "-t", "shell", prompt],
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description="Copilot CLI smoke test")
    parser.add_argument("--timeout", type=int, default=60)
    args = parser.parse_args()

    exe = find_copilot()
    if not exe:
        print("FAIL: Copilot CLI executable not found")
        return 1

    prompt = f"Reply with EXACTLY: {EXPECTED}"
    print(f"Using executable: {exe}")
    cmds = build_cmds(exe, prompt)

    saw_failure = False
    for idx, cmd in enumerate(cmds, start=1):
        print(f"Attempt {idx}/{len(cmds)}:", " ".join(cmd[:4]), "<prompt>")
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

        if EXPECTED in stdout or EXPECTED in stderr:
            print("PASS: Copilot CLI responded with expected marker")
            return 0

        if completed.returncode != 0:
            saw_failure = True

    if saw_failure:
        print("FAIL: Copilot CLI command failed")
        return 2
    print("FAIL: Expected marker not found in output")
    return 4


if __name__ == "__main__":
    raise SystemExit(main())
