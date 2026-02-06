#!/usr/bin/env python3
"""Analyze a 4D project and produce a structured summary."""

import json
import os
import sys
import re
from pathlib import Path


def find_project_root(start_path: str) -> Path | None:
    """Walk up to find directory containing a .4DProject file."""
    p = Path(start_path).resolve()
    if p.is_file():
        p = p.parent
    for d in [p, *p.parents]:
        project_dir = d / "Project"
        if project_dir.is_dir():
            for f in project_dir.iterdir():
                if f.suffix == ".4DProject":
                    return d
    return None


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
    for f in project_dir.iterdir():
        if f.suffix == ".4DProject":
            try:
                data = json.loads(f.read_text())
                result["project_file"] = f.name
                result["compatibility_version"] = data.get("compatibilityVersion")
                result["tokenized_text"] = data.get("tokenizedText")
            except Exception:
                pass
            break

    # settings.4DSettings
    settings_file = project_dir / "Sources" / "settings.4DSettings"
    if settings_file.exists():
        result["has_settings"] = True
    else:
        result["has_settings"] = False

    return result


def main():
    start = sys.argv[1] if len(sys.argv) > 1 else os.getcwd()
    root = find_project_root(start)
    if not root:
        print(json.dumps({"error": "No 4D project found", "searched_from": start}), file=sys.stdout)
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

    # Output format
    fmt = "--compact" if "--compact" in sys.argv else "--full"
    if fmt == "--compact":
        compact = {
            "project_root": report["project_root"],
            "settings": report["settings"],
            "summary": report["summary"],
            "method_names": [m["name"] for m in methods],
            "class_names": [c["name"] for c in classes],
            "form_names": [f["name"] for f in forms],
        }
        print(json.dumps(compact, indent=2))
    else:
        print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
