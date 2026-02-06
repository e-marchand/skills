---
name: 4d-publish-gitlab
description: Publish a 4D project to GitLab using glab CLI. Use this skill when the user wants to publish, push, or share a 4D project to GitLab. Creates remote repository, initializes git, and pushes code. Supports gitlab.com and private/self-hosted GitLab instances with group/namespace support.
license: Apache 2.0
---

# 4D Publish to GitLab

Publish a 4D project to GitLab with support for gitlab.com and self-hosted instances.

## Script

### publish.py - Publish to GitLab

Creates GitLab repository from 4D project.

**Interactive mode:**
```bash
python3 "<skill_path>/scripts/publish.py"
```

**Non-interactive mode (with arguments):**
```bash
python3 "<skill_path>/scripts/publish.py" --yes [options]
```

| Argument | Description |
|----------|-------------|
| `--yes`, `-y` | Non-interactive mode |
| `--public` | Create public repository (default: private) |
| `--description "..."`, `-d` | Repository description |
| `--hostname` | GitLab instance hostname (default: gitlab.com) |
| `--group`, `-g` | GitLab group/namespace for the repository |

**Examples:**
```bash
# Interactive
python3 publish.py

# Private repo on gitlab.com, no questions
python3 publish.py --yes

# Public repo with description
python3 publish.py --yes --public --description "My 4D component"

# Self-hosted GitLab instance
python3 publish.py --yes --hostname gitlab.example.com

# Under a group namespace
python3 publish.py --yes --group my-team

# Self-hosted + group
python3 publish.py --yes --hostname gitlab.example.com --group my-team --description "Shared component"
```
