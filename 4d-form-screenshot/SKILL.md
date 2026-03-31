---
name: 4d-form-screenshot
description: Capture a PNG screenshot of a specific 4D form from the current project. Use this skill when the user wants a preview image for a form name or a form.4DForm path. Copies assets/_formScreenshot.4dm into the project if missing, passes the form input through --user-param, and retries after copying assets/defaultJsonForm.json into the runtime Resources folder when that file is missing.
license: Apache 2.0
---

# 4D Form Screenshot

Capture a screenshot for a specific form and save it as `Project/Sources/Forms/<FormName>/form.png`.

## Inputs

Accept either:
- A form name such as `Form1`
- A path to `form.4DForm` such as `Project/Sources/Forms/Form1/form.4DForm`
- A path to the form folder if that folder contains `form.4DForm`

Pass the raw form input through `--user-param`. The bundled `_formScreenshot.4dm` resolves a `form.4DForm` path to the form name before calling `FORM SCREENSHOT`.

## Use /4d-run

Use the `/4d-run` skill to locate `tool4d` and to run the startup method.

## Workflow

1. Locate the current `.4DProject`.
2. Copy `assets/_formScreenshot.4dm` to `Project/Sources/Methods/_formScreenshot.4dm` if it is missing.
3. Keep the user input unchanged and pass it as `--user-param=<form name or path>`.
4. Use `/4d-run` to run `_formScreenshot` on the current project.
5. Prefer `tool4d` first. If `/4d-run` needs the full 4D runtime, use the user-provided 4D executable path through `/4d-run`.
6. If the run crashes because `defaultJsonForm.json` is missing, copy `assets/defaultJsonForm.json` into the `Resources` folder of the runtime being used, then retry.
7. Return the generated screenshot path: `Project/Sources/Forms/<FormName>/form.png`.

## Missing defaultJsonForm.json

Some runtimes crash on `FORM SCREENSHOT` when `defaultJsonForm.json` is missing.

When that happens:
- If `/4d-run` is using `tool4d.app`, copy the bundled `assets/defaultJsonForm.json` to `tool4d.app/Contents/Resources/defaultJsonForm.json`
- Retry the same `_formScreenshot` run afterward
