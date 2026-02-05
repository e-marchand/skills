#!/usr/bin/env python3
"""Publish a 4D project to GitHub."""

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


def check_gh(interactive=True):
    """Check if gh CLI is installed, offer to install on macOS."""
    if is_command_available("gh"):
        return True
    
    print("GitHub CLI (gh) is not installed.")
    
    if interactive and platform.system() == "Darwin" and is_command_available("brew"):
        print("\nInstall gh using Homebrew?")
        choice = input("[Y/n]: ").strip().lower()
        if choice != 'n':
            print("Installing gh...")
            result = subprocess.run("brew install gh", shell=True)
            if result.returncode == 0:
                print("  gh installed successfully")
                return True
            else:
                print("  Installation failed")
                return False
    
    print("\nPlease install gh manually:")
    if platform.system() == "Darwin":
        print("  brew install gh")
    elif platform.system() == "Linux":
        print("  https://github.com/cli/cli/blob/trunk/docs/install_linux.md")
    else:
        print("  https://cli.github.com/")
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


def check_gh_auth():
    """Check if gh CLI is authenticated."""
    result = subprocess.run("gh auth status", shell=True, capture_output=True)
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


def setup_github_repo(project_root, project_name, public=False, description=None, interactive=True):
    """Create GitHub repository if needed."""
    os.chdir(project_root)
    
    if has_remote(project_root):
        print("  GitHub remote already configured")
        return True
    
    # Check gh authentication
    if not check_gh_auth():
        print("\nGitHub CLI not authenticated.")
        if interactive:
            print("Run: gh auth login")
            choice = input("\nLogin now? [Y/n]: ").strip().lower()
            if choice != 'n':
                subprocess.run("gh auth login", shell=True)
                if not check_gh_auth():
                    print("Authentication failed.")
                    return False
            else:
                return False
        else:
            print("Please run: gh auth login")
            return False
    
    if interactive:
        print(f"\nCreate GitHub repository '{project_name}'?")
        choice = input("[Y/n]: ").strip().lower()
        if choice == 'n':
            return False
        
        # Ask for description if not provided
        if description is None:
            print("\nRepository description (optional, press Enter to skip):")
            description = input("> ").strip() or None
        
        # Ask for visibility if not specified
        print("\nRepository visibility:")
        print("  1. Private (default)")
        print("  2. Public")
        visibility = input("Choice [1/2]: ").strip()
        public = visibility == "2"
    
    visibility_flag = "--public" if public else "--private"
    
    # Create README if description provided
    if description:
        readme_created = create_readme(project_root, project_name, description)
        if readme_created:
            run_cmd("git add README.md")
            run_cmd('git commit -m "Add README.md"')
    
    # Build gh command
    cmd = f'gh repo create "{project_name}" --source=. --push {visibility_flag}'
    if description:
        escaped_desc = description.replace('"', '\\"')
        cmd += f' --description "{escaped_desc}"'
    
    result = subprocess.run(cmd, shell=True)
    
    if result.returncode == 0:
        print(f"  Repository created: {project_name}")
        return True
    else:
        print("  Failed to create repository")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Publish a 4D project to GitHub",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Interactive mode (default)
  python3 publish.py
  
  # Non-interactive: create private repo
  python3 publish.py --yes
  
  # Non-interactive: create public repo with description
  python3 publish.py --yes --public --description "My 4D component"
"""
    )
    parser.add_argument("--yes", "-y", action="store_true",
                        help="Non-interactive mode, accept defaults")
    parser.add_argument("--public", action="store_true",
                        help="Create public repository (default: private)")
    parser.add_argument("--description", "-d", type=str, default=None,
                        help="Repository description")
    
    args = parser.parse_args()
    interactive = not args.yes
    
    # Check required tools
    if not check_git():
        return 1
    if not check_gh(interactive=interactive):
        return 1
    
    project_root = find_project_root()
    project_name = get_project_name(project_root)
    
    print(f"\n{'='*50}")
    print(f"  4D Project → GitHub Publisher")
    print(f"{'='*50}")
    print(f"\nProject: {project_name}")
    print(f"Path: {project_root}")
    print("-" * 50)
    
    # Step 1: Git init
    if not setup_git(project_root, interactive=interactive):
        print("\nGit repository required. Exiting.")
        return 1
    
    # Step 2: Create GitHub repo
    if not setup_github_repo(project_root, project_name, 
                              public=args.public, 
                              description=args.description,
                              interactive=interactive):
        return 1
    
    print("\nDone! Repository published to GitHub.")
    print("\nTo add CI/CD workflows, run:")
    print("  python3 install_workflows.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
