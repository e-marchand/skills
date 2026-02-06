#!/usr/bin/env python3
"""Publish a 4D project to GitLab."""

import argparse
import os
import platform
import subprocess
import sys
from pathlib import Path


def is_command_available(cmd):
    """Check if a command is available in PATH."""
    result = subprocess.run(f"which {cmd}", shell=True, capture_output=True, text=True)
    return result.returncode == 0


def check_git():
    """Check if git is installed."""
    if is_command_available("git"):
        return True
    print("Error: git is not installed.")
    print("Please install git first:")
    if platform.system() == "Darwin":
        print("  brew install git")
        print("  or: xcode-select --install")
    elif platform.system() == "Linux":
        print("  sudo apt install git  (Debian/Ubuntu)")
        print("  sudo dnf install git  (Fedora)")
    else:
        print("  https://git-scm.com/downloads")
    return False


def check_glab(interactive=True):
    """Check if glab CLI is installed, offer to install on macOS."""
    if is_command_available("glab"):
        return True

    print("GitLab CLI (glab) is not installed.")

    if interactive and platform.system() == "Darwin" and is_command_available("brew"):
        print("\nInstall glab using Homebrew?")
        choice = input("[Y/n]: ").strip().lower()
        if choice != 'n':
            print("Installing glab...")
            result = subprocess.run("brew install glab", shell=True)
            if result.returncode == 0:
                print("  glab installed successfully")
                return True
            else:
                print("  Installation failed")
                return False

    print("\nPlease install glab manually:")
    if platform.system() == "Darwin":
        print("  brew install glab")
    elif platform.system() == "Linux":
        print("  https://gitlab.com/gitlab-org/cli#installation")
    else:
        print("  https://gitlab.com/gitlab-org/cli#installation")
    return False


def find_project_root():
    """Find the 4D project root (folder containing Project/*.4DProject)."""
    cwd = Path.cwd()

    project_file = list(cwd.glob("Project/*.4DProject"))
    if project_file:
        return cwd

    project_file = list(cwd.parent.glob("Project/*.4DProject"))
    if project_file:
        return cwd.parent

    return cwd


def get_project_name(project_root):
    """Get 4D project name from .4DProject file."""
    project_file = list(project_root.glob("Project/*.4DProject"))
    if project_file:
        return project_file[0].stem
    return project_root.name


def run_cmd(cmd, check=True):
    """Run a shell command and return output."""
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if check and result.returncode != 0:
        return None
    return result.stdout.strip()


def is_git_repo(path):
    """Check if path is a git repository."""
    return (path / ".git").exists()


def has_remote(path):
    """Check if git repo has a remote origin."""
    os.chdir(path)
    result = run_cmd("git remote get-url origin", check=False)
    return result is not None and result != ""


def check_glab_auth(hostname=None):
    """Check if glab CLI is authenticated."""
    cmd = "glab auth status"
    if hostname:
        cmd += f' --hostname "{hostname}"'
    result = subprocess.run(cmd, shell=True, capture_output=True)
    return result.returncode == 0


def setup_git(project_root, interactive=True):
    """Initialize git repository if needed."""
    os.chdir(project_root)

    if is_git_repo(project_root):
        print("  Git repository already initialized")
        return True

    if interactive:
        print("\nInitialize git repository?")
        choice = input("[Y/n]: ").strip().lower()
        if choice == 'n':
            return False

    run_cmd("git init")
    run_cmd("git add .")
    run_cmd('git commit -m "Initial commit"')
    print("  Git repository initialized")
    return True


def create_readme(project_root, project_name, description):
    """Create README.md with project name and description."""
    readme_path = project_root / "README.md"
    if readme_path.exists():
        return False

    content = f"# {project_name}\n\n{description}\n"
    readme_path.write_text(content)
    print(f"  Created: README.md")
    return True


