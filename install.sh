#!/bin/bash
#
# 4D Skills Installer
# Downloads and installs 4D skills for AI coding assistants
#
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/e-marchand/skills/main/install.sh | bash
#   curl -fsSL https://raw.githubusercontent.com/e-marchand/skills/main/install.sh | bash -s -- /path/to/project
#

set -e

REPO_ZIP_URL="https://github.com/e-marchand/skills/archive/refs/heads/main.zip"
REPO_URL="https://github.com/e-marchand/skills"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

# Target directory (argument or current directory)
TARGET_DIR="${1:-.}"
TARGET_DIR="$(cd "$TARGET_DIR" && pwd)"

# Detect existing config folders
detect_config_folder() {
    local found_folders=()

    if [ -d "$TARGET_DIR/.claude" ]; then
        found_folders+=(".claude")
    fi
    if [ -d "$TARGET_DIR/.github" ]; then
        found_folders+=(".github")
    fi
    if [ -d "$TARGET_DIR/.agent" ]; then
        found_folders+=(".agent")
    fi

    echo "${found_folders[@]}"
}

# Find all skill folders (directories containing SKILL.md)
find_skills() {
    local source_dir="$1"
    local skills=()

    for dir in "$source_dir"/*/; do
        if [ -f "$dir/SKILL.md" ]; then
            skills+=("$(basename "$dir")")
        fi
    done

    echo "${skills[@]}"
}

# Main installation
main() {
    echo ""
    echo "╔═══════════════════════════════════════╗"
    echo "║      4D Skills Installer              ║"
    echo "╚═══════════════════════════════════════╝"
    echo ""

    print_info "Installing skills to: $TARGET_DIR"

    # Detect existing folders
    IFS=' ' read -ra found_folders <<< "$(detect_config_folder)"

    if [ ${#found_folders[@]} -eq 0 ]; then
        # No config folder found, ask user
        print_warning "No .claude, .github, or .agent folder found in $TARGET_DIR"
        echo ""
        echo "Which folder would you like to create?"
        echo "  1) .claude  (Claude Code)"
        echo "  2) .github  (GitHub Copilot)"
        echo "  3) .agent   (Antigravity)"
        echo "  4) All of the above"
        echo ""
        read -p "Enter choice [1-4]: " choice

        case "$choice" in
            1) found_folders=(".claude") ;;
            2) found_folders=(".github") ;;
            3) found_folders=(".agent") ;;
            4) found_folders=(".claude" ".github" ".agent") ;;
            *)
                print_error "Invalid choice. Exiting."
                exit 1
                ;;
        esac
    else
        print_success "Found existing config folders: ${found_folders[*]}"
    fi

    echo ""

    # Create temp directory
    TMP_DIR=$(mktemp -d)
    trap "rm -rf '$TMP_DIR'" EXIT

    # Download and extract the repo
    print_info "Downloading skills from GitHub..."
    if curl -fsSL "$REPO_ZIP_URL" -o "$TMP_DIR/skills.zip"; then
        print_success "Downloaded skills archive"
    else
        print_error "Failed to download skills archive"
        exit 1
    fi

    print_info "Extracting..."
    if unzip -q "$TMP_DIR/skills.zip" -d "$TMP_DIR"; then
        print_success "Extracted archive"
    else
        print_error "Failed to extract archive"
        exit 1
    fi

    # Find the extracted folder (skills-main)
    EXTRACTED_DIR="$TMP_DIR/skills-main"

    # Find all skills
    IFS=' ' read -ra SKILLS <<< "$(find_skills "$EXTRACTED_DIR")"

    if [ ${#SKILLS[@]} -eq 0 ]; then
        print_error "No skills found in the repository"
        exit 1
    fi

    print_success "Found ${#SKILLS[@]} skills: ${SKILLS[*]}"
    echo ""

    # Install skills to each folder
    for folder in "${found_folders[@]}"; do
        dest_dir="$TARGET_DIR/$folder/skills"

        print_info "Installing to $folder/skills/"
        mkdir -p "$dest_dir"

        for skill in "${SKILLS[@]}"; do
            print_info "  Copying $skill..."
            cp -r "$EXTRACTED_DIR/$skill" "$dest_dir/"

            # Make scripts executable
            if [ -d "$dest_dir/$skill/scripts" ]; then
                chmod +x "$dest_dir/$skill/scripts/"*.sh 2>/dev/null || true
            fi

            print_success "  Installed $skill"
        done

        echo ""
    done

    print_success "Installation complete!"
    echo ""
    echo "Installed skills:"
    for skill in "${SKILLS[@]}"; do
        echo "  - $skill"
    done
    echo ""
    echo "See README at: $REPO_URL"
}

main
