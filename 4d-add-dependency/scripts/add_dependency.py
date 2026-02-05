#!/usr/bin/env python3
"""Add a dependency to a 4D project.

Usage:
    add_dependency.py <repo> [options]

Arguments:
    repo    Local path, GitHub repo (owner/repo), or GitHub URL

Options:
    --name NAME        Override the dependency name (default: derived from repo)
    --tag TAG          Exact version tag (e.g., "1.0.0")
    --version VERSION  Semantic version (e.g., "latest", "1.1.0")
    --project PATH     Path to 4D project root (default: current directory)
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path


def parse_github_url(url: str) -> tuple[str | None, str | None]:
    """Parse GitHub URL to extract owner/repo and optional tag.

    Supports:
        https://github.com/owner/repo
        https://github.com/owner/repo/releases/tag/v1.0.0

    Returns:
        (owner/repo, tag) or (None, None) if not a GitHub URL
    """
    # Match github.com URLs
    match = re.match(r"https?://github\.com/([^/]+/[^/]+?)(?:\.git)?(?:/releases/tag/([^/]+))?/?$", url)
    if match:
        repo = match.group(1)
        tag = match.group(2)
        return repo, tag
    return None, None


def is_github_url(repo: str) -> bool:
    """Check if string is a GitHub URL."""
    return repo.startswith("https://github.com/") or repo.startswith("http://github.com/")


def find_project_root(start_path: Path) -> Path | None:
    """Find 4D project root by looking for Project/Sources directory."""
    current = start_path.resolve()
    while current != current.parent:
        if (current / "Project" / "Sources").is_dir():
            return current
        # Also check if we're inside Project/Sources
        if current.name == "Sources" and current.parent.name == "Project":
            return current.parent.parent
        if current.name == "Project" and (current / "Sources").is_dir():
            return current.parent
        current = current.parent
    return None


def find_environment4d(start_path: Path) -> Path | None:
    """Find environment4d.json by walking up directories."""
    current = start_path.resolve()
    while current != current.parent:
        env_file = current / "environment4d.json"
        if env_file.is_file():
            return env_file
        current = current.parent
    return None


def is_github_repo(repo: str) -> bool:
    """Check if repo string looks like a GitHub repo (owner/repo format or URL)."""
    if is_github_url(repo):
        return True
    if os.path.exists(repo):
        return False
    parts = repo.split("/")
    return len(parts) == 2 and not repo.startswith("/") and not repo.startswith(".")


def get_dependency_name(repo: str, name_override: str | None) -> str:
    """Extract dependency name from repo path or use override."""
    if name_override:
        return name_override
    if is_github_url(repo):
        parsed_repo, _ = parse_github_url(repo)
        if parsed_repo:
            return parsed_repo.split("/")[-1]
    if is_github_repo(repo):
        return repo.split("/")[-1]
    # Local path: use folder name, strip .4dbase if present
    path = Path(repo)
    name = path.name
    if name.endswith(".4dbase"):
        name = name[:-7]
    return name


def is_sibling_folder(project_root: Path, repo_path: Path) -> bool:
    """Check if repo is a sibling folder (same parent as project)."""
    project_parent = project_root.resolve().parent
    repo_resolved = repo_path.resolve()
    return repo_resolved.parent == project_parent


def load_json_file(path: Path) -> dict:
    """Load JSON file or return empty dict if not exists."""
    if path.is_file():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_json_file(path: Path, data: dict):
    """Save dict as JSON file with formatting."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent="\t", ensure_ascii=False)
        f.write("\n")


