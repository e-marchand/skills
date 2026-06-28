#!/usr/bin/env python3
"""Generate GitHub CI files for a 4D project.

Generates build.yml / release.yml from the templates in assets/, injecting a
`Check out <dep>` step for every github dependency in
Project/Sources/dependencies.json, and writes FUNDING.yml only when a
`funding` section exists in assets/config.yml.

Checkout ref rule (per dependency `version`):
  - a real tag / semver  -> check that ref out
  - empty / "latest" / "4d" / missing -> check out "main"

This script may inspect config keys to decide whether to keep the DLTK token
line in release.yml, and never prints secret values. Use set_secrets.py to push
secrets.
"""
import argparse
import json
import sys
from pathlib import Path

import _config

MARKER = "# __DEPENDENCY_CHECKOUTS__"
DLTK_TOKEN_LINE = "token: ${{ secrets.DLTK }}"
DLTK_BLOCK_LINES = {
    "product-line: vcs",
    "version: vcs",
    "build: official",
    DLTK_TOKEN_LINE,
}
ASSETS = _config.ASSETS
FUNDING_HEADER = "# These are supported funding model platforms\n\n"


def resolve_ref(version):
    """Map a dependencies.json version to a git ref for checkout."""
    if version is None:
        return "main"
    v = str(version).strip()
    if v.lower() in ("", "latest", "4d"):
        return "main"
    return v


def load_github_deps(project: Path):
    """Return [{name, github, ref}] for github deps in dependencies.json."""
    dep_file = project / "Project" / "Sources" / "dependencies.json"
    if not dep_file.is_file():
        print(f"  ! no dependencies.json at {dep_file} — no checkout steps added")
        return []
    try:
        data = json.loads(dep_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        print(f"  ! could not parse {dep_file}: {exc}")
        return []
    deps = []
    for name, spec in (data.get("dependencies") or {}).items():
        if isinstance(spec, dict) and spec.get("github"):
            deps.append(
                {
                    "name": name,
                    "github": spec["github"],
                    "ref": resolve_ref(spec.get("version")),
                }
            )
    return deps


def render_dep_steps(deps, indent):
    blocks = []
    for d in deps:
        repo = d["github"]
        repo_name = repo.rstrip("/").split("/")[-1]
        blocks.append(
            f"{indent}- name: Check out {repo_name}\n"
            f"{indent}  uses: actions/checkout@v5\n"
            f"{indent}  with:\n"
            f"{indent}    repository: {repo}\n"
            f"{indent}    path: Components/{repo_name}.4dbase\n"
            f"{indent}    ref: {d['ref']}\n"
            f"{indent}    fetch-depth: 0"
        )
    return "\n".join(blocks)


def render_workflow(template_text, deps, include_dltk_token=True):
    out = []
    for line in template_text.splitlines():
        if not include_dltk_token and line.strip() in DLTK_BLOCK_LINES:
            continue
        if line.strip() == MARKER:
            if not deps:
                continue  # drop the placeholder line entirely
            indent = line[: len(line) - len(line.lstrip())]
            out.append(render_dep_steps(deps, indent))
        else:
            out.append(line)
    return "\n".join(out).rstrip("\n") + "\n"


def funding_lines(funding):
    lines = []
    for key, value in (funding or {}).items():
        if isinstance(value, (list, tuple)):
            lines.append(f"{key}: [{', '.join(str(x) for x in value)}]")
        else:
            lines.append(f"{key}: {value}")
    return lines


def render_funding(funding):
    return FUNDING_HEADER + "\n".join(funding_lines(funding)) + "\n"


def write_file(path: Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    existed = path.exists()
    path.write_text(content, encoding="utf-8")
    print(f"  {'updated' if existed else 'created'}  {path}")


def has_configured_dltk(data):
    if not isinstance(data, dict):
        return False
    secrets = data.get("secrets")
    if not isinstance(secrets, dict):
        return False
    value = secrets.get("DLTK")
    if value is None:
        return False
    s = str(value).strip()
    return s not in _config.PLACEHOLDERS


def main():
    ap = argparse.ArgumentParser(description="Install GitHub CI for a 4D project.")
    ap.add_argument(
        "--project",
        default=".",
        help="Path to the 4D project root (default: current directory).",
    )
    ap.add_argument(
        "--config",
        default=None,
        help="Config file (default: assets/config.yml, or the shipped example).",
    )
    args = ap.parse_args()

    project = Path(args.project).resolve()
    if not project.is_dir():
        print(f"error: project not found: {project}", file=sys.stderr)
        return 1

    print(f"Project: {project}")
    deps = load_github_deps(project)
    if deps:
        print("  github dependencies detected:")
        for d in deps:
            print(f"    - {d['name']}: {d['github']} @ {d['ref']}")
    else:
        print("  no github dependencies — workflows will have no extra checkout")

    # Funding comes only from the real config.yml (or explicit --config).
    # Do not fall back to the example; missing funding means no FUNDING.yml.
    data, cfg_path = _config.load(explicit=args.config, allow_example=False)
    funding = (data or {}).get("funding") or {}
    include_dltk_token = has_configured_dltk(data)
    if funding:
        print(f"  funding from {cfg_path.name}: {'; '.join(funding_lines(funding))}")
    else:
        if data is None:
            print("  ! no config.yml found — FUNDING.yml will be skipped")
        else:
            print("  ! no `funding` section in config — FUNDING.yml will be skipped")
    if include_dltk_token:
        print(
            "  DLTK secret configured — release.yml keeps product-line/version/build/token block"
        )
    else:
        print(
            "  ! no configured secrets.DLTK — release.yml will omit product-line/version/build/token block"
        )

    gh = project / ".github"
    build_tmpl = (ASSETS / "build.yml.tmpl").read_text(encoding="utf-8")
    release_tmpl = (ASSETS / "release.yml.tmpl").read_text(encoding="utf-8")

    write_file(gh / "workflows" / "build.yml", render_workflow(build_tmpl, deps))
    write_file(
        gh / "workflows" / "release.yml",
        render_workflow(release_tmpl, deps, include_dltk_token=include_dltk_token),
    )
    if funding:
        write_file(gh / "FUNDING.yml", render_funding(funding))

    print("Done. Next: run set_secrets.py only if your config has `secrets` to push.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
