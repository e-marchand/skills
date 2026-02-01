# 4D Skills for AI Assistants

Skills for running and compiling 4D projects with AI coding assistants.

## Available Skills

| Skill | Description |
|-------|-------------|
| [4d-run](4d-run/SKILL.md) | Run a 4D method using tool4d command-line tool |
| [4d-check-syntax](4d-check-syntax/SKILL.md) | Compile a 4D project to check for syntax errors |
| [4d-create-project](4d-create-project/SKILL.md) | Create a new 4D project from scratch |
| [4d-find-command](4d-find-command/SKILL.md) | Find 4D commands by keyword |
| [4d-validate-form](4d-validate-form/SKILL.md) | Validate a .4DForm file against JSON schema |

## Installation

### Quick Install (Recommended)

Run this command in your project directory:

```bash
curl -fsSL https://raw.githubusercontent.com/e-marchand/skills/main/install.sh | bash
```

Or specify a target directory:

```bash
curl -fsSL https://raw.githubusercontent.com/e-marchand/skills/main/install.sh | bash -s -- /path/to/your/project
```

The installer will:
- Detect existing `.claude`, `.github`, or `.agent` folders
- If none found, prompt you to choose which one to create
- Download and install all skills to the appropriate location

### Manual Installation

Copy the skill folders to the appropriate location for your AI assistant:

| Assistant | Project Location | Global Location |
|-----------|------------------|-----------------|
| Claude Code | `.claude/skills/` | - |
| GitHub Copilot | `.github/skills/` | `~/.github/skills/` |
| Antigravity | `.agent/skills/` | `~/.gemini/antigravity/global_skills/` |

## Requirements

- **tool4d**: Must be installed in VS Code or Antigravity by [4D-Analyser extension](https://marketplace.visualstudio.com/items?itemName=4D.4d-analyzer)
- **macOS**: Scripts are designed for macOS paths

## What are Agent Skills?

See [ABOUT_SKILLS.md](ABOUT_SKILLS.md) for a detailed explanation of what Agent Skills are and how they work.
