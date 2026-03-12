---
name: 4d-run
description: Run a 4D project method. Use tool4d by default for fast dataless execution, and fall back to a user-provided 4D executable path when the method needs a real database or runtime features unavailable in tool4d. Includes Python helpers for macOS and Windows.
license: Apache 2.0
---

# 4D Method Runner

Run a 4D project method with the right runtime.

## Choose the Runtime First

- Use `tool4d` for most test-like runs, especially when `--dataless` is acceptable.
- If it is unclear whether the method needs the full runtime, try `tool4d` first. If that run fails for reasons that look specific to `tool4d` or missing database/runtime support, then switch to the full 4D runtime.
- Use the full 4D runtime when the method depends on a real data file, database state, UI/runtime features missing from `tool4d`, or the user explicitly says `tool4d` is insufficient.
- Do not try to discover the 4D runtime automatically. Ask the user for the path to `4D.app`, the inner `4D` binary, or `4D.exe`.

Prefer this fallback strategy because it is usually faster than deciding up front from incomplete context.

## Finding tool4d

tool4d can be located in two ways:

### 1. Environment Variable

Set `TOOL4D` to the tool4d executable:

```bash
export TOOL4D="/path/to/tool4d.app/Contents/MacOS/tool4d"
```

### 2. Auto-discovery from Extension

tool4d is typically installed by the 4D-Analyzer extension in one of these locations:
- VS Code: `$HOME/Library/Application Support/Code/User/globalStorage/4d.4d-analyzer/tool4d/`
- Antigravity: `$HOME/Library/Application Support/Antigravity/User/globalStorage/4d.4d-analyzer/tool4d/`

Use `scripts/find_tool4d.py` to return the newest installed executable.

```bash
python3 <skill-dir>/scripts/find_tool4d.py
```

The script checks:
- `TOOL4D`
- Standard 4D-Analyzer locations on macOS
- Standard 4D-Analyzer locations on Windows under `%APPDATA%` and `%LOCALAPPDATA%`

## Running with tool4d

```bash
"<tool4d_path>" --project="<project_path>" --startup-method="<method_name>" --skip-onstartup --dataless
```

Parameters:
- `--project`: Full path to the `.4DProject` file
- `--startup-method`: Method name without `.4dm`
- `--skip-onstartup`: Skip the database `On Startup`
- `--dataless`: Run without a data file

Example:

```bash
SKILL_DIR="/path/to/4d-run"
TOOL4D="$(python3 "$SKILL_DIR/scripts/find_tool4d.py")"
"$TOOL4D" --project="/path/to/MyProject/MyProject.4DProject" --startup-method="test_MyFeature" --skip-onstartup --dataless
```

## Running with the Full 4D Runtime

Ask the user for the 4D executable path first:
- macOS bundle: `/Applications/4D.app`
- macOS binary: `/Applications/4D.app/Contents/MacOS/4D`
- Windows binary: `C:\Program Files\4D\4D.exe`

Then run the helper:

```bash
SKILL_DIR="/path/to/4d-run"
python3 "$SKILL_DIR/scripts/run_with_4d.py" \
    "/Applications/4D.app" \
    "/path/to/MyProject/MyProject.4DProject" \
    "test_UsesDatabase"
```

`run_with_4d.py` launches the runtime, waits for it to exit, and kills it after `30` seconds by default if it is still running.

Important:
- Prefer startup methods that call `QUIT 4D` when the work is complete.
- If the method does not call `QUIT 4D`, the helper script will terminate the process after `FOURD_KILL_AFTER` seconds.
- Set `FOURD_KILL_AFTER=0` only when you intentionally want to leave 4D running.

Equivalent direct command if you already know the binary path:

```bash
"C:\Program Files\4D\4D.exe" \
    --project="/path/to/MyProject/MyProject.4DProject" \
    --startup-method="test_UsesDatabase" \
    --skip-onstartup
```

## Output Handling

- `tool4d` sends most diagnostic output to stderr.
- 4D may keep running after the method finishes unless the method explicitly calls `QUIT 4D`.
- `ALERT` is not reliable for automated runs. Prefer `LOG EVENT` or file output.

When deciding whether to fall back from `tool4d` to full 4D, treat these as fallback signals:
- The user already says the method touches the real database.
- The `tool4d` run fails and the failure points to forbidden methods, unavailable runtime features, UI dependencies, or missing access to the real data file.
- The `tool4d` run cannot complete the startup method even though the method name and project path are correct.

Do not fall back automatically for ordinary method bugs. If the method itself is wrong, report the failure instead of switching runtimes.

### Logging from 4D Code

Use `LOG EVENT` to output messages:

```4d
LOG EVENT(Into system standard outputs; "message"; Information message)
```

Or write to a file:

```4d
File("/path/to/debug.txt").setText($debugText)
```

## Workflow

1. Locate the `.4DProject` file.
2. Decide whether `tool4d` is clearly sufficient, clearly insufficient, or unclear.
3. If it is unclear, try `tool4d` first because that is usually the fastest path.
4. If `tool4d` succeeds, keep using it.
5. If `tool4d` fails for a likely runtime/database limitation, ask the user for the 4D executable path and retry with full 4D.
6. When using the full runtime, ensure the method calls `QUIT 4D` or use `scripts/run_with_4d.py` so the process gets cleaned up.
