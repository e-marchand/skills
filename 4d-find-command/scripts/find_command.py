#!/usr/bin/env python3
"""
Find 4D commands matching a search term.

Usage:
  python3 find_command.py <search_term> [--verbose] [--summary]

Examples:
  python3 find_command.py json
  python3 find_command.py json --verbose
  python3 find_command.py "file" --summary
  python3 find_command.py selection
"""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path


TYPE_MAP = {
    "R": "Real",
    "L": "Integer",
    "S": "String",
    "B": "Boolean",
    "D": "Date",
    "T": "Time",
    "H": "Time",
    "o": "Object",
    "j": "Collection",
    "E": "Expression",
    "a": "Text",
    "a80": "Text",
    "a3": "Text",
    "A": "Text",
    "P": "Picture",
    "V": "Variant",
    "v": "Pointer",
    "C": "Field",
    "F": "Table",
    "Y": "Variable",
    "y": "NumericField",
    "X": "",
}


CATEGORY_MAP = {
    "1": "Application",
    "2": "Arrays",
    "3": "Blobs",
    "4": "Boolean",
    "6": "Communications",
    "7": "Compiler",
    "8": "Data Entry",
    "9": "Date and Time",
    "11": "Entry Control",
    "12": "Interruptions",
    "13": "Listbox",
    "15": "Hierarchical Lists",
    "16": "Import Export",
    "17": "Errors",
    "18": "Language",
    "19": "Math",
    "20": "Menus",
    "21": "Messages",
    "23": "Objects (Forms)",
    "24": "Statistics",
    "25": "Users and Groups",
    "26": "Pictures",
    "27": "Printing",
    "30": "Process",
    "31": "Record Locking",
    "32": "Records",
    "33": "Relations",
    "34": "Resources",
    "35": "Queries",
    "37": "Selection",
    "38": "Sets",
    "39": "String",
    "40": "Structure",
    "42": "System Documents",
    "43": "System Environment",
    "45": "SQL",
    "48": "User Interface",
    "49": "Variables",
    "50": "Web Server",
    "51": "Windows",
    "54": "Quick Reports",
    "56": "Formulas",
    "59": "System",
    "60": "Backup",
    "61": "Forms",
    "62": "Web Area",
    "63": "XML DOM",
    "64": "XML SAX",
    "68": "Design Object Access",
    "71": "JSON",
    "72": "Objects",
    "73": "Styled Text",
    "74": "Write Pro",
    "76": "Cache",
    "77": "Collections",
    "80": "License",
    "81": "FileHandle",
}


SEARCH_PATHS = [
    Path.home() / "Library/Application Support/Code/User/globalStorage/4d.4d-analyzer/tool4d",
    Path.home() / "Library/Application Support/Antigravity/User/globalStorage/4d.4d-analyzer/tool4d",
]


@dataclass(frozen=True)
class CommandEntry:
    name: str
    category: str
    signature: str
    summary: str
    details: tuple[str, ...]


@dataclass(frozen=True)
class ParamSpec:
    names: tuple[str, ...]
    types: tuple[str, ...]

    def type_for(self, token: str) -> str:
        normalized = normalize_whitespace(token)

        if len(self.names) == len(self.types):
            for name, type_name in zip(self.names, self.types):
                if normalize_whitespace(name) == normalized:
                    return type_name

        if normalized == "*" and "Operator" in self.types:
            return "Operator"

        if len(self.types) == 1:
            return self.types[0]

        for type_name in self.types:
            if type_name != "Operator":
                return type_name

        return self.types[0] if self.types else ""


@dataclass(frozen=True)
class ParamDoc:
    name: str
    type_name: str
    direction: str
    description: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="find_command.py",
        description="Find 4D commands matching a search term.",
    )
    parser.add_argument("search_term", help="Command name or keyword to search for")
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Add category, summary, and parameter details for each command",
    )
    parser.add_argument(
        "--summary",
        action="store_true",
        help="Include command summary lines without enabling verbose mode",
    )
    return parser.parse_args()


def normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text.replace("\xa0", " ")).strip()


