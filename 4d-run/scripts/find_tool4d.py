#!/usr/bin/env python3
"""Find the newest installed tool4d executable."""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path


def natural_sort_key(path: Path) -> list[object]:
    return [int(part) if part.isdigit() else part.casefold() for part in re.split(r"(\d+)", str(path))]


def tool4d_search_paths() -> list[Path]:
    paths: list[Path] = []
    home = Path.home()

    if sys.platform == "darwin":
        paths.extend(
            [
                home / "Library/Application Support/Code/User/globalStorage/4d.4d-analyzer/tool4d",
                home / "Library/Application Support/Antigravity/User/globalStorage/4d.4d-analyzer/tool4d",
            ]
        )
    elif os.name == "nt":
        for env_name in ("APPDATA", "LOCALAPPDATA"):
            env_value = os.environ.get(env_name)
            if not env_value:
                continue
            base = Path(env_value)
            paths.extend(
                [
                    base / "Code/User/globalStorage/4d.4d-analyzer/tool4d",
                    base / "Antigravity/User/globalStorage/4d.4d-analyzer/tool4d",
                ]
            )

    return paths


def resolve_tool4d(candidate: Path) -> Path | None:
    candidate = candidate.expanduser()

    if candidate.is_file():
        if candidate.name in {"tool4d", "tool4d.exe"}:
            return candidate.resolve()
        return None

    if candidate.is_dir() and candidate.suffix == ".app":
        binary = candidate / "Contents/MacOS/tool4d"
        if binary.is_file():
            return binary.resolve()

    return None


def discover_tool4d() -> Path | None:
    candidates: list[Path] = []
    for base_path in tool4d_search_paths():
        if not base_path.is_dir():
            continue

        for pattern in ("**/tool4d", "**/tool4d.exe", "**/tool4d.app"):
            for candidate in base_path.glob(pattern):
                resolved = resolve_tool4d(candidate)
                if resolved is not None:
                    candidates.append(resolved)

    if not candidates:
        return None

    unique_candidates = sorted({candidate for candidate in candidates}, key=natural_sort_key)
    return unique_candidates[-1]


def main() -> int:
    tool4d_env = os.environ.get("TOOL4D")
    if tool4d_env:
        resolved = resolve_tool4d(Path(tool4d_env))
        if resolved is None:
            print(f"Error: TOOL4D is set but does not point to tool4d: {tool4d_env}", file=sys.stderr)
            return 1
        print(resolved)
        return 0

    discovered = discover_tool4d()
    if discovered is None:
        print("tool4d not found; set TOOL4D to the executable path", file=sys.stderr)
        return 1

    print(discovered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
