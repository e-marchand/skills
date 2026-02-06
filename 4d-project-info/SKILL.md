---
name: 4d-project-info
description: Analyze a 4D project and produce a structured summary. Use when the user wants to understand a 4D project's structure, get an overview of methods/classes/forms/dependencies, onboard onto a codebase, or when context about the project is needed before performing other tasks.
---

# 4D Project Info

Analyze a 4D project and produce a JSON summary of its structure.

## Usage

```bash
python3 scripts/project_info.py [path] [--compact]
```

- `path`: Any path inside a 4D project (auto-detects project root). Defaults to current directory.
- `--compact`: Output only names and counts (fewer tokens). Use by default unless the user needs full detail.

## Output

### Compact mode (default, recommended)

```json
{
  "project_root": "/path/to/project",
  "settings": { "project_file": "MyProject.4DProject", "compatibility_version": 2100 },
  "summary": {
    "methods_count": 12,
    "classes_count": 5,
    "forms_count": 3,
    "database_methods": ["onStartup"],
    "has_catalog": true,
    "total_code_lines": 1847,
    "dependencies": { "file_exists": true, "dependencies": { "SemVer": { "github": "mesopelagique/SemVer" } } }
  },
  "method_names": ["test_Feature", "utils_helper"],
  "class_names": ["Employee", "DataStore"],
  "form_names": ["MainForm", "Dialog_Settings"]
}
```

### Full mode

Adds per-method line counts and per-class details (properties, functions, extends).

## When to Use

- Before any refactoring or migration task
- When the user asks "what's in this project?"
- To provide project context to other skills (e.g., 4d-migrate-syntax, 4d-generate-doc)
- When onboarding onto an unfamiliar 4D codebase
