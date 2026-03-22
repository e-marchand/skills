#!/usr/bin/env python3
"""Analyze a 4D project and produce a structured summary."""

import argparse
import json
import os
import re
import sys
from pathlib import Path

MAX_PROJECT_CANDIDATES = 20
MAX_CANDIDATE_SEARCH_DEPTH = 3
GUIDE_SECTION_BEGIN = "<!-- BEGIN 4D PROJECT INFO -->"
GUIDE_SECTION_END = "<!-- END 4D PROJECT INFO -->"
POINTER_SECTION_BEGIN = "<!-- BEGIN 4D PROJECT INFO POINTER -->"
POINTER_SECTION_END = "<!-- END 4D PROJECT INFO POINTER -->"
AGENTS_TEMPLATE_PLACEHOLDER = "{{4D_PROJECT_INFO_SECTION}}"
CLAUDE_TEMPLATE_PLACEHOLDER = "{{4D_PROJECT_INFO_POINTER}}"
PREVIEW_LIMIT = 8
GUIDANCE_METHOD_LIMIT = 30
GUIDANCE_METHOD_PATTERN_LIMIT = 10
GUIDANCE_METHOD_PATTERN_MIN_COUNT = 5


def get_project_file(project_dir: Path) -> Path | None:
    """Return the first .4DProject file in a Project directory."""
    if not project_dir.is_dir():
        return None
    for file_path in sorted(project_dir.glob("*.4DProject")):
        if file_path.is_file():
            return file_path
    return None


def find_project_root(start_path: str) -> Path | None:
    """Resolve a 4D project root from a project root, Project dir, or .4DProject file."""
    path = Path(start_path).expanduser().resolve()

    if path.is_file():
        if path.suffix == ".4DProject" and path.parent.name == "Project":
            return path.parent.parent
        path = path.parent

    if path.name == "Project" and get_project_file(path):
        return path.parent

    if get_project_file(path / "Project"):
        return path

    for directory in [path, *path.parents]:
        project_dir = directory / "Project"
        if get_project_file(project_dir):
            return directory
    return None


def find_project_candidates(start_path: str, limit: int = MAX_PROJECT_CANDIDATES) -> list[str]:
    """Find nearby .4DProject files to help the next run target one explicitly."""
    path = Path(start_path).expanduser().resolve()
    search_root = path.parent if path.is_file() else path

    if not search_root.exists():
        return []

    candidates = []
    seen = set()
    try:
        scopes = [search_root, *list(search_root.parents)[:2]]
        for scope in scopes:
            for project_file in sorted(find_project_files_bounded(scope, MAX_CANDIDATE_SEARCH_DEPTH)):
                if not project_file.is_file():
                    continue
                project_str = str(project_file)
                if project_str in seen:
                    continue
                seen.add(project_str)
                candidates.append(project_str)
                if len(candidates) >= limit:
                    return candidates
            if candidates:
                return candidates
    except Exception:
        return candidates

    return candidates


def find_project_files_bounded(root: Path, max_depth: int) -> list[Path]:
    """Find .4DProject files without traversing large ancestor trees indefinitely."""
    if not root.exists():
        return []

    project_files = []
    root_depth = len(root.parts)
    for current_root, dirnames, filenames in os.walk(root):
        current_path = Path(current_root)
        depth = len(current_path.parts) - root_depth
        if depth >= max_depth:
            dirnames[:] = []
        for filename in filenames:
            if filename.endswith(".4DProject"):
                project_files.append(current_path / filename)
    return project_files


def count_files(directory: Path, extension: str) -> list[str]:
    """Return list of file stems matching extension."""
    if not directory.exists():
        return []
    return sorted(f.stem for f in directory.rglob(f"*{extension}") if f.is_file())


def analyze_method(filepath: Path) -> dict:
    """Extract basic info from a .4dm file."""
    try:
        content = filepath.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return {"name": filepath.stem, "lines": 0}
    lines = content.splitlines()
    return {
        "name": filepath.stem,
        "lines": len(lines),
    }