def setup_gitlab_repo(project_root, project_name, public=False, description=None,
                      hostname=None, group=None, interactive=True):
    """Create GitLab repository if needed."""
    os.chdir(project_root)

    if has_remote(project_root):
        print("  GitLab remote already configured")
        return True

    # Check glab authentication
    if not check_glab_auth(hostname):
        print("\nGitLab CLI not authenticated.")
        if interactive:
            login_cmd = "glab auth login"
            if hostname:
                login_cmd += f' --hostname "{hostname}"'
            print(f"Run: {login_cmd}")
            choice = input("\nLogin now? [Y/n]: ").strip().lower()
            if choice != 'n':
                subprocess.run(login_cmd, shell=True)
                if not check_glab_auth(hostname):
                    print("Authentication failed.")
                    return False
            else:
                return False
        else:
            print("Please run: glab auth login" +
                  (f' --hostname "{hostname}"' if hostname else ""))
            return False

    if interactive:
        print(f"\nCreate GitLab repository '{project_name}'?")
        choice = input("[Y/n]: ").strip().lower()
        if choice == 'n':
            return False

        # Ask for description if not provided
        if description is None:
            print("\nRepository description (optional, press Enter to skip):")
            description = input("> ").strip() or None

        # Ask for group if not provided
        if group is None:
            print("\nGitLab group/namespace (optional, press Enter for personal namespace):")
            group = input("> ").strip() or None

        # Ask for visibility if not specified
        print("\nRepository visibility:")
        print("  1. Private (default)")
        print("  2. Internal")
        print("  3. Public")
        visibility = input("Choice [1/2/3]: ").strip()
        if visibility == "3":
            public = True

    visibility_flag = "--public" if public else "--private"

    # Create README if description provided
    if description:
        readme_created = create_readme(project_root, project_name, description)
        if readme_created:
            run_cmd("git add README.md")
            run_cmd('git commit -m "Add README.md"')

    # Build glab command
    repo_path = project_name
    if hostname:
        prefix = hostname.rstrip("/")
        if group:
            repo_path = f"{prefix}/{group}/{project_name}"
        else:
            repo_path = f"{prefix}/{project_name}"
    elif group:
        repo_path = project_name

    cmd = f'glab repo create "{repo_path}" {visibility_flag}'
    if description:
        escaped_desc = description.replace('"', '\\"')
        cmd += f' --description "{escaped_desc}"'
    if group and not hostname:
        cmd += f' --group "{group}"'

    result = subprocess.run(cmd, shell=True)

    if result.returncode != 0:
        print("  Failed to create repository")
        return False

    print(f"  Repository created: {project_name}")

    # Push code to remote
    run_cmd("git push --set-upstream origin HEAD")
    print("  Code pushed to GitLab")
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Publish a 4D project to GitLab",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Interactive mode (default)
  python3 publish.py

  # Non-interactive: create private repo
  python3 publish.py --yes

  # Public repo with description
  python3 publish.py --yes --public --description "My 4D component"

  # Private GitLab instance
  python3 publish.py --yes --hostname gitlab.example.com

  # Under a group
  python3 publish.py --yes --group my-team
"""
    )
    parser.add_argument("--yes", "-y", action="store_true",
                        help="Non-interactive mode, accept defaults")
    parser.add_argument("--public", action="store_true",
                        help="Create public repository (default: private)")
    parser.add_argument("--description", "-d", type=str, default=None,
                        help="Repository description")
    parser.add_argument("--hostname", type=str, default=None,
                        help="GitLab instance hostname (default: gitlab.com)")
    parser.add_argument("--group", "-g", type=str, default=None,
                        help="GitLab group/namespace for the repository")

    args = parser.parse_args()
    interactive = not args.yes

    # Check required tools
    if not check_git():
        return 1
    if not check_glab(interactive=interactive):
        return 1

    project_root = find_project_root()
    project_name = get_project_name(project_root)

    print(f"\n{'='*50}")
    print(f"  4D Project → GitLab Publisher")
    print(f"{'='*50}")
    print(f"\nProject: {project_name}")
    print(f"Path: {project_root}")
    if args.hostname:
        print(f"Instance: {args.hostname}")
    if args.group:
        print(f"Group: {args.group}")
    print("-" * 50)

    # Step 1: Git init
    if not setup_git(project_root, interactive=interactive):
        print("\nGit repository required. Exiting.")
        return 1

    # Step 2: Create GitLab repo
    if not setup_gitlab_repo(project_root, project_name,
                              public=args.public,
                              description=args.description,
                              hostname=args.hostname,
                              group=args.group,
                              interactive=interactive):
        return 1

    print("\nDone! Repository published to GitLab.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
