#!/usr/bin/env python3
"""Shared config loader for the 4d-github-ci skill.

A single config.yml holds BOTH the funding handle(s) and the Actions secrets:

    funding:
      github: [phimage]
    secrets:
      DLTK: "..."

Because it contains secret values the file is private (git-ignored). Only the
skill's scripts read it, and secret values are never printed. PyYAML is used
when available; otherwise a tiny built-in parser handles this simple shape so
the skill works with a bare Python install.
"""
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
ASSETS = SKILL_DIR / "assets"
CONFIG = ASSETS / "config.yml"
CONFIG_EXAMPLE = ASSETS / "config.yml.example"

PLACEHOLDERS = {"", "PUT_YOUR_DLTK_TOKEN_HERE", "CHANGE_ME"}


def _strip_quotes(s):
    s = s.strip()
    if len(s) >= 2 and s[0] == s[-1] and s[0] in "\"'":
        return s[1:-1]
    return s


def _parse_value(raw):
    raw = raw.strip()
    if raw.startswith("[") and raw.endswith("]"):
        inner = raw[1:-1].strip()
        return [_strip_quotes(p) for p in inner.split(",")] if inner else []
    return _strip_quotes(raw)


def _mini_parse(text):
    """YAML subset: top-level `section:` blocks of `key: value` lines, where
    value is a scalar or a flow list [a, b]."""
    result = {}
    current = None
    for raw in text.splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        if raw[0] not in (" ", "\t"):
            head = raw.strip()
            if head.endswith(":"):
                current = {}
                result[head[:-1].strip()] = current
            elif ":" in head:
                k, v = head.split(":", 1)
                result[k.strip()] = _parse_value(v)
                current = None
            continue
        if current is not None and ":" in raw:
            k, v = raw.split(":", 1)
            current[k.strip()] = _parse_value(v)
    return result


def parse(text):
    try:
        import yaml  # type: ignore

        return yaml.safe_load(text) or {}
    except ImportError:
        return _mini_parse(text)


def load(explicit=None, allow_example=True):
    """Return (data, path). Prefer config.yml; fall back to the example only
    when allow_example is True (used for the non-secret funding default)."""
    if explicit:
        p = Path(explicit)
    elif CONFIG.is_file():
        p = CONFIG
    elif allow_example and CONFIG_EXAMPLE.is_file():
        p = CONFIG_EXAMPLE
    else:
        return None, CONFIG
    if not p.is_file():
        return None, p
    return parse(p.read_text(encoding="utf-8")), p