def analyze_class(filepath: Path) -> dict:
    """Extract class info: properties, functions, extends."""
    try:
        content = filepath.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return {"name": filepath.stem, "lines": 0, "properties": [], "functions": [], "extends": None}

    lines = content.splitlines()
    props = []
    funcs = []
    extends = None

    for line in lines:
        stripped = line.strip()
        match = re.match(r"Class\s+extends\s+(.+)", stripped, re.IGNORECASE)
        if match:
            extends = match.group(1).strip()

        match = re.match(r"property\s+(.+)", stripped, re.IGNORECASE)
        if match:
            props.append(match.group(1).strip())

        match = re.match(r"(exposed\s+)?(shared\s+)?Function\s+(\w[\w.]*)", stripped, re.IGNORECASE)
        if match:
            prefix = ""
            if match.group(1):
                prefix += "exposed "
            if match.group(2):
                prefix += "shared "
            funcs.append(f"{prefix}{match.group(3)}")

    return {
        "name": filepath.stem,
        "lines": len(lines),
        "properties": props,
        "functions": funcs,
        "extends": extends,
    }


def analyze_dependencies(project_root: Path) -> dict:
    """Parse dependencies.json."""
    dep_file = project_root / "Project" / "Sources" / "dependencies.json"
    if not dep_file.exists():
        return {"file_exists": False, "dependencies": {}}
    try:
        data = json.loads(dep_file.read_text())
        return {"file_exists": True, "dependencies": data.get("dependencies", {})}
    except Exception as exc:
        return {"file_exists": True, "error": str(exc)}


def analyze_forms(sources_dir: Path) -> list[dict]:
    """List forms and their basic info."""
    forms_dir = sources_dir / "Forms"
    if not forms_dir.exists():
        return []
    forms = []
    for form_dir in sorted(forms_dir.iterdir()):
        if form_dir.is_dir():
            form_file = form_dir / "form.4DForm"
            info = {"name": form_dir.name, "has_form_file": form_file.exists()}
            if form_file.exists():
                try:
                    data = json.loads(form_file.read_text())
                    pages = data.get("pages", [])
                    if isinstance(pages, list):
                        info["pages"] = len(pages)
                    elif isinstance(pages, dict):
                        info["pages"] = len(pages.keys())
                    else:
                        info["pages"] = 0
                except Exception:
                    pass
            methods = sorted(m.stem for m in form_dir.glob("*.4dm"))
            if methods:
                info["methods"] = methods
            forms.append(info)
    return forms


def analyze_settings(project_root: Path) -> dict:
    """Extract key project settings from .4DProject and settings.4DSettings."""
    result = {}
    project_dir = project_root / "Project"
    project_file = get_project_file(project_dir)
    if project_file:
        try:
            data = json.loads(project_file.read_text())
            result["project_file"] = project_file.name
            result["compatibility_version"] = data.get("compatibilityVersion")
            result["tokenized_text"] = data.get("tokenizedText")
        except Exception:
            pass

    result["has_settings"] = (project_dir / "Sources" / "settings.4DSettings").exists()
    return result


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "path",
        nargs="?",
        default=os.getcwd(),
        help="Path inside a 4D project, the project root, Project/, or a .4DProject file",
    )
    parser.add_argument("--compact", action="store_true", help="Return compact JSON with names and counts instead of full details")
    parser.add_argument("--sync-guidance", action="store_true", help="Create or refresh AGENTS.md guidance for a valid 4D project")
    parser.add_argument(
        "--format",
        default="json",
        help="Output format: json, human, or terse (aliases: text, token, tokens, toon)",
    )
    return parser.parse_args()


def normalize_output_format(value: str) -> str:
    """Normalize format aliases to canonical output modes."""
    normalized = value.strip().lower()
    aliases = {
        "json": "json",
        "human": "human",
        "text": "human",
        "terse": "terse",
        "token": "terse",
        "tokens": "terse",
        "toon": "terse",
    }
    if normalized not in aliases:
        raise ValueError(f"Unsupported format: {value}")
    return aliases[normalized]


