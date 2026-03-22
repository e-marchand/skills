---
name: 4d-project-info
description: Analyze a 4D project and produce a structured summary. Use when the user wants to understand a 4D project's structure, get an overview of methods/classes/forms/dependencies, onboard onto a codebase, or when context about the project is needed before performing other tasks.
---

# 4D Project Info

Use the script instead of browsing the project first.

```bash
python3 scripts/project_info.py [path] --compact --sync-guidance
python3 scripts/project_info.py [path] --compact
python3 scripts/project_info.py [path]
```

- Omit `--compact` only for explicit analysis or deep dives.
- Use `--sync-guidance` to create or refresh a short `AGENTS.md` guide for a valid 4D project.
- If no 4D project is found, do not write guidance files.
