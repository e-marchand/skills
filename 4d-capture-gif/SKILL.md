---
name: 4d-capture-gif
description: Record a running 4D form window to an animated GIF (macOS). Use this skill when the user wants a GIF or video of a 4D demo/form in motion — a README animation, showing a button's effect, capturing an animation or transition. Launches /Applications/4D.app on a startup method, waits for the form window, optionally clicks buttons on a schedule, captures the window frame by frame with CGWindowListCreateImage, and writes a GIF. Not for a single still frame — use 4d-form-screenshot for that.
license: Apache 2.0
---

# 4D window → animated GIF

Record a 4D form **in motion** (slides, transitions, bursts, spinners) to a GIF.
`FORM SCREENSHOT` / the `4d-form-screenshot` skill only give a still frame and do
not run `On Load`; this skill runs the real app and films the window.

The engine is [`scripts/capture_demo.py`](scripts/capture_demo.py). It:

1. **Launches** `/Applications/4D.app` with `--startup-method=<method> --dataless
   --skip-onstartup` — a *real* window. (Headless `tool4d` shows nothing, so it
   cannot be used here.)
2. **Finds** the form window via `CGWindowListCopyWindowInfo` (owner `4D`, layer 0).
   When a `--click` is given, the form is read so the window whose size matches the
   form wins — an incidental 4D IDE window can't be mistaken for the demo.
3. **Clicks** (optional): a button is located *by its label in the `.4DForm`*, its
   centre mapped to screen coordinates (title-bar and border insets derived from
   frame − form content, no magic numbers), 4D is brought to the front, and a HID
   click is posted. Clicks are scheduled, so several can be staged.
4. **Records** with `CGWindowListCreateImage` **in-process** — this is essential:
   the `screencapture` CLI fails from a subprocess (wrong TCC attribution), whereas
   in-process capture runs under the host app's Screen Recording grant.
5. **Kills** 4D and writes the GIF (frames down-scaled off the Retina buffer, with
   their real inter-frame timings).

## Requirements (once)

- macOS with `/Applications/4D.app`.
- Python deps — install into a venv:

  ```bash
  python3 -m venv .venv && ./.venv/bin/pip install -r "$SKILL_DIR/scripts/requirements.txt"
  ```

- **Screen Recording permission** for the app that runs the script (the terminal /
  the Claude app / …). Without it every frame is black. Check and, if needed,
  prompt for it:

  ```python
  import Quartz
  print(Quartz.CGPreflightScreenCaptureAccess())   # True == granted
  Quartz.CGRequestScreenCaptureAccess()            # shows the system prompt
  ```

  If it is off, the user grants it in System Settings ▸ Privacy & Security ▸ Screen
  Recording and **restarts that app** (a fresh grant needs a relaunch). This is a
  security setting — you cannot toggle it for them.

## Usage

```bash
python "$SKILL_DIR/scripts/capture_demo.py" \
    --project /path/to/<Name>/Project/<Name>.4DProject \
    --method  PLAY_<Name> \
    --out     /path/to/<Name>/Documentation/<name>.gif \
    [--click "Label@1.2" ...] [--duration 4] [--fps 18] [--width 520] [--colors 128]
```

`--method` is the startup method that opens the form window (for these demos,
`PLAY_<Name>`, which the base's `On Startup` normally calls).

### No click — it animates on load

```bash
python "$SKILL_DIR/scripts/capture_demo.py" --project …/MatrixRain.4DProject \
    --method PLAY_MatrixRain --duration 4 --out MatrixRain/Documentation/matrixrain.gif
```

### One click

```bash
python "$SKILL_DIR/scripts/capture_demo.py" --project …/Confetti.4DProject \
    --method PLAY_Confetti --click Celebrate --duration 4.5 \
    --out Confetti/Documentation/confetti.gif
```

### Several clicks, staged (`Label@seconds`)

```bash
# three toasts stacking; then a segmented control's pill gliding across
--click "Success@0.5" --click "Info@1.2" --click "Error@1.9"
--click "Week@0.6" --click "Month@1.3" --click "Year@2.0" --click "Day@2.7"
```

A click target is a **label** looked up in the form (a button, or any object with
that text — e.g. a segment's text label sitting over a transparent click button),
or literal form-point coordinates `x,y`. Without an explicit `@time`, clicks are
spaced by `--click-gap` starting at `--click-delay`.

## Key options

| Option | Meaning |
|---|---|
| `--click` (repeatable) | `Label` \| `Label@1.2` \| `x,y` \| `x,y@1.2` |
| `--click-delay` / `--click-gap` | timing of clicks that have no explicit `@time` |
| `--duration` / `--fps` | length and frame rate of the recording |
| `--width` / `--colors` | GIF width (px) and palette size |
| `--settle` | pause after the window appears before recording (default 1.5 s) |
| `--title` | substring the window title must contain (disambiguation) |
| `--form` | explicit `.4DForm` path (default: `<project>/Sources/Forms/Demo/form.4DForm`) |
| `--crop-titlebar` | drop the macOS title bar from the frames |
| `--fourd` | path to the 4D executable (default `/Applications/4D.app/...`) |

## Tips

- **File size.** Scenes with constant motion (rain, spinners) can't dedup static
  frames, so their GIFs are larger — trim with `--colors 48 --fps 14 --width 440`.
  Scenes that settle (a toast that stops, a list that lands) stay small on their own.
- **Odd form path.** If the demo form is not `Forms/Demo/form.4DForm`, pass `--form`
  (e.g. MatrixRain's is `Forms/Rain/form.4DForm`).
- **Focus race.** The script brings 4D to the front before clicking; if a GIF ever
  comes out with no effect (the click was swallowed by window focus), just re-run.
- **Verify.** Read a few frames back to confirm motion before shipping:
  `Image.open(gif); g.seek(i); g.convert("RGB")`.