def format_dependencies_human(dependencies: dict) -> str:
    """Render dependencies in a concise human-readable form."""
    if not dependencies.get("file_exists"):
        return "none"
    if "error" in dependencies:
        return f"error: {dependencies['error']}"
    deps = dependencies.get("dependencies", {})
    if not deps:
        return "none"
    rendered = []
    for name, config in sorted(deps.items()):
        if isinstance(config, dict):
            source = config.get("github") or config.get("url") or "local"
            version = config.get("tag") or config.get("version")
            rendered.append(f"{name} ({source}{' @ ' + version if version else ''})")
        else:
            rendered.append(f"{name} ({config})")
    return ", ".join(rendered)


def build_architecture(root: Path) -> dict:
    """Return canonical source locations for a 4D project."""
    paths = {
        "project": "Project/",
        "project_file": f"Project/{get_project_file(root / 'Project').name}" if get_project_file(root / "Project") else "Project/*.4DProject",
        "methods": "Project/Sources/Methods/",
        "classes": "Project/Sources/Classes/",
        "database_methods": "Project/Sources/DatabaseMethods/",
        "forms": "Project/Sources/Forms/",
    }
    return {
        name: {
            "path": path,
            "exists": (root / path.rstrip("/")).exists() if "*" not in path else bool(get_project_file(root / "Project")),
        }
        for name, path in paths.items()
    }


def build_guidance_status(root: Path | None = None) -> dict:
    """Return AGENTS.md/CLAUDE.md status."""
    guidance = {
        "canonical": "AGENTS.md",
        "agents_exists": False,
        "claude_exists": False,
        "synced": False,
        "updated_files": [],
    }
    if root is None:
        return guidance
    guidance["agents_exists"] = (root / "AGENTS.md").exists()
    guidance["claude_exists"] = (root / "CLAUDE.md").exists()
    return guidance


def preview_names(names: list[str], limit: int = PREVIEW_LIMIT) -> str:
    """Return a concise preview list."""
    if not names:
        return "none"
    preview = ", ".join(names[:limit])
    remaining = len(names) - limit
    if remaining > 0:
        preview += f", +{remaining} more"
    return preview


def get_name_glob_pattern(name: str) -> str | None:
    """Return a simple glob-style prefix pattern for underscore-delimited names."""
    if "_" not in name:
        return None
    prefix = name.split("_", 1)[0]
    if not prefix:
        return None
    return f"{prefix}_*"


def summarize_guidance_methods(names: list[str]) -> str:
    """Return a compact method preview for AGENTS.md."""
    filtered = [name for name in names if not name.upper().startswith("COMPILER_")]
    if len(filtered) <= GUIDANCE_METHOD_LIMIT:
        return preview_names(filtered, GUIDANCE_METHOD_LIMIT)

    pattern_names: dict[str, list[str]] = {}
    pattern_order: list[str] = []
    for name in filtered:
        pattern = get_name_glob_pattern(name)
        if not pattern:
            continue
        if pattern not in pattern_names:
            pattern_names[pattern] = []
            pattern_order.append(pattern)
        pattern_names[pattern].append(name)

    selected_patterns = [
        pattern
        for pattern in pattern_order
        if len(pattern_names[pattern]) >= GUIDANCE_METHOD_PATTERN_MIN_COUNT
    ][:GUIDANCE_METHOD_PATTERN_LIMIT]
    if not selected_patterns:
        return preview_names(filtered, GUIDANCE_METHOD_LIMIT)

    represented_names = {name for pattern in selected_patterns for name in pattern_names[pattern]}
    parts = []
    represented_count = 0
    added_patterns: set[str] = set()

    for name in filtered:
        pattern = get_name_glob_pattern(name)
        if pattern in selected_patterns:
            if pattern in added_patterns:
                continue
            parts.append(pattern)
            represented_count += len(pattern_names[pattern])
            added_patterns.add(pattern)
        else:
            parts.append(name)
            represented_count += 1
        if len(parts) >= GUIDANCE_METHOD_LIMIT:
            break

    remaining = len(filtered) - represented_count
    if remaining > 0:
        parts.append(f"+{remaining} more")
    return ", ".join(parts) if parts else "none"


def build_compact_report(report: dict, methods: list[dict], classes: list[dict], forms: list[dict]) -> dict:
    """Return the compact JSON representation."""
    return {
        "project_root": report["project_root"],
        "settings": report["settings"],
        "summary": report["summary"],
        "architecture": report["architecture"],
        "guidance": report["guidance"],
        "method_names": [m["name"] for m in methods],
        "class_names": [c["name"] for c in classes],
        "form_names": [f["name"] for f in forms],
    }


