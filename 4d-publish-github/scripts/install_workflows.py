#!/usr/bin/env python3
"""Install GitHub workflows for a 4D project."""

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path


def get_skill_assets_path():
    """Get path to skill assets folder."""
    script_dir = Path(__file__).parent
    return script_dir.parent / "assets" / ".github" / "workflows"


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


def copy_workflow(src_name, dest_dir, dest_name=None):
    """Copy a workflow file from assets to project."""
    assets_path = get_skill_assets_path()
    src = assets_path / src_name
    dest = dest_dir / (dest_name or src_name)
    
    if not src.exists():
        print(f"Error: {src} not found")
        return False
    
    shutil.copy(src, dest)
    print(f"  Added: {dest.name}")
    return True


def has_remote():
    """Check if git repo has a remote origin."""
    result = run_cmd("git remote get-url origin", check=False)
    return result is not None and result != ""


def install_workflows(project_root, build=None, release=None, interactive=True):
    """Install CI/CD workflows."""
    workflows_dir = project_root / ".github" / "workflows"
    os.chdir(project_root)
    
    # Check existing workflows
    build_exists = (workflows_dir / "build.yml").exists()
    release_exists = (
        (workflows_dir / "release.yml").exists() or
        (workflows_dir / "releaseOnTag.yml").exists() or
        (workflows_dir / "releaseOnCreate.yml").exists()
    )
    
    if build_exists and release_exists:
        print("\nWorkflows already configured (build.yml and release workflow exist)")
        return True
    
    # Determine what to install
    install_build = build
    install_release = release
    
    if interactive:
        if not build_exists:
            if build is None:
                print("\nAdd build.yml workflow? (builds on .4dm changes)")
                choice = input("[Y/n]: ").strip().lower()
                install_build = choice != 'n'
        
        if not release_exists:
            if release is None:
                print("\nAdd release workflow?")
                print("  1. Release on tag push (automatic release when pushing a tag)")
                print("  2. Release on create (build when you create release on GitHub)")
                print("  3. No release workflow")
                choice = input("\nChoice [1/2/3]: ").strip()
                if choice == "1":
                    install_release = "tag"
                elif choice == "2":
                    install_release = "create"
                else:
                    install_release = None
    else:
        # Non-interactive defaults
        if install_build is None:
            install_build = not build_exists
    
    # Create workflows directory
    if install_build or install_release:
        workflows_dir.mkdir(parents=True, exist_ok=True)
        print(f"\nInstalling workflows in: {workflows_dir}")
    
    # Install build.yml
    if install_build and not build_exists:
        copy_workflow("build.yml", workflows_dir)
    elif build_exists:
        print("  Skipped: build.yml (already exists)")
    
    # Install release workflow
    if install_release and not release_exists:
        if install_release == "tag":
            copy_workflow("releaseOnTag.yml", workflows_dir, "release.yml")
        elif install_release == "create":
            copy_workflow("releaseOnCreate.yml", workflows_dir, "release.yml")
    elif release_exists:
        print("  Skipped: release workflow (already exists)")
    
    return install_build or install_release


def commit_and_push(project_root, interactive=True):
    """Commit and push workflow changes."""
    os.chdir(project_root)
    
    # Check if there are changes to commit
    status = run_cmd("git status --porcelain .github/workflows/")
    if not status:
        return True
    
    if interactive:
        print("\nCommit and push workflow changes?")
        choice = input("[Y/n]: ").strip().lower()
        if choice == 'n':
            print("  Changes not committed. Run manually:")
            print("    git add .github/workflows/")
            print('    git commit -m "Add CI/CD workflows"')
            print("    git push")
            return False
    
    run_cmd("git add .github/workflows/")
    run_cmd('git commit -m "Add CI/CD workflows"')
    
    if has_remote():
        run_cmd("git push")
        print("  Workflows committed and pushed")
    else:
        print("  Workflows committed (no remote to push)")
    
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Install GitHub CI/CD workflows for a 4D project",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Interactive mode (default)
  python3 install_workflows.py
  
  # Non-interactive: install build.yml only
  python3 install_workflows.py --yes --build
  
  # Non-interactive: install build and release-on-tag
  python3 install_workflows.py --yes --build --release-on-tag
  
  # Non-interactive: install release-on-create only
  python3 install_workflows.py --yes --release-on-create
"""
    )
    parser.add_argument("--yes", "-y", action="store_true",
                        help="Non-interactive mode, accept defaults")
    parser.add_argument("--build", action="store_true",
                        help="Install build.yml workflow")
    parser.add_argument("--release-on-tag", action="store_true",
                        help="Install release workflow (triggered on tag push)")
    parser.add_argument("--release-on-create", action="store_true",
                        help="Install release workflow (triggered on release create)")
    parser.add_argument("--no-push", action="store_true",
                        help="Don't commit and push changes")
    
    args = parser.parse_args()
    interactive = not args.yes
    
    # Determine release type
    release = None
    if args.release_on_tag:
        release = "tag"
    elif args.release_on_create:
        release = "create"
    
    # Determine build
    build = args.build if args.yes else None
    
    project_root = find_project_root()
    project_name = get_project_name(project_root)
    
    print(f"\n{'='*50}")
    print(f"  4D Project Workflow Installer")
    print(f"{'='*50}")
    print(f"\nProject: {project_name}")
    print(f"Path: {project_root}")
    print("-" * 50)
    
    # Install workflows
    if install_workflows(project_root, build=build, release=release, interactive=interactive):
        # Commit and push
        if not args.no_push:
            commit_and_push(project_root, interactive=interactive)
    
    print("\nDone!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
