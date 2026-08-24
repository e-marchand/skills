#!/usr/bin/env python3
"""Detect public 4D class members that are missing from the Markdown documentation.

Convention in this repo:
  * Public classes  = ``.4dm`` files under ``Project/Sources/Classes`` whose name
    does NOT start with ``_`` (leading underscore = internal/private class).
  * Public members  = ``Function <name>`` declarations whose name does NOT start
    with ``_``. Computed properties (``Function get <name>`` / ``Function set
    <name>``) collapse to a single property ``<name>``. ``Class constructor`` is
    ignored.
  * Documentation   = ``Documentation/Classes/<ClassName>.md``. A member is
    considered documented when its name appears either as a ``### name`` heading
    or as a ``**name**`` bold token anywhere in that file.

Exit code is 0 when every public member is documented, 1 when at least one gap
(undocumented member or missing doc file) is found, so it can be used in CI.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# ``[modifiers] Function <rest>`` — modifiers such as server/shared/session/local/exposed.
_FUNCTION_RE = re.compile(r"^\s*(?:[A-Za-z]+\s+)*?Function\s+(?P<rest>\S.*)$")
# A computed-property accessor: ``get <name>`` / ``set <name>`` (name, not an opening paren).
_ACCESSOR_RE = re.compile(r"^(?P<kind>get|set)\s+(?P<name>[A-Za-z_][A-Za-z0-9_]*)")
# A plain method: ``<name>(`` (this also matches methods literally named get/set).
_METHOD_RE = re.compile(r"^(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*\(")


class Member:
    __slots__ = ("name", "kind", "line")

    def __init__(self, name: str, kind: str, line: int) -> None:
        self.name = name
        self.kind = kind  # "method" | "property"
        self.line = line


def extract_public_members(source: str) -> list[Member]:
    """Return the public methods/properties declared in a 4D class source."""
    members: dict[str, Member] = {}
    for lineno, raw in enumerate(source.splitlines(), start=1):
        m = _FUNCTION_RE.match(raw)
        if not m:
            continue
        rest = m.group("rest").strip()

        accessor = _ACCESSOR_RE.match(rest)
        if accessor:
            name, kind = accessor.group("name"), "property"
        else:
            method = _METHOD_RE.match(rest)
            if not method:
                continue
            name, kind = method.group("name"), "method"

        if name.startswith("_"):  # internal helper
            continue
        # First declaration wins (a get/set pair maps to one property entry).
        members.setdefault(name, Member(name, kind, lineno))
    return sorted(members.values(), key=lambda x: x.line)


def is_documented(name: str, doc: str) -> bool:
    """True when ``name`` is documented in the Markdown.

    Members are documented in three shapes in this repo, all accepted here:
      * ``### name`` / ``### name()`` headings (methods),
      * ``**name**`` bold signatures (methods),
      * ``` `name` ``` inline-code cells in a property table (computed properties).
    """
    escaped = re.escape(name)
    if re.search(r"\*\*" + escaped + r"\*\*", doc):
        return True
    if re.search(r"^###\s+" + escaped + r"\b", doc, re.MULTILINE):
        return True
    if re.search(r"`" + escaped + r"`", doc):
        return True
    return False


def scan(classes_dir: Path, docs_dir: Path) -> list[dict]:
    """Return one report entry per public class."""
    report: list[dict] = []
    for class_file in sorted(classes_dir.glob("*.4dm")):
        stem = class_file.stem
        if stem.startswith("_"):
            continue

        members = extract_public_members(class_file.read_text(encoding="utf-8"))
        doc_file = docs_dir / f"{stem}.md"
        doc_exists = doc_file.exists()
        doc_text = doc_file.read_text(encoding="utf-8") if doc_exists else ""

        missing = [
            {"name": mbr.name, "kind": mbr.kind, "line": mbr.line}
            for mbr in members
            if not (doc_exists and is_documented(mbr.name, doc_text))
        ]

        report.append(
            {
                "class": stem,
                "source": str(class_file),
                "doc": str(doc_file),
                "doc_exists": doc_exists,
                "public_members": len(members),
                "missing": missing,
            }
        )
    return report


def render_text(report: list[dict]) -> tuple[str, int]:
    """Return a human-readable report and the number of gaps found."""
    lines: list[str] = []
    total_missing = 0
    total_members = 0

    for entry in report:
        total_members += entry["public_members"]
        gaps = entry["missing"]
        if not entry["doc_exists"]:
            total_missing += len(gaps)
            lines.append(f"✗ {entry['class']}: NO documentation file ({entry['doc']})")
            for g in gaps:
                lines.append(f"    - {g['name']} ({g['kind']}, line {g['line']})")
            continue
        if gaps:
            total_missing += len(gaps)
            lines.append(f"✗ {entry['class']}: {len(gaps)} undocumented member(s)")
            for g in gaps:
                lines.append(f"    - {g['name']} ({g['kind']}, line {g['line']})")
        else:
            lines.append(f"✓ {entry['class']}: all {entry['public_members']} public member(s) documented")

    header = (
        f"Documentation coverage: {total_members - total_missing}/{total_members} "
        f"public member(s) documented across {len(report)} class(es)."
    )
    lines.append("")
    lines.append(header)
    return "\n".join(lines), total_missing


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="Repository root (default: cwd).")
    parser.add_argument(
        "--classes-dir",
        type=Path,
        default=None,
        help="Override the classes directory (default: <root>/Project/Sources/Classes).",
    )
    parser.add_argument(
        "--docs-dir",
        type=Path,
        default=None,
        help="Override the docs directory (default: <root>/Documentation/Classes).",
    )
    parser.add_argument("--json", action="store_true", help="Emit the report as JSON.")
    args = parser.parse_args(argv)

    classes_dir = args.classes_dir or (args.root / "Project" / "Sources" / "Classes")
    docs_dir = args.docs_dir or (args.root / "Documentation" / "Classes")

    if not classes_dir.is_dir():
        print(f"error: classes directory not found: {classes_dir}", file=sys.stderr)
        return 2

    report = scan(classes_dir, docs_dir)

    if args.json:
        gaps = sum(len(e["missing"]) for e in report)
        print(json.dumps({"gaps": gaps, "classes": report}, indent=2))
        return 1 if gaps else 0

    text, gaps = render_text(report)
    print(text)
    return 1 if gaps else 0


if __name__ == "__main__":
    raise SystemExit(main())