def render_human(report: dict, compact: dict) -> str:
    """Render a readable multiline summary."""
    settings = compact["settings"]
    summary = compact["summary"]
    guidance = compact["guidance"]
    lines = [
        f"Project: {compact['project_root']}",
        f"Project file: {settings.get('project_file', 'unknown')}",
        f"Compatibility: {settings.get('compatibility_version', 'unknown')}",
        f"Tokenized text: {'yes' if settings.get('tokenized_text') else 'no'}",
        f"Settings file: {'yes' if settings.get('has_settings') else 'no'}",
        f"Summary: methods={summary['methods_count']}, classes={summary['classes_count']}, forms={summary['forms_count']}, db_methods={len(summary['database_methods'])}, catalog={'yes' if summary['has_catalog'] else 'no'}, code_lines={summary['total_code_lines']}",
        f"Dependencies: {format_dependencies_human(summary['dependencies'])}",
        f"Methods path: {compact['architecture']['methods']['path']}",
        f"Classes path: {compact['architecture']['classes']['path']}",
        f"Database methods path: {compact['architecture']['database_methods']['path'] if compact['architecture']['database_methods']['exists'] else 'not present'}",
        f"Forms path: {compact['architecture']['forms']['path'] if compact['architecture']['forms']['exists'] else 'not present'}",
        f"Guidance: canonical={guidance['canonical']} agents={'yes' if guidance['agents_exists'] else 'no'} claude={'yes' if guidance['claude_exists'] else 'no'} synced={'yes' if guidance['synced'] else 'no'}",
        f"Database methods: {', '.join(summary['database_methods']) if summary['database_methods'] else 'none'}",
        f"Methods: {preview_names(compact['method_names'])}",
        f"Classes: {preview_names(compact['class_names'])}",
        f"Forms: {preview_names(compact['form_names'])}",
    ]
    return "\n".join(lines)


def render_terse(compact: dict) -> str:
    """Render a token-light summary."""
    settings = compact["settings"]
    summary = compact["summary"]
    guidance = compact["guidance"]
    db_methods = ",".join(summary["database_methods"]) if summary["database_methods"] else "-"
    methods = ",".join(compact["method_names"][:PREVIEW_LIMIT]) if compact["method_names"] else "-"
    classes = ",".join(compact["class_names"][:PREVIEW_LIMIT]) if compact["class_names"] else "-"
    forms = ",".join(compact["form_names"][:PREVIEW_LIMIT]) if compact["form_names"] else "-"
    deps = format_dependencies_human(summary["dependencies"])
    return "\n".join(
        [
            f"root={compact['project_root']}",
            f"project={settings.get('project_file', '?')} compat={settings.get('compatibility_version', '?')} tokenized={1 if settings.get('tokenized_text') else 0} settings={1 if settings.get('has_settings') else 0}",
            f"counts m={summary['methods_count']} c={summary['classes_count']} f={summary['forms_count']} db={len(summary['database_methods'])} catalog={1 if summary['has_catalog'] else 0} lines={summary['total_code_lines']}",
            f"paths methods={compact['architecture']['methods']['path']} classes={compact['architecture']['classes']['path']} db={compact['architecture']['database_methods']['path'] if compact['architecture']['database_methods']['exists'] else '-'} forms={compact['architecture']['forms']['path'] if compact['architecture']['forms']['exists'] else '-'}",
            f"guide agents={1 if guidance['agents_exists'] else 0} claude={1 if guidance['claude_exists'] else 0} synced={1 if guidance['synced'] else 0}",
            f"db_methods={db_methods}",
            f"methods={methods}",
            f"classes={classes}",
            f"forms={forms}",
            f"deps={deps}",
        ]
    )


def build_non_project_hints() -> dict:
    """Return likely 4D locations for the next run."""
    return {
        "project_file": "Project/*.4DProject",
        "methods": "Project/Sources/Methods/*.4dm",
        "classes": "Project/Sources/Classes/*.4dm",
        "database_methods": "Project/Sources/DatabaseMethods/*.4dm",
        "forms": "Project/Sources/Forms/*/form.4DForm",
    }


