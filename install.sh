#!/bin/bash
#
# 4D Skills Installer
# Downloads and installs 4D skills for AI coding assistants
#
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/e-marchand/skills/main/install.sh | bash
#   curl -fsSL https://raw.githubusercontent.com/e-marchand/skills/main/install.sh | bash -s -- /path/to/project
#   curl -fsSL https://raw.githubusercontent.com/e-marchand/skills/main/install.sh | bash -s -- --global
#   ./install.sh --symlink              # Copy to first folder, symlink the rest to it
#   ./install.sh --global --symlink     # Copy to first global dir, symlink the rest
#

set -e

REPO_ZIP_URL="https://github.com/e-marchand/skills/archive/refs/heads/main.zip"
REPO_URL="https://github.com/e-marchand/skills"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
ORANGE='\033[38;5;208m'
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

# Check if running from pipe (stdin is not a terminal)
is_piped() {
    ! [ -t 0 ]
}

# If piped, download and re-exec from local file with TTY
if is_piped && [ -z "$SKILLS_REEXEC" ]; then
    TMP_DIR=$(mktemp -d)
    curl -fsSL "$REPO_ZIP_URL" -o "$TMP_DIR/skills.zip" 2>/dev/null
    unzip -q "$TMP_DIR/skills.zip" -d "$TMP_DIR"
    export SKILLS_REEXEC=1
    export SKILLS_TMP_DIR="$TMP_DIR"
    # Re-exec with stdin from /dev/tty to restore terminal input
    exec bash "$TMP_DIR/skills-main/install.sh" "$@" </dev/tty
fi

# Parse arguments
GLOBAL_MODE=false
SYMLINK_MODE=false
TARGET_DIR=""

for arg in "$@"; do
    case "$arg" in
        --global) GLOBAL_MODE=true ;;
        --symlink) SYMLINK_MODE=true ;;
        *) TARGET_DIR="$arg" ;;
    esac
done

if [ "$GLOBAL_MODE" = false ]; then
    TARGET_DIR="${TARGET_DIR:-.}"
    TARGET_DIR="$(cd "$TARGET_DIR" && pwd)"
fi

# Global install directory for a given service key
global_dir_for() {
    case "$1" in
        .github) echo "$HOME/.github/skills" ;;
        .agent)
            if [ "$SYMLINK_MODE" = true ]; then
                echo "$HOME/.agent/skills"
            else
                echo "$HOME/.gemini/antigravity/global_skills"
            fi
            ;;
        .codex)  echo "$HOME/.codex/skills" ;;
        .claude)  echo "$HOME/.claude/skills" ;;
    esac
}

# Detect existing config folders (project mode)
detect_config_folder() {
    local found_folders=()

    if [ -d "$TARGET_DIR/.agent" ]; then
        found_folders+=(".agent")
    fi
    if [ -d "$TARGET_DIR/.claude" ]; then
        found_folders+=(".claude")
    fi
    if [ -d "$TARGET_DIR/.github" ]; then
        found_folders+=(".github")
    fi
    if [ -d "$TARGET_DIR/.codex" ]; then
        found_folders+=(".codex")
    fi

    echo "${found_folders[@]}"
}

# Detect existing global config folders
detect_global_folder() {
    local found_folders=()

    for key in ".agent" ".github" ".codex" ".claude"; do
        local dir
        dir="$(global_dir_for "$key")"
        # Check if the parent structure exists, or if symlink mode will create it
        if [ -d "$(dirname "$dir")" ] || [ "$SYMLINK_MODE" = true ]; then
            found_folders+=("$key")
        fi
    done

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

# Ask user which folder to create (project mode)
ask_folder_choice() {
    # Print menu to stderr so it's visible (stdout is captured by $(...))
    echo "" >&2
    echo "Which folder would you like to create?" >&2
    echo "  1) .claude  (Claude Code)" >&2
    echo "  2) .github  (GitHub Copilot)" >&2
    echo "  3) .agent   (Antigravity)" >&2
    echo "  4) .codex   (Codex)" >&2
    echo "  5) All of the above" >&2
    echo "" >&2
    read -p "Enter choice [1-5]: " choice

    case "$choice" in
        1) echo ".claude" ;;
        2) echo ".github" ;;
        3) echo ".agent" ;;
        4) echo ".codex" ;;
        5) echo ".claude .github .agent .codex" ;;
        *)
            print_error "Invalid choice. Exiting."
            exit 1
            ;;
    esac
}

