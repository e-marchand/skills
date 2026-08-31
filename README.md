# 4D Skills for AI Assistants

[Skills](#what-are-agent-skills) for running and compiling 4D projects with AI coding assistants.

## Available Skills

| Skill | Description | Requirements |
|-------|-------------|--------------|
| [4d-add-dependency](4d-add-dependency/SKILL.md) | Add dependencies to a 4D project | Python |
| [4d-capture-gif](4d-capture-gif/SKILL.md) | Record a running 4D form window to an animated GIF (macOS) | 4D.app, Python |
| [4d-catalog](4d-catalog/SKILL.md) | Manage 4D base catalog files (.4DCatalog) | Python |
| [4d-check-syntax](4d-check-syntax/SKILL.md) | Compile a 4D project to check for syntax errors | [tool4d](#tool4d) |
| [4d-clean-project](4d-clean-project/SKILL.md) | Clean a 4D project by removing generated files and caches | Python |
| [4d-create-project](4d-create-project/SKILL.md) | Create a new 4D project from scratch | - |
| [4d-doc-coverage](4d-doc-coverage/SKILL.md) | Check that public 4D class methods/functions are documented | Python |
| [4d-doc-lookup](4d-doc-lookup/SKILL.md) | Look up 4D documentation for commands, classes, or language concepts | Python |
| [4d-find-command](4d-find-command/SKILL.md) | Find 4D commands by keyword | [tool4d](#tool4d), Python |
| [4d-form-layout](4d-form-layout/SKILL.md) | Design or refactor 4D forms via a relational intermediate JSON format | Python |
| [4d-form-screenshot](4d-form-screenshot/SKILL.md) | Capture a PNG screenshot for a specific 4D form | [tool4d](#tool4d) or 4D runtime |
| [4d-github-ci](4d-github-ci/SKILL.md) | Set up GitHub CI workflows, funding and Actions secrets for a 4D project | Python, gh CLI |
| [4d-project-info](4d-project-info/SKILL.md) | Analyze a 4D project and produce a structured summary | Python |
| [4d-publish-github](4d-publish-github/SKILL.md) | Publish a 4D project to GitHub with CI/CD workflows | Python |
| [4d-publish-gitlab](4d-publish-gitlab/SKILL.md) | Publish a 4D project to GitLab (gitlab.com or self-hosted) | Python |
| [4d-run](4d-run/SKILL.md) | Run a 4D method with tool4d or a user-provided 4D runtime path | [tool4d](#tool4d) or 4D runtime, Python |
| [4d-validate-form](4d-validate-form/SKILL.md) | Validate a .4DForm file against JSON schema | Python |

## Installation

### Using npx (Easiest)

One-command installation using the [skills CLI](https://github.com/vercel-labs/skills) (node must be installed).

```bash
npx skills add e-marchand/skills
```

### Quick Install All

Run this command in your project directory:

```bash
curl -fsSL https://raw.githubusercontent.com/e-marchand/skills/main/install.sh | bash
```

Or specify a target directory:

```bash
curl -fsSL https://raw.githubusercontent.com/e-marchand/skills/main/install.sh | bash -s -- /path/to/your/project
```

Or install **globally** (available across all projects):

```bash
curl -fsSL https://raw.githubusercontent.com/e-marchand/skills/main/install.sh | bash -s -- --global
```

Or use **symlink mode** --symlink (copy to first folder, symlink the rest)

The installer will:
- Detect existing `.claude`, `.github`, `.agent` or `.codex` folders (or their global equivalents with `--global`)
- If none found, prompt you to choose which one to create
- Download and install all skills to the appropriate location

### Manual Installation

Copy the skill folders to the appropriate location for your AI assistant:

| Assistant | Project Location | Global Location |
|-----------|------------------|-----------------|
| Claude Code | `.claude/skills/` | [Install from release](https://github.com/e-marchand/skills/releases) |
| GitHub Copilot | `.github/skills/` | `~/.github/skills/` |
| Antigravity | `.agent/skills/` | `~/.gemini/antigravity/global_skills/` |
| Codex | `.codex/skills/` | `~/.codex/skills/` |

## Requirements

### tool4d

Required by: [4d-check-syntax](4d-check-syntax/SKILL.md), [4d-find-command](4d-find-command/SKILL.md), [4d-form-screenshot](4d-form-screenshot/SKILL.md). Also used by [4d-run](4d-run/SKILL.md) when a dataless tool4d run is appropriate.

**Option 1: Install via Extension (Recommended)**

Install the [4D-Analyser extension](https://marketplace.visualstudio.com/items?itemName=4D.4d-analyzer) in VS Code or Antigravity. The extension will automatically install tool4d.

**Option 2: Set Environment Variable**

If you have tool4d installed elsewhere, set the `TOOL4D` environment variable to point to the tool4d executable:

```bash
export TOOL4D="/path/to/tool4d.app/Contents/MacOS/tool4d"
```

Add this to your `~/.zshrc` or `~/.bash_profile` to make it permanent.

### 4D.app

Required by: [4d-capture-gif](4d-capture-gif/SKILL.md) — headless `tool4d` shows no window, so a real 4D app is needed to film one.

Optional for: [4d-run](4d-run/SKILL.md) and [4d-form-screenshot](4d-form-screenshot/SKILL.md) when the method needs a real database or runtime features not available in tool4d.

The skill can:
- Use a user-provided `4D.app` path
- Use a user-provided `4D.exe` path on Windows
- Kill the launched process after a timeout if the startup method does not call `QUIT 4D`

### Other Requirements

- **Python 3**: Required by skills using Python scripts
- **Python packages**: [4d-capture-gif](4d-capture-gif/SKILL.md) also needs `pyobjc-framework-Quartz`, `pyobjc-framework-Cocoa` and `Pillow` (see [requirements.txt](4d-capture-gif/scripts/requirements.txt))
- **gh CLI**: Required by [4d-github-ci](4d-github-ci/SKILL.md) and [4d-publish-github](4d-publish-github/SKILL.md)
- **macOS**: Scripts are designed for macOS paths. Feel free to PR for other OS.

## What are Agent Skills?

See [ABOUT_SKILLS.md](ABOUT_SKILLS.md) for a detailed explanation of what Agent Skills are and how they work.

## Legal

This project is maintained by a 4D employee for development tasks but is not an official 4D product. It is provided as-is without warranty. 4D is a trademark of 4D SAS.

**Security Note**: Always review skill content before installation. Skills contain prompts and scripts that will be executed by your AI assistant and system. Be cautious when installing skills from untrusted sources, as malicious prompts or code injection is possible.
