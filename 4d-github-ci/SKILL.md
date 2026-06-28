---
name: 4d-github-ci
description: Set up GitHub CI for a 4D project. Copies the build/release GitHub Actions workflows into a target 4D project, generating the dependency "Check out" steps from Project/Sources/dependencies.json, writes FUNDING.yml when a funding section exists in private config.yml, and can push Actions secrets (including DLTK) via gh from that same config (values never printed). Use when the user wants to configure GitHub CI, add the build/release workflows, set up funding, set Action secrets, or bootstrap GitHub Actions for a new or existing 4D project.
---

# 4D GitHub CI Setup

## 1. Generate and copy the CI files

```bash
python "$SKILL_DIR/scripts/install_ci.py" --project /path/to/4d-project
```

install_ci.py generates workflows and may omit the full DLTK build block from
release.yml (`product-line`, `version`, `build`, `token`) when
`secrets.DLTK` is absent or still a placeholder in config.yml. Secret values
are never printed.

## 2. Push Actions secrets (optional)

```bash
python "$SKILL_DIR/scripts/set_secrets.py" --project /path/to/4d-project
# or target explicitly:
python "$SKILL_DIR/scripts/set_secrets.py" --repo OWNER/REPO
```

If config.yml has no `secrets` section (or no DLTK), skip this step.

## Security — do not read the config

- **Never read, open, or print `assets/config.yml`.** It holds the DLTK token.
  Only the scripts read it; the secret only ever moves through `gh` via stdin.
  `config.yml` is git-ignored.
- Do not echo the DLTK value, pass it as a CLI argument, or place it in a
  commit, workflow file, or chat message.

## Notes

- `$SKILL_DIR` is this skill's directory: for instance `~/.claude/skills/4d-github-ci`.
- Edit `funding:` in config.yml to change the funding handle for all future
  projects (supports github, patreon, open_collective, ko_fi, custom, ...).