def render_error(error: dict, output_format: str) -> str:
    """Render error payload in the requested format."""
    if output_format == "json":
        return json.dumps(error, indent=2)

    lines = [
        error["error"],
        f"searched_from: {error['searched_from']}",
        error["message"],
    ]
    candidates = error.get("project_candidates", [])
    if candidates:
        lines.append("project_candidates:")
        lines.extend(candidates)
    else:
        lines.append("project_candidates: none")
    hints = error.get("next_run_hints", {})
    if hints:
        lines.append("likely_4d_paths:")
        for key, value in hints.items():
            lines.append(f"{key}: {value}")
    if error.get("project_candidates_truncated"):
        lines.append("project_candidates_truncated: true")
    return "\n".join(lines)


def replace_or_append_block(text: str, begin_marker: str, end_marker: str, block: str) -> str:
    """Replace a managed block or append it if missing."""
    pattern = re.compile(re.escape(begin_marker) + r".*?" + re.escape(end_marker), re.DOTALL)
    if pattern.search(text):
        updated = pattern.sub(block, text, count=1)
    else:
        stripped = text.rstrip()
        updated = f"{stripped}\n\n{block}\n" if stripped else f"{block}\n"
    return updated


def get_agents_template() -> str:
    """Load the AGENTS.md template."""
    template_path = Path(__file__).resolve().parent.parent / "assets" / "AGENTS.md.template"
    try:
        template = template_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        template = "# Agent Guide\n\n" + AGENTS_TEMPLATE_PLACEHOLDER + "\n"
    if AGENTS_TEMPLATE_PLACEHOLDER not in template:
        template = template.rstrip() + "\n\n" + AGENTS_TEMPLATE_PLACEHOLDER + "\n"
    return template


def get_claude_template() -> str:
    """Load the CLAUDE.md template."""
    template_path = Path(__file__).resolve().parent.parent / "assets" / "CLAUDE.md.template"
    try:
        template = template_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        template = CLAUDE_TEMPLATE_PLACEHOLDER + "\n"
    if CLAUDE_TEMPLATE_PLACEHOLDER not in template:
        template = template.rstrip() + "\n\n" + CLAUDE_TEMPLATE_PLACEHOLDER + "\n"
    return template


def render_agents_block(compact: dict) -> str:
    """Render the managed AGENTS.md section."""
    settings = compact["settings"]
    summary = compact["summary"]
    architecture = compact["architecture"]
    project_file_path = architecture["project_file"]["path"]
    forms_hint = "Project/Sources/Forms/*/form.4DForm + optional *.4dm, ObjectMethods/*.4dm"
    lines = [
        GUIDE_SECTION_BEGIN,
        "## 4D Project",
        "",
        "This repository is a 4D project.",
        f"- Project file: `{project_file_path}`",
        f"- Methods ({architecture['methods']['path']}*.4dm): {summarize_guidance_methods(compact['method_names'])}",
        f"- Classes ({architecture['classes']['path']}*.4dm): {preview_names(compact['class_names'])}",
    ]
    if architecture["database_methods"]["exists"]:
        lines.append(
            f"- Database methods ({architecture['database_methods']['path']}*.4dm): {preview_names(summary['database_methods'])}"
        )
    if architecture["forms"]["exists"]:
        lines.append(f"- Forms ({forms_hint}): {preview_names(compact['form_names'])}")
    lines.extend(
        [
            f"- Counts: methods={summary['methods_count']}, classes={summary['classes_count']}, forms={summary['forms_count']}, db_methods={len(summary['database_methods'])}",
            f"- Dependencies: {format_dependencies_human(summary['dependencies'])}",
        ]
    )
    lines.append(GUIDE_SECTION_END)
    return "\n".join(lines)


def render_claude_pointer_block() -> str:
    """Render the managed CLAUDE.md pointer block."""
    return "\n".join(
        [
            POINTER_SECTION_BEGIN,
            "Read `AGENTS.md` first for project guidance.",
            POINTER_SECTION_END,
        ]
    )


def write_text_if_changed(path: Path, content: str) -> bool:
    """Write text only when content changes."""
    existing = None
    if path.exists():
        existing = path.read_text(encoding="utf-8")
    if existing == content:
        return False
    path.write_text(content, encoding="utf-8")
    return True