def add_dependency(
    repo: str,
    name_override: str | None = None,
    tag: str | None = None,
    version: str | None = None,
    project_path: str | None = None,
) -> dict:
    """Add a dependency to the 4D project.

    Returns dict with status and messages.
    """
    result = {"success": False, "messages": [], "files_modified": []}

    # Find project root
    start_path = Path(project_path) if project_path else Path.cwd()
    project_root = find_project_root(start_path)

    if not project_root:
        result["messages"].append(f"Error: No 4D project found from {start_path}")
        return result

    # Handle GitHub URLs - extract repo and tag
    github_path = repo
    url_tag = None
    if is_github_url(repo):
        parsed_repo, url_tag = parse_github_url(repo)
        if parsed_repo:
            github_path = parsed_repo

    # Determine dependency name and type
    dep_name = get_dependency_name(repo, name_override)
    github_repo = is_github_repo(repo)

    # Build dependency entry
    if github_repo:
        dep_entry = {"github": github_path}
        # CLI tag takes precedence over URL tag
        effective_tag = tag or url_tag
        if effective_tag:
            dep_entry["tag"] = effective_tag
        elif version:
            dep_entry["version"] = version
    else:
        dep_entry = {}

    # Update dependencies.json
    deps_file = project_root / "Project" / "Sources" / "dependencies.json"
    deps_data = load_json_file(deps_file)

    if "dependencies" not in deps_data:
        deps_data["dependencies"] = {}
    if "version" not in deps_data:
        deps_data["version"] = 2130

    deps_data["dependencies"][dep_name] = dep_entry
    save_json_file(deps_file, deps_data)
    result["files_modified"].append(str(deps_file))
    result["messages"].append(f"Added '{dep_name}' to {deps_file}")

    # For local repos, handle environment4d.json if needed
    if not github_repo:
        repo_path = Path(repo).resolve()

        if not is_sibling_folder(project_root, repo_path):
            # Need to add to environment4d.json
            env_file = find_environment4d(project_root)

            if env_file is None:
                # Create in parent directory of project
                env_file = project_root.parent / "environment4d.json"
                result["messages"].append(f"Creating new {env_file}")

            env_data = load_json_file(env_file)

            if "dependencies" not in env_data:
                env_data["dependencies"] = {}
            if "devDependencies" not in env_data:
                env_data["devDependencies"] = {}

            # Add file:// URL for local dependency
            file_url = f"file://{repo_path}"
            if not file_url.endswith(".4dbase"):
                # Check if .4dbase folder exists
                if repo_path.with_suffix(".4dbase").is_dir():
                    file_url = f"file://{repo_path}.4dbase"
                elif (repo_path / f"{repo_path.name}.4dbase").is_dir():
                    file_url = f"file://{repo_path / f'{repo_path.name}.4dbase'}"

            env_data["dependencies"][dep_name] = file_url
            save_json_file(env_file, env_data)
            result["files_modified"].append(str(env_file))
            result["messages"].append(f"Added '{dep_name}' to {env_file}")
        else:
            result["messages"].append(f"'{dep_name}' is a sibling folder, no environment4d.json update needed")

    result["success"] = True
    return result


def main():
    parser = argparse.ArgumentParser(
        description="Add a dependency to a 4D project",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Add a GitHub dependency
    %(prog)s mesopelagique/JSONRPC --tag 1.0.0

    # Add from GitHub URL
    %(prog)s https://github.com/mesopelagique/SemVer

    # Add from GitHub release URL (tag extracted automatically)
    %(prog)s https://github.com/mesopelagique/SemVer/releases/tag/0.2.0

    # Add a local sibling dependency
    %(prog)s ../MyComponent

    # Add a local dependency with custom name
    %(prog)s /path/to/component --name MyComponent

    # Add to specific project
    %(prog)s owner/repo --project /path/to/4d/project
"""
    )
    parser.add_argument("repo", help="Local path, GitHub repo (owner/repo), or GitHub URL")
    parser.add_argument("--name", dest="name_override", help="Override dependency name")
    parser.add_argument("--tag", help="Exact version tag")
    parser.add_argument("--version", help="Semantic version (e.g., 'latest', '1.1.0')")
    parser.add_argument("--project", dest="project_path", help="Path to 4D project")

    args = parser.parse_args()

    if args.tag and args.version:
        print("Error: Cannot specify both --tag and --version", file=sys.stderr)
        sys.exit(1)

    result = add_dependency(
        repo=args.repo,
        name_override=args.name_override,
        tag=args.tag,
        version=args.version,
        project_path=args.project_path,
    )

    for msg in result["messages"]:
        print(msg)

    sys.exit(0 if result["success"] else 1)


if __name__ == "__main__":
    main()