def clean_summary(text: str) -> str:
    text = text.replace("<br/>", " ")
    text = re.sub(r"</?[^>]+>", " ", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    text = re.sub(r"\*([^*]+)\*", r"\1", text)
    return normalize_whitespace(text)


def clean_syntax(text: str) -> str:
    text = text.replace("<br/>", "\n")
    lines = []
    for raw_line in text.splitlines():
        line = normalize_whitespace(raw_line.replace("**", "").replace("*", ""))
        if line:
            lines.append(line)
    return "\n".join(lines)


def command_name_from_signature(signature: str) -> str:
    command_name = re.split(r"\s+\(", signature, maxsplit=1)[0]
    command_name = re.split(r"\s+->", command_name, maxsplit=1)[0]
    return command_name.strip()


def parse_params(params: str) -> str:
    params = params.split("//", 1)[0].strip()
    if not params or params == "X":
        return "()"

    parsed: list[str] = []
    for part in params.split(";"):
        part = part.strip()
        if not part or re.fullmatch(r"[X*|{}()]", part):
            continue

        optional = part.endswith("'")
        if optional:
            part = part[:-1]

        match = re.match(r"[A-Za-z0-9]+", part)
        if not match:
            continue

        type_name = TYPE_MAP.get(match.group(0), match.group(0))
        if type_name:
            suffix = "?" if optional else ""
            parsed.append(f"{type_name}{suffix}")

    if not parsed:
        return "()"
    return f"({', '.join(parsed)})"


def natural_sort_key(path: Path) -> list[object]:
    return [int(part) if part.isdigit() else part.casefold() for part in re.split(r"(\d+)", str(path))]


def find_tool4d_app() -> Path | None:
    if "TOOL4D" in os.environ:
        tool4d_env = Path(os.environ["TOOL4D"]).expanduser()
        if tool4d_env.is_file() and tool4d_env.name == "tool4d":
            app_path = tool4d_env.parents[2]
            if app_path.suffix == ".app":
                return app_path
        if tool4d_env.is_dir() and tool4d_env.suffix == ".app":
            return tool4d_env

    candidates: list[Path] = []
    for base_path in SEARCH_PATHS:
        if not base_path.is_dir():
            continue
        candidates.extend(base_path.glob("**/tool4d.app"))

    if not candidates:
        return None
    return sorted(candidates, key=natural_sort_key)[-1]


def load_signatures(path: Path) -> dict[str, str]:
    if not path.is_file():
        return {}

    signatures: dict[str, str] = {}
    root = ET.parse(path).getroot()
    for unit in root.findall(".//trans-unit"):
        target = unit.find("target")
        if target is None:
            continue

        text = normalize_whitespace("".join(target.itertext()))
        if not text:
            continue

        name = command_name_from_signature(text)
        if name and name not in signatures:
            signatures[name] = text

    return signatures


def parse_param_specs(params: list[list[str]]) -> list[ParamSpec]:
    specs: list[ParamSpec] = []
    for row in params:
        if not row:
            continue

        raw_name = html.unescape(row[0] or "")
        raw_type = row[1] if len(row) > 1 else ""
        if not raw_name or raw_name == "Function result" or raw_name in {"->", "<-", "<->"}:
            continue

        names = tuple(normalize_whitespace(part) for part in raw_name.split("|"))
        if len(names) > 1:
            types = tuple(normalize_whitespace(part) for part in raw_type.split(",") if normalize_whitespace(part))
        else:
            normalized_type = normalize_whitespace(raw_type)
            types = (normalized_type,) if normalized_type else ()
        specs.append(ParamSpec(names=names, types=types))

    return specs


def parse_param_docs(params: list[list[str]]) -> tuple[str, ...]:
    docs: list[ParamDoc] = []

    for row in params:
        if not row:
            continue

        raw_name = html.unescape(row[0] or "")
        type_name = normalize_whitespace(row[1]) if len(row) > 1 else ""
        direction = normalize_whitespace(row[2]) if len(row) > 2 else ""
        description = clean_summary(row[3]) if len(row) > 3 else ""

        if raw_name in {"->", "<-", "<->"}:
            continue

        if not raw_name:
            if docs and description:
                previous = docs[-1]
                separator = "" if not previous.description or previous.description.endswith((".", "!", "?", ":")) else "."
                extra = f"{previous.description}{separator} {description}".strip()
                docs[-1] = ParamDoc(previous.name, previous.type_name, previous.direction, extra)
            continue

        name = normalize_whitespace(raw_name)
        if name == "Function result":
            name = "result"

        docs.append(ParamDoc(name=name, type_name=type_name, direction=direction, description=description))

    lines: list[str] = []
    for doc in docs:
        meta_parts = [part for part in [doc.type_name, doc.direction] if part]
        meta = f" [{', '.join(meta_parts)}]" if meta_parts else ""
        description = f": {doc.description}" if doc.description else ""
        lines.append(f"  {doc.name}{meta}{description}")

    return tuple(lines)


def extract_signature_param_names(signature: str) -> tuple[str, ...]:
    names: list[str] = []
    seen: set[str] = set()

    for line in signature.splitlines():
        if "(" not in line or ")" not in line:
            continue

        params_text = line.split("(", 1)[1].rsplit(")", 1)[0]
        for match in re.finditer(r"([A-Za-z_][A-Za-z0-9_]*)(?=\s*:)|(\*)(?=\s*[;)}])", params_text):
            token = match.group(1) or match.group(2)
            if token not in seen:
                seen.add(token)
                names.append(token)

    return tuple(names)


def align_detail_names(signature: str, details: tuple[str, ...]) -> tuple[str, ...]:
    signature_names = extract_signature_param_names(signature)
    if not signature_names:
        return details

    detail_infos: list[tuple[str, str]] = []
    for line in details:
        stripped = line.strip()
        if not stripped:
            continue
        name = stripped.split(" [", 1)[0].split(":", 1)[0].strip()
        detail_infos.append((name, line))

    non_result_names = [name for name, _ in detail_infos if name != "result"]
    if len(non_result_names) != len(signature_names):
        return details

    aligned: list[str] = []
    signature_iter = iter(signature_names)
    for name, line in detail_infos:
        if name == "result":
            aligned.append(line)
            continue

        target_name = next(signature_iter)
        if name == target_name:
            aligned.append(line)
        else:
            aligned.append(line.replace(f"  {name}", f"  {target_name}", 1))

    return tuple(aligned)


def build_typed_signature(raw_syntax: str, params: list[list[str]]) -> str:
    param_specs = parse_param_specs(params)
    signatures: list[str] = []

    for raw_line in raw_syntax.replace("<br/>", "\n").splitlines():
        line = normalize_whitespace(raw_line.replace("**", ""))
        if not line:
            continue

        if "(" not in line or ")" not in line or not param_specs:
            signatures.append(line.replace("*", ""))
            continue

        head, tail = line.split("(", 1)
        params_text, suffix = tail.rsplit(")", 1)

        token_pattern = re.compile(r"\*[^*]+\*|\*|[A-Za-z_][A-Za-z0-9_]*")
        rewritten: list[str] = []
        last_index = 0
        spec_index = 0

        for match in token_pattern.finditer(params_text):
            token = match.group(0)
            rewritten.append(params_text[last_index:match.start()])

            display_token = "*" if token == "*" else token.strip("*")
            replacement = display_token

            if spec_index < len(param_specs):
                type_name = param_specs[spec_index].type_for(display_token)
                if display_token != "*" and type_name and type_name != "Operator":
                    replacement = f"{display_token} : {type_name}"
                spec_index += 1

            rewritten.append(replacement)
            last_index = match.end()

        rewritten.append(params_text[last_index:])
        typed_params = "".join(rewritten).strip()
        signatures.append(f"{head.strip()} ( {typed_params} ){suffix}")

    return "\n".join(signatures)


def syntax_already_typed(raw_syntax: str) -> bool:
    cleaned = clean_syntax(raw_syntax)
    if not cleaned:
        return False
    return bool(re.search(r"\(\s*[^)]*\b[A-Za-z_][A-Za-z0-9_]*\s*:\s*[^)]+", cleaned))


def load_command_metadata(path: Path) -> tuple[dict[str, str], dict[str, str], dict[str, tuple[str, ...]]]:
    if not path.is_file():
        return {}, {}, {}

    with path.open(encoding="utf-8") as handle:
        payload = json.load(handle)

    signatures: dict[str, str] = {}
    summaries: dict[str, str] = {}
    details: dict[str, tuple[str, ...]] = {}
    for name, entry in payload.get("_command_", {}).items():
        syntax = entry.get("Syntax", "")
        params = entry.get("Params", [])
        if syntax:
            if syntax_already_typed(syntax):
                signatures[name] = clean_syntax(syntax)
            else:
                signatures[name] = build_typed_signature(syntax, params)

        summary = clean_summary(entry.get("Summary", ""))
        if summary:
            summaries[name] = summary

        param_details = parse_param_docs(params)
        if param_details:
            details[name] = param_details

    return signatures, summaries, details


def build_fallback_signature(name: str, params: str, return_type: str) -> str:
    signature = f"{name}{parse_params(params)}"
    if return_type:
        signature = f"{signature} -> {TYPE_MAP.get(return_type, return_type)}"
    return signature


def parse_gram_line(line: str) -> tuple[str, str, str, str]:
    match = re.match(r"^([A-Za-z0-9]+)\s+<==(.+)$", line)
    if match:
        return_type, rest = match.groups()
    else:
        return_type, rest = "", line

    parts = [part.strip() for part in rest.split(":")]
    command_name = parts[0].split(",", 1)[0].strip()
    category = parts[1] if len(parts) > 1 else ""
    params = ":".join(parts[2:]) if len(parts) > 2 else ""
    return command_name, category, params, return_type


def iter_matching_commands(
    syntax_file: Path,
    search_re: re.Pattern[str],
    signatures: dict[str, str],
    summaries: dict[str, str],
    details: dict[str, tuple[str, ...]],
) -> list[CommandEntry]:
    results: dict[str, CommandEntry] = {}

    with syntax_file.open(encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line:
                continue
            if line.startswith("@") or line.startswith("_O_") or "_O_" in line or line.startswith("_4D"):
                continue
            if not re.match(r"^[A-Za-z]", line):
                continue
            if not search_re.search(line):
                continue

            name, category, params, return_type = parse_gram_line(line)
            if not name:
                continue

            signature = signatures.get(name)
            if not signature:
                signature = build_fallback_signature(name, params, return_type)

            entry = CommandEntry(
                name=name,
                category=CATEGORY_MAP.get(category, f"Category {category}" if category else "Unknown"),
                signature=signature,
                summary=summaries.get(name, ""),
                details=details.get(name, ()),
            )
            results[signature.casefold()] = entry

    return sorted(results.values(), key=lambda entry: entry.signature.casefold())


def format_entry(entry: CommandEntry, verbose: bool, include_summary: bool) -> str:
    signature_lines = entry.signature.splitlines() or [entry.signature]
    if verbose:
        signature_lines[0] = f"{signature_lines[0]} [{entry.category}]"

    line = "\n".join(signature_lines)

    extra_lines: list[str] = []
    if include_summary and entry.summary:
        extra_lines.append(f"  {entry.summary}")
    if verbose and entry.details:
        extra_lines.extend(align_detail_names(entry.signature, entry.details))

    if extra_lines:
        return f"{line}\n" + "\n".join(extra_lines)
    return line


def compile_search_pattern(search_term: str) -> re.Pattern[str]:
    try:
        return re.compile(search_term, re.IGNORECASE)
    except re.error:
        return re.compile(re.escape(search_term), re.IGNORECASE)


def main() -> int:
    args = parse_args()

    tool4d_app = find_tool4d_app()
    if tool4d_app is None:
        print("Error: tool4d.app not found", file=sys.stderr)
        print("Install 4D-Analyzer extension in VS Code or Antigravity", file=sys.stderr)
        return 1

    resources_dir = tool4d_app / "Contents/Resources"
    syntax_file = resources_dir / "gram.4dsyntax"
    syntax_xlf = resources_dir / "en.lproj/4DSyntaxEN.xlf"
    syntax_json = resources_dir / "en.lproj/syntaxEN.json"

    if not syntax_file.is_file():
        print(f"Error: gram.4dsyntax not found at {syntax_file}", file=sys.stderr)
        return 1

    fallback_signatures = load_signatures(syntax_xlf)
    typed_signatures, summaries, details = load_command_metadata(syntax_json)
    search_re = compile_search_pattern(args.search_term)
    include_summary = args.verbose or args.summary

    signatures = {**fallback_signatures, **typed_signatures}
    matches = iter_matching_commands(syntax_file, search_re, signatures, summaries, details)
    for entry in matches:
        print(format_entry(entry, verbose=args.verbose, include_summary=include_summary))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