def sync_guidance_files(root: Path, compact: dict) -> dict:
    """Create or refresh AGENTS.md and CLAUDE.md pointer blocks."""
    agents_path = root / "AGENTS.md"
    claude_path = root / "CLAUDE.md"
    updated_files = []

    agents_block = render_agents_block(compact)
    if agents_path.exists():
        agents_content = replace_or_append_block(
            agents_path.read_text(encoding="utf-8"),
            GUIDE_SECTION_BEGIN,
            GUIDE_SECTION_END,
            agents_block,
        )
    else:
        agents_content = get_agents_template().replace(AGENTS_TEMPLATE_PLACEHOLDER, agents_block)
    if write_text_if_changed(agents_path, agents_content):
        updated_files.append("AGENTS.md")

    claude_block = render_claude_pointer_block()
    if claude_path.exists():
        claude_content = replace_or_append_block(
            claude_path.read_text(encoding="utf-8"),
            POINTER_SECTION_BEGIN,
            POINTER_SECTION_END,
            claude_block,
        )
    else:
        claude_content = get_claude_template().replace(CLAUDE_TEMPLATE_PLACEHOLDER, claude_block)
    if write_text_if_changed(claude_path, claude_content):
        updated_files.append("CLAUDE.md")

    guidance = build_guidance_status(root)
    guidance["synced"] = True
    guidance["updated_files"] = updated_files
    return guidance


def build_report(root: Path) -> tuple[dict, dict]:
    """Build full and compact reports for a resolved 4D project root."""
    sources_dir = root / "Project" / "Sources"
    methods_dir = sources_dir / "Methods"
    classes_dir = sources_dir / "Classes"
    database_methods_dir = sources_dir / "DatabaseMethods"

    methods = [analyze_method(path) for path in sorted(methods_dir.glob("*.4dm"))] if methods_dir.exists() else []
    classes = [analyze_class(path) for path in sorted(classes_dir.glob("*.4dm"))] if classes_dir.exists() else []
    db_methods = count_files(database_methods_dir, ".4dm") if database_methods_dir.exists() else []
    forms = analyze_forms(sources_dir)
    deps = analyze_dependencies(root)
    settings = analyze_settings(root)
    total_lines = sum(method.get("lines", 0) for method in methods) + sum(cls.get("lines", 0) for cls in classes)

    report = {
        "project_root": str(root),
        "settings": settings,
        "summary": {
            "methods_count": len(methods),
            "classes_count": len(classes),
            "forms_count": len(forms),
            "database_methods": db_methods,
            "has_catalog": (sources_dir / "catalog.4DCatalog").exists(),
            "total_code_lines": total_lines,
            "dependencies": deps,
        },
        "architecture": build_architecture(root),
        "guidance": build_guidance_status(root),
        "methods": methods,
        "classes": classes,
        "forms": forms,
    }
    return report, build_compact_report(report, methods, classes, forms)


def main() -> None:
    args = parse_args()
    start = args.path
    try:
        output_format = normalize_output_format(args.format)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(2)

    root = find_project_root(start)
    if not root:
        candidates = find_project_candidates(start)
        error = {
            "error": "No 4D project found",
            "searched_from": start,
            "message": "Pass a project root, Project directory, or one of the suggested .4DProject files on the next run.",
            "project_candidates": candidates,
            "next_run_hints": build_non_project_hints(),
            "guidance": build_guidance_status(),
        }
        if args.sync_guidance:
            error["guidance"]["sync_skipped_reason"] = "no_4d_project"
        if len(candidates) == MAX_PROJECT_CANDIDATES:
            error["project_candidates_truncated"] = True
        print(render_error(error, output_format), file=sys.stdout)
        sys.exit(1)

    report, compact = build_report(root)

    if args.sync_guidance:
        guidance = sync_guidance_files(root, compact)
        report["guidance"] = guidance
        compact["guidance"] = guidance

    if output_format == "human":
        print(render_human(report, compact))
    elif output_format == "terse":
        print(render_terse(compact))
    elif args.compact:
        print(json.dumps(compact, indent=2))
    else:
        print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
