#!/usr/bin/env python3
"""Run a startup method with a user-provided 4D executable path."""

from __future__ import annotations

import argparse
import os
import signal
import subprocess
import sys
import time
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run a 4D startup method and terminate the process if it stays alive."
    )
    parser.add_argument("four_d_path", help="Path to 4D.app, 4D binary, or 4D.exe")
    parser.add_argument("project_path", help="Path to the .4DProject file")
    parser.add_argument("startup_method", help="Startup method name")
    parser.add_argument("extra_args", nargs="*", help="Extra arguments forwarded to 4D")
    return parser.parse_args()


def resolve_four_d_binary(raw_path: str) -> Path:
    candidate = Path(raw_path).expanduser()

    if candidate.is_file():
        if candidate.name in {"4D", "4D.exe"}:
            return candidate.resolve()
        raise ValueError(f"expected a 4D binary, got file: {candidate}")

    if candidate.is_dir() and candidate.suffix == ".app":
        binary = candidate / "Contents/MacOS/4D"
        if binary.is_file():
            return binary.resolve()

    raise ValueError(f"expected a 4D.app path, 4D binary, or 4D.exe path: {candidate}")


def terminate_process(process: subprocess.Popen) -> None:
    if process.poll() is not None:
        return

    process.terminate()
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        if process.poll() is not None:
            return
        time.sleep(0.2)

    process.kill()


def main() -> int:
    args = parse_args()

    try:
        binary_path = resolve_four_d_binary(args.four_d_path)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    project_path = Path(args.project_path).expanduser()
    if not project_path.is_file() or project_path.suffix != ".4DProject":
        print(f"Error: project path must point to a .4DProject file: {project_path}", file=sys.stderr)
        return 1

    kill_after = int(os.environ.get("FOURD_KILL_AFTER", "30"))
    command = [
        str(binary_path),
        f"--project={project_path.resolve()}",
        f"--startup-method={args.startup_method}",
        "--skip-onstartup",
        *args.extra_args,
    ]

    creationflags = 0
    preexec_fn = None
    if os.name == "nt":
        creationflags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    else:
        preexec_fn = os.setsid

    process = subprocess.Popen(command, creationflags=creationflags, preexec_fn=preexec_fn)
    timed_out = False

    try:
        if kill_after == 0:
            return process.wait()

        try:
            return process.wait(timeout=kill_after)
        except subprocess.TimeoutExpired:
            timed_out = True
            print(
                f"4D is still running after {kill_after}s; terminating it. "
                "Prefer a startup method that calls QUIT 4D.",
                file=sys.stderr,
            )

            if os.name != "nt":
                try:
                    os.killpg(process.pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass

            terminate_process(process)
            return_code = process.wait()
            if return_code == 0:
                return 124
            return return_code
    except KeyboardInterrupt:
        print("Interrupted; terminating 4D process.", file=sys.stderr)
        timed_out = True
        terminate_process(process)
        return 130
    finally:
        if not timed_out and process.poll() is None:
            terminate_process(process)


if __name__ == "__main__":
    raise SystemExit(main())
