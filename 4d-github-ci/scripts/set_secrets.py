#!/usr/bin/env python3
"""Push GitHub Actions secrets from the `secrets` section of assets/config.yml.

Each value is fed to `gh secret set <NAME>` through stdin, so the secret value
never appears in argv, in process listings, in shell history, or in any printed
output. Only secret NAMES (never values) are logged.

The assistant must NOT read config.yml. This script is the only thing that
reads its `secrets` section, and only via stdin to gh.

Usage:
    python set_secrets.py [--repo OWNER/REPO] [--project DIR] [--config PATH]

If --repo is omitted, the repo is resolved with `gh repo view` run inside
--project (default: current directory).
"""
import argparse
import subprocess
import sys
from pathlib import Path

import _config


def resolve_repo(project: Path):
    try:
        out = subprocess.run(
            ["gh", "repo", "view", "--json", "nameWithOwner", "-q", ".nameWithOwner"],
            cwd=project,
            capture_output=True,
            text=True,
            check=True,
        )
        return out.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return ""


def set_secret(name: str, value: str, repo: str) -> bool:
    # value via stdin only — never on the command line.
    proc = subprocess.run(
        ["gh", "secret", "set", name, "--repo", repo],
        input=value,
        text=True,
        capture_output=True,
    )
    if proc.returncode != 0:
        # gh's stderr does not echo the value; safe to surface.
        sys.stderr.write(proc.stderr)
    return proc.returncode == 0


def main():
    ap = argparse.ArgumentParser(description="Push GitHub Actions secrets via gh.")
    ap.add_argument("--repo", default="", help="OWNER/REPO target (default: detect).")
    ap.add_argument("--project", default=".", help="Repo dir for auto-detect.")
    ap.add_argument(
        "--config",
        default=None,
        help=f"Config file (default: {_config.CONFIG}).",
    )
    args = ap.parse_args()

    # Never fall back to the example for secrets (it only holds a placeholder).
    data, cfg_path = _config.load(explicit=args.config, allow_example=False)
    if data is None:
        print(
            f"error: {cfg_path} not found.\n"
            f"  Copy {_config.CONFIG_EXAMPLE.name} to config.yml and fill in "
            f"your DLTK token.",
            file=sys.stderr,
        )
        return 1

    secrets = (data or {}).get("secrets") or {}
    secrets = {str(k): "" if v is None else str(v) for k, v in secrets.items()}
    if not secrets:
        print(f"No `secrets` section in {cfg_path}; nothing to set.")
        return 0

    repo = args.repo or resolve_repo(Path(args.project).resolve())
    if not repo:
        print(
            "error: could not determine the GitHub repo. Pass --repo OWNER/REPO, "
            "or run inside a cloned repo with a GitHub remote (gh authenticated).",
            file=sys.stderr,
        )
        return 1

    print(f"Setting {len(secrets)} secret(s) on {repo}:")
    failures = 0
    for name, value in secrets.items():
        if value in _config.PLACEHOLDERS:
            print(f"  skip   {name} (still a placeholder — edit config.yml)")
            failures += 1
            continue
        ok = set_secret(name, value, repo)
        print(f"  {'ok    ' if ok else 'FAILED'} {name}")
        failures += 0 if ok else 1

    if failures:
        print(f"{failures} secret(s) not set.", file=sys.stderr)
        return 1
    print("All secrets set.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