# Ask user which global folder to create
ask_global_folder_choice() {
    echo "" >&2
    echo "Which global location would you like to install to?" >&2
    echo "  1) ~/.github/skills/                        (GitHub Copilot)" >&2
    echo "  2) ~/.gemini/antigravity/global_skills/      (Antigravity)" >&2
    echo "  3) ~/.codex/skills/                          (Codex)" >&2
    echo "  4) All of the above" >&2
    echo "" >&2
    print_warning "Claude Code does not support a global skills directory." >&2
    echo "" >&2
    read -p "Enter choice [1-4]: " choice

    case "$choice" in
        1) echo ".github" ;;
        2) echo ".agent" ;;
        3) echo ".codex" ;;
        4) echo ".github .agent .codex" ;;
        *)
            print_error "Invalid choice. Exiting."
            exit 1
            ;;
    esac
}

# Main installation
main() {
    echo ""
    echo -e "${ORANGE}╔═══════════════════════════════════════╗${NC}"
    echo -e "${ORANGE}║${NC}                                       ${ORANGE}║${NC}"
    echo -e "${ORANGE}║${NC}      ${BLUE}█  █▀▀▀▖${NC}                         ${ORANGE}║${NC}"
    echo -e "${ORANGE}║${NC}      ${BLUE}█  █   ▌${NC}  Skills Installer       ${ORANGE}║${NC}"
    echo -e "${ORANGE}║${NC}      ${BLUE}████   ▌${NC}                         ${ORANGE}║${NC}"
    echo -e "${ORANGE}║${NC}         ${BLUE}█   ▌${NC}                         ${ORANGE}║${NC}"
    echo -e "${ORANGE}║${NC}         ${BLUE}█▄▄▄▘${NC}                         ${ORANGE}║${NC}"
    echo -e "${ORANGE}║${NC}                                       ${ORANGE}║${NC}"
    echo -e "${ORANGE}╚═══════════════════════════════════════╝${NC}"
    echo ""

    if [ "$GLOBAL_MODE" = true ]; then
        print_info "Installing skills globally"
    else
        print_info "Installing skills to: $TARGET_DIR"
    fi

    if [ "$GLOBAL_MODE" = true ]; then
        # Global mode: detect existing global folders
        IFS=' ' read -ra found_folders <<< "$(detect_global_folder)"

        if [ ${#found_folders[@]} -eq 0 ]; then
            print_warning "No global config folders found"
            IFS=' ' read -ra found_folders <<< "$(ask_global_folder_choice)"
        else
            print_success "Found existing global config for: ${found_folders[*]}"
        fi
    else
        # Project mode: detect existing project folders
        IFS=' ' read -ra found_folders <<< "$(detect_config_folder)"

        if [ ${#found_folders[@]} -eq 0 ]; then
            print_warning "No .claude, .github, .agent, or .codex folder found in $TARGET_DIR"
            IFS=' ' read -ra found_folders <<< "$(ask_folder_choice)"
        else
            print_success "Found existing config folders: ${found_folders[*]}"
        fi
    fi

    echo ""

    # Use existing temp dir if re-exec'd, otherwise download
    if [ -n "$SKILLS_TMP_DIR" ] && [ -d "$SKILLS_TMP_DIR/skills-main" ]; then
        EXTRACTED_DIR="$SKILLS_TMP_DIR/skills-main"
        trap "rm -rf '$SKILLS_TMP_DIR'" EXIT
    else
        TMP_DIR=$(mktemp -d)
        trap "rm -rf '$TMP_DIR'" EXIT

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

        EXTRACTED_DIR="$TMP_DIR/skills-main"
    fi

    # Symlink mode needs at least 2 folders to be useful (first gets copies, rest get links)
    if [ "$SYMLINK_MODE" = true ] && [ ${#found_folders[@]} -lt 2 ]; then
        print_warning "Symlink mode requires at least 2 target folders (first gets copies, rest get links)"
        print_warning "Falling back to copy mode"
        SYMLINK_MODE=false
    fi

    # Find all skills
    IFS=' ' read -ra SKILLS <<< "$(find_skills "$EXTRACTED_DIR")"

    if [ ${#SKILLS[@]} -eq 0 ]; then
        print_error "No skills found in the repository"
        exit 1
    fi

    print_success "Found ${#SKILLS[@]} skills: ${SKILLS[*]}"
    echo ""

    # Install skills to each folder
    # In symlink mode: first folder gets copies, the rest get symlinks to the first
    local primary_dir=""

    for folder in "${found_folders[@]}"; do
        if [ "$GLOBAL_MODE" = true ]; then
            dest_dir="$(global_dir_for "$folder")"
        else
            dest_dir="$TARGET_DIR/$folder/skills"
        fi

        # Determine if this folder gets copies or symlinks
        local is_primary=false
        if [ "$SYMLINK_MODE" = true ] && [ -z "$primary_dir" ]; then
            is_primary=true
            primary_dir="$dest_dir"
        fi

        if [ "$is_primary" = true ] || [ "$SYMLINK_MODE" = false ]; then
            if [ "$GLOBAL_MODE" = true ]; then
                print_info "Installing to $dest_dir/"
            else
                print_info "Installing to $folder/skills/"
            fi
        else
            if [ "$GLOBAL_MODE" = true ]; then
                print_info "Linking $dest_dir/ -> $primary_dir/"
            else
                print_info "Linking $folder/skills/ -> ${found_folders[0]}/skills/"
            fi
        fi

        mkdir -p "$dest_dir"

        for skill in "${SKILLS[@]}"; do
            local target="$dest_dir/$skill"

            # Remove existing symlink to avoid cp errors
            # In symlink mode, also remove existing directory so ln -s replaces it
            if [ -L "$target" ]; then
                rm "$target"
            elif [ -d "$target" ] && [ "$SYMLINK_MODE" = true ]; then
                rm -rf "$target"
            fi

            if [ "$SYMLINK_MODE" = true ] && [ "$is_primary" = false ]; then
                # Symlink to the primary folder's skill
                local link_source="$primary_dir/$skill"
                if ln -s "$link_source" "$target" 2>/dev/null; then
                    print_success "  Linked $skill"
                else
                    # Fallback to copy if symlink fails
                    print_warning "  Symlink failed for $skill, copying instead..."
                    cp -r "$EXTRACTED_DIR/$skill" "$dest_dir/"
                    print_success "  Installed $skill (copied)"
                fi
            else
                # Copy from source
                print_info "  Copying $skill..."
                cp -r "$EXTRACTED_DIR/$skill" "$dest_dir/"
                print_success "  Installed $skill"
            fi

            # Make scripts executable (follow symlinks)
            local real_skill="$target"
            if [ -L "$target" ]; then
                real_skill="$(readlink "$target")"
            fi
            if [ -d "$real_skill/scripts" ]; then
                chmod +x "$real_skill/scripts/"*.sh 2>/dev/null || true
                chmod +x "$real_skill/scripts/"*.py 2>/dev/null || true
            fi
        done

        echo ""
    done

    # In global symlink mode, also link Gemini's expected path to the primary
    if [ "$SYMLINK_MODE" = true ] && [ "$GLOBAL_MODE" = true ]; then
        local gemini_dir="$HOME/.gemini/antigravity/global_skills"
        if [ "$primary_dir" != "$gemini_dir" ]; then
            print_info "Linking $gemini_dir/ -> $primary_dir/"
            mkdir -p "$gemini_dir"
            for skill in "${SKILLS[@]}"; do
                local gtarget="$gemini_dir/$skill"
                if [ -L "$gtarget" ]; then
                    rm "$gtarget"
                elif [ -d "$gtarget" ]; then
                    rm -rf "$gtarget"
                fi
                if ln -s "$primary_dir/$skill" "$gtarget" 2>/dev/null; then
                    print_success "  Linked $skill"
                else
                    print_warning "  Symlink failed for $skill"
                fi
            done
            echo ""
        fi
    fi

    if [ "$SYMLINK_MODE" = true ]; then
        print_success "Installation complete! (symlink mode)"
    else
        print_success "Installation complete!"
    fi
    echo ""
    echo "Installed skills:"
    for skill in "${SKILLS[@]}"; do
        echo "  - $skill"
    done
    echo ""
    echo "See README at: $REPO_URL"
}

main
