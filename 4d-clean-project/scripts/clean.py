#!/usr/bin/env python3
"""Clean a 4D project by removing generated files and caches."""

import os
import shutil
import sys
from pathlib import Path


def find_project_root(start_path: Path) -> Path:
    """Find 4D project root by looking for .4DProject file."""
    current = start_path.resolve()

    # Search in current directory and parents
    search_dirs = [current] + list(current.parents)

    for directory in search_dirs:
        # Look for .4DProject file in Project/ subfolder
        project_folder = directory / "Project"
        if project_folder.is_dir():
            for f in project_folder.glob("*.4DProject"):
                if f.is_file():
                    return directory

        # Also check if we're inside Project folder
        if directory.name == "Project":
            for f in directory.glob("*.4DProject"):
                if f.is_file():
                    return directory.parent

    raise FileNotFoundError(f"No .4DProject file found from: {start_path}")


def clean_project(project_dir: Path) -> list[str]:
    """Clean the 4D project and return list of removed items."""
    removed = []

    # Remove DerivedData folders (recursively)
    for derived in project_dir.rglob("DerivedData"):
        if derived.is_dir():
            shutil.rmtree(derived)
            removed.append(str(derived.relative_to(project_dir)))

    # Remove Libraries/ folder at root
    libraries = project_dir / "Libraries"
    if libraries.is_dir():
        shutil.rmtree(libraries)
        removed.append("Libraries/")

    # Remove userPreferences.*/ folders at root
    for pref in project_dir.glob("userPreferences.*"):
        if pref.is_dir():
            shutil.rmtree(pref)
            removed.append(f"{pref.name}/")

    # Remove Project/Trash folder
    trash = project_dir / "Project" / "Trash"
    if trash.is_dir():
        shutil.rmtree(trash)
        removed.append("Project/Trash/")

    # Remove Logs/* at root (keep folder, remove contents)
    logs = project_dir / "Logs"
    if logs.is_dir():
        for item in logs.iterdir():
            if item.is_dir():
                shutil.rmtree(item)
            else:
                item.unlink()
            removed.append(f"Logs/{item.name}")

    # Remove system files recursively
    for pattern in [".DS_Store", "ehthumbs.db", "Thumbs.db"]:
        for f in project_dir.rglob(pattern):
            if f.is_file():
                f.unlink()
                removed.append(str(f.relative_to(project_dir)))

    return removed


def main():
    start_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()

    try:
        project_dir = find_project_root(start_path)
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"Cleaning 4D project: {project_dir}")

    removed = clean_project(project_dir)

    if not removed:
        print("Nothing to clean")
    else:
        print(f"Removed {len(removed)} items:")
        for item in removed:
            print(f"  - {item}")


if __name__ == "__main__":
    main()
