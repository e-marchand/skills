#!/usr/bin/env python3
"""Analyze a 4D project and produce a structured summary."""

import argparse
import json
import os
import sys
import re
from pathlib import Path

MAX_PROJECT_CANDIDATES = 20


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
        for scope in [search_root, *search_root.parents]:
            for project_file in sorted(scope.rglob("*.4DProject")):
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


def count_files(directory: Path, extension: str) -> list[str]:
    """Return list of file stems matching extension."""
    if not directory.exists():
        return []
    return [f.stem for f in directory.rglob(f"*{extension}") if f.is_file()]


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
        # Class extends
        m = re.match(r"Class\s+extends\s+(.+)", stripped, re.IGNORECASE)
        if m:
            extends = m.group(1).strip()
        # Property declarations
        m = re.match(r"property\s+(.+)", stripped, re.IGNORECASE)
        if m:
            props.append(m.group(1).strip())
        # Function declarations
        m = re.match(r"(exposed\s+)?(shared\s+)?Function\s+(\w[\w.]*)", stripped, re.IGNORECASE)
        if m:
            prefix = ""
            if m.group(1):
                prefix += "exposed "
            if m.group(2):
                prefix += "shared "
            funcs.append(f"{prefix}{m.group(3)}")

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
    except Exception as e:
        return {"file_exists": True, "error": str(e)}


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
                    info["pages"] = len(pages) if isinstance(pages, list) else len(pages.keys()) if isinstance(pages, dict) else 0
                except Exception:
                    pass
            # Count associated methods
            methods = list(form_dir.glob("*.4dm"))
            if methods:
                info["methods"] = [m.stem for m in methods]
            forms.append(info)
    return forms


def analyze_settings(project_root: Path) -> dict:
    """Extract key project settings from .4DProject and settings.4DSettings."""
    result = {}
    # .4DProject
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

    # settings.4DSettings
    settings_file = project_dir / "Sources" / "settings.4DSettings"
    if settings_file.exists():
        result["has_settings"] = True
    else:
        result["has_settings"] = False

    return result


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", nargs="?", default=os.getcwd(), help="Path inside a 4D project, the project root, Project/, or a .4DProject file")
    parser.add_argument("--compact", action="store_true", help="Return compact JSON with names and counts instead of full details")
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


def build_compact_report(report: dict, methods: list[dict], classes: list[dict], forms: list[dict]) -> dict:
    """Return the compact JSON representation."""
    return {
        "project_root": report["project_root"],
        "settings": report["settings"],
        "summary": report["summary"],
        "method_names": [m["name"] for m in methods],
        "class_names": [c["name"] for c in classes],
        "form_names": [f["name"] for f in forms],
    }


def render_human(report: dict, compact: dict) -> str:
    """Render a readable multiline summary."""
    settings = compact["settings"]
    summary = compact["summary"]
    lines = [
        f"Project: {compact['project_root']}",
        f"Project file: {settings.get('project_file', 'unknown')}",
        f"Compatibility: {settings.get('compatibility_version', 'unknown')}",
        f"Tokenized text: {'yes' if settings.get('tokenized_text') else 'no'}",
        f"Settings file: {'yes' if settings.get('has_settings') else 'no'}",
        f"Summary: methods={summary['methods_count']}, classes={summary['classes_count']}, forms={summary['forms_count']}, db_methods={len(summary['database_methods'])}, catalog={'yes' if summary['has_catalog'] else 'no'}, code_lines={summary['total_code_lines']}",
        f"Database methods: {', '.join(summary['database_methods']) if summary['database_methods'] else 'none'}",
        f"Dependencies: {format_dependencies_human(summary['dependencies'])}",
        f"Methods: {', '.join(compact['method_names']) if compact['method_names'] else 'none'}",
        f"Classes: {', '.join(compact['class_names']) if compact['class_names'] else 'none'}",
        f"Forms: {', '.join(compact['form_names']) if compact['form_names'] else 'none'}",
    ]
    return "\n".join(lines)


def render_terse(compact: dict) -> str:
    """Render a token-light summary."""
    settings = compact["settings"]
    summary = compact["summary"]
    db_methods = ",".join(summary["database_methods"]) if summary["database_methods"] else "-"
    methods = ",".join(compact["method_names"]) if compact["method_names"] else "-"
    classes = ",".join(compact["class_names"]) if compact["class_names"] else "-"
    forms = ",".join(compact["form_names"]) if compact["form_names"] else "-"
    deps = format_dependencies_human(summary["dependencies"])
    return "\n".join(
        [
            f"root={compact['project_root']}",
            f"project={settings.get('project_file', '?')} compat={settings.get('compatibility_version', '?')} tokenized={1 if settings.get('tokenized_text') else 0} settings={1 if settings.get('has_settings') else 0}",
            f"counts m={summary['methods_count']} c={summary['classes_count']} f={summary['forms_count']} db={len(summary['database_methods'])} catalog={1 if summary['has_catalog'] else 0} lines={summary['total_code_lines']}",
            f"db_methods={db_methods}",
            f"methods={methods}",
            f"classes={classes}",
            f"forms={forms}",
            f"deps={deps}",
        ]
    )


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
    if error.get("project_candidates_truncated"):
        lines.append("project_candidates_truncated: true")
    return "\n".join(lines)


def main():
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
        }
        if len(candidates) == MAX_PROJECT_CANDIDATES:
            error["project_candidates_truncated"] = True
        print(render_error(error, output_format), file=sys.stdout)
        sys.exit(1)

    sources_dir = root / "Project" / "Sources"
    methods_dir = sources_dir / "Methods"
    classes_dir = sources_dir / "Classes"
    database_methods_dir = sources_dir / "DatabaseMethods"

    # Methods
    methods = []
    if methods_dir.exists():
        for f in sorted(methods_dir.glob("*.4dm")):
            methods.append(analyze_method(f))

    # Classes
    classes = []
    if classes_dir.exists():
        for f in sorted(classes_dir.glob("*.4dm")):
            classes.append(analyze_class(f))

    # Database methods
    db_methods = count_files(database_methods_dir, ".4dm") if database_methods_dir.exists() else []

    # Forms
    forms = analyze_forms(sources_dir)

    # Dependencies
    deps = analyze_dependencies(root)

    # Settings
    settings = analyze_settings(root)

    # Catalog (structure)
    catalog_file = root / "Project" / "Sources" / "catalog.4DCatalog"
    has_catalog = catalog_file.exists()

    # Summary
    total_lines = sum(m.get("lines", 0) for m in methods) + sum(c.get("lines", 0) for c in classes)

    report = {
        "project_root": str(root),
        "settings": settings,
        "summary": {
            "methods_count": len(methods),
            "classes_count": len(classes),
            "forms_count": len(forms),
            "database_methods": db_methods,
            "has_catalog": has_catalog,
            "total_code_lines": total_lines,
            "dependencies": deps,
        },
        "methods": methods,
        "classes": classes,
        "forms": forms,
    }

    compact = build_compact_report(report, methods, classes, forms)

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
