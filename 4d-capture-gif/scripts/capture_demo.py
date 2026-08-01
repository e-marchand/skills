#!/usr/bin/env python3
"""
capture_demo.py — record a 4D form demo to an animated GIF (macOS).

It launches a 4D project on a given startup method, waits for the form window
to appear, optionally clicks a button, records the window frame by frame, kills
4D, and writes a GIF.

    python3 capture_demo.py \
        --project /path/to/Confetti/Project/Confetti.4DProject \
        --method  PLAY_Confetti \
        --click   Celebrate \
        --out     Confetti/Documentation/confetti.gif

How it works
------------
* Launch:  /Applications/4D.app  --project=… --startup-method=… --dataless
           --skip-onstartup   (a *real* window, unlike headless tool4d).
* Find:    the on-screen, layer-0 window owned by "4D" (largest, or the one
           whose title matches --title).  Uses CGWindowListCopyWindowInfo.
* Click:   the button is located *by its label* in the .4DForm, its centre is
           mapped from form coordinates to screen coordinates (the title-bar and
           border insets are derived from window-frame minus form content, so no
           magic numbers), 4D is brought to the front, and a HID mouse click is
           posted there.
* Record:  CGWindowListCreateImage grabs just that window — even if occluded —
           in-process, so it runs under the host app's Screen Recording grant.
* GIF:     frames are down-scaled off the Retina buffer and written with their
           real inter-frame timings.

Requirements
------------
* macOS with /Applications/4D.app
* pip install pyobjc-framework-Quartz pyobjc-framework-Cocoa Pillow
* The app that runs this script (Terminal / the Claude app / …) must hold the
  "Screen Recording" permission — System Settings ▸ Privacy & Security ▸ Screen
  Recording.  Without it every frame comes back black.
"""

import argparse
import json
import subprocess
import sys
import time

import Quartz
from Quartz import (
    CGWindowListCopyWindowInfo, kCGWindowListOptionOnScreenOnly, kCGNullWindowID,
    CGWindowListCreateImage, CGRectNull, kCGWindowListOptionIncludingWindow,
    kCGWindowImageBoundsIgnoreFraming,
    CGImageGetWidth, CGImageGetHeight, CGImageGetDataProvider,
    CGDataProviderCopyData, CGImageGetBytesPerRow,
    CGEventCreateMouseEvent, CGEventPost, kCGHIDEventTap,
    kCGEventLeftMouseDown, kCGEventLeftMouseUp, kCGEventMouseMoved,
    kCGMouseButtonLeft,
)
from AppKit import NSRunningApplication
from PIL import Image

FOURD_DEFAULT = "/Applications/4D.app/Contents/MacOS/4D"


# --------------------------------------------------------------------------- #
# window discovery
# --------------------------------------------------------------------------- #
def find_window(owner, min_area, title_substr=None, expect=None):
    """Return (window_id, bounds_dict, pid) of the best matching window, or None.

    With `expect=(w, h)` (the form's expected frame size) the window whose size is
    closest to it wins — so an incidental large 4D IDE window can't be mistaken for
    the demo form. Without it, the largest matching window wins."""
    best = None
    for w in CGWindowListCopyWindowInfo(kCGWindowListOptionOnScreenOnly, kCGNullWindowID):
        if (w.get("kCGWindowOwnerName") or "").lower() != owner.lower():
            continue
        if w.get("kCGWindowLayer") != 0:
            continue
        b = w.get("kCGWindowBounds") or {}
        W, H = b.get("Width", 0), b.get("Height", 0)
        if W * H < min_area:
            continue
        if title_substr and title_substr.lower() not in (w.get("kCGWindowName") or "").lower():
            continue
        if expect:
            score = -(abs(W - expect[0]) + abs(H - expect[1]))   # closest size wins
        else:
            score = W * H                                        # largest wins
        if best is None or score > best[3]:
            best = (w.get("kCGWindowNumber"), b, w.get("kCGWindowOwnerPID"), score)
    if best is None:
        return None
    return best[0], best[1], best[2]


# --------------------------------------------------------------------------- #
# capture
# --------------------------------------------------------------------------- #
def capture(window_id):
    """Grab the window as a PIL RGB image (Retina pixels), or None on failure."""
    img = CGWindowListCreateImage(
        CGRectNull, kCGWindowListOptionIncludingWindow, window_id,
        kCGWindowImageBoundsIgnoreFraming,
    )
    if img is None:
        return None
    w, h = CGImageGetWidth(img), CGImageGetHeight(img)
    if w == 0 or h == 0:
        return None
    data = CGDataProviderCopyData(CGImageGetDataProvider(img))
    bpr = CGImageGetBytesPerRow(img)
    return Image.frombuffer("RGBA", (w, h), bytes(data), "raw", "BGRA", bpr, 1).convert("RGB")


# --------------------------------------------------------------------------- #
# clicking
# --------------------------------------------------------------------------- #
def click(x, y):
    for kind in (kCGEventMouseMoved, kCGEventLeftMouseDown, kCGEventLeftMouseUp):
        CGEventPost(kCGHIDEventTap, CGEventCreateMouseEvent(None, kind, (x, y), kCGMouseButtonLeft))
        time.sleep(0.04)


def form_content_size(form):
    objs = form["pages"][1]["objects"]
    max_r = max(v["left"] + v.get("width", 0) for v in objs.values()
                if isinstance(v, dict) and isinstance(v.get("left"), (int, float)))
    max_b = max(v["top"] + v.get("height", 0) for v in objs.values()
                if isinstance(v, dict) and isinstance(v.get("top"), (int, float)))
    return (max_r + form.get("rightMargin", 0), max_b + form.get("bottomMargin", 0))


def form_object_center(form, label):
    """Return (cx, cy) in form points for the object whose text == label.

    Prefers a button; falls back to any object (e.g. a segment's text label that
    sits over a transparent click button)."""
    objs = form["pages"][1]["objects"]
    hit = None
    for v in objs.values():
        if isinstance(v, dict) and v.get("text") == label:
            if v.get("type") == "button":
                hit = v
                break
            hit = hit or v
    if hit is None:
        raise SystemExit(f"no object labelled {label!r} in the form")
    return (hit["left"] + hit.get("width", 0) / 2, hit["top"] + hit.get("height", 0) / 2)


def parse_click(spec, index, click_delay, click_gap):
    """'Label@1.2' | 'Label' | 'x,y@1.2' -> (delay_seconds, target) where target is
    a label string or a (x, y) tuple in form points."""
    delay = None
    target = spec
    if "@" in spec:
        head, tail = spec.rsplit("@", 1)
        try:
            delay = float(tail)
            target = head
        except ValueError:
            pass
    if delay is None:
        delay = click_delay + index * click_gap
    if "," in target and target.replace(",", "").replace(".", "").replace("-", "").isdigit():
        x, y = target.split(",")
        target = (float(x), float(y))
    return delay, target


def default_form_path(project):
    # …/Project/<Name>.4DProject  ->  …/Project/Sources/Forms/Demo/form.4DForm
    import os
    proj_dir = os.path.dirname(project)
    return os.path.join(proj_dir, "Sources", "Forms", "Demo", "form.4DForm")


# --------------------------------------------------------------------------- #
# main
# --------------------------------------------------------------------------- #
def main():
    ap = argparse.ArgumentParser(description="Record a 4D form demo window to a GIF (macOS).")
    ap.add_argument("--project", required=True, help="path to the .4DProject file")
    ap.add_argument("--method", required=True, help="startup method to run (e.g. PLAY_Confetti)")
    ap.add_argument("--out", required=True, help="output .gif path")
    ap.add_argument("--form", help="path to the .4DForm (default: <project>/Sources/Forms/Demo/form.4DForm)")
    ap.add_argument("--click", action="append", default=[],
                    help="a click, repeatable. 'Label' or 'Label@1.2' or 'x,y' or 'x,y@1.2' "
                         "(label looked up in the form; @ gives seconds into the recording)")
    ap.add_argument("--click-delay", type=float, default=0.7, help="delay of the first click without an explicit @time")
    ap.add_argument("--click-gap", type=float, default=0.6, help="spacing between clicks that have no explicit @time")
    ap.add_argument("--owner", default="4D", help="window owner name to match (default: 4D)")
    ap.add_argument("--title", help="substring the window title must contain (optional)")
    ap.add_argument("--fourd", default=FOURD_DEFAULT, help="path to the 4D executable")
    ap.add_argument("--settle", type=float, default=1.5, help="seconds to wait after the window appears")
    ap.add_argument("--duration", type=float, default=4.5, help="seconds to record")
    ap.add_argument("--fps", type=float, default=18.0, help="target capture frame rate")
    ap.add_argument("--width", type=int, default=520, help="output GIF width in px (height kept proportional)")
    ap.add_argument("--colors", type=int, default=128, help="GIF palette size")
    ap.add_argument("--crop-titlebar", action="store_true", help="drop the macOS title bar from the frames")
    ap.add_argument("--timeout", type=float, default=40.0, help="seconds to wait for the window")
    args = ap.parse_args()

    # resolve click targets against the form (label -> form coords, or explicit x,y)
    schedule = []          # list of [delay, form_point_or_None, label_or_None]
    content = None
    if args.click:
        form_path = args.form or default_form_path(args.project)
        form = json.load(open(form_path))
        content = form_content_size(form)
        for i, spec in enumerate(args.click):
            delay, target = parse_click(spec, i, args.click_delay, args.click_gap)
            point = target if isinstance(target, tuple) else form_object_center(form, target)
            schedule.append([delay, point, None if isinstance(target, tuple) else target])

    # 1. launch 4D on the demo method
    proc = subprocess.Popen([
        args.fourd, f"--project={args.project}",
        f"--startup-method={args.method}", "--dataless", "--skip-onstartup",
    ])
    print(f"launched 4D (pid {proc.pid}) on {args.method}")

    # 2. wait for the window (prefer the one matching the form's size, if known)
    expect = (content[0], content[1] + 34) if content else None
    win = None
    t0 = time.time()
    while time.time() - t0 < args.timeout:
        win = find_window(args.owner, min_area=100_000, title_substr=args.title, expect=expect)
        if win:
            break
        time.sleep(0.4)
    if not win:
        proc.terminate()
        raise SystemExit("timed out waiting for the form window")
    window_id, b, pid = win
    X, Y, W, H = b["X"], b["Y"], b["Width"], b["Height"]
    print(f"window {window_id}: frame ({X},{Y}) {W}x{H}")
    time.sleep(args.settle)

    # map each click point (form content coords -> screen), deriving insets from the frame
    if schedule:
        titlebar = H - content[1] if content else 28
        side = (W - content[0]) / 2 if content else 0
        schedule.sort(key=lambda c: c[0])
        for c in schedule:
            fx, fy = c[1]
            c[1] = (X + side + fx, Y + titlebar + fy)
            print(f"click @{c[0]:.1f}s -> {c[2] or 'xy'} at screen {tuple(round(v) for v in c[1])}")

    # bring 4D to the front so the clicks land on it
    app = NSRunningApplication.runningApplicationWithProcessIdentifier_(pid)
    if app:
        app.activateWithOptions_(1 << 1)  # NSApplicationActivateIgnoringOtherApps
        time.sleep(0.3)

    # 3. record, firing each scheduled click as its time comes
    frames, stamps = [], []
    pending = list(schedule)
    start = time.monotonic()
    next_tick = start
    while time.monotonic() - start < args.duration:
        elapsed = time.monotonic() - start
        while pending and elapsed >= pending[0][0]:
            click(*pending.pop(0)[1])
        im = capture(window_id)
        if im is not None:
            frames.append(im)
            stamps.append(time.monotonic())
        next_tick += 1.0 / args.fps
        sleep = next_tick - time.monotonic()
        if sleep > 0:
            time.sleep(sleep)
    print(f"captured {len(frames)} frames in {time.monotonic()-start:.1f}s")

    # 4. kill 4D
    proc.terminate()
    try:
        proc.wait(timeout=8)
    except subprocess.TimeoutExpired:
        proc.kill()

    if not frames:
        raise SystemExit("no frames captured — is Screen Recording permission granted to the host app?")

    # 5. build the GIF
    if args.crop_titlebar and content:
        scale = frames[0].width / W                      # Retina pixels per point
        top_px = int((H - content[1]) * scale)
        frames = [f.crop((0, top_px, f.width, f.height)) for f in frames]

    tgt_w = args.width
    tgt_h = round(frames[0].height * tgt_w / frames[0].width)
    frames = [f.resize((tgt_w, tgt_h), Image.LANCZOS).quantize(colors=args.colors, method=Image.MEDIANCUT)
              for f in frames]

    # real inter-frame durations (ms), clamped so a stall doesn't freeze the GIF
    durations = []
    for i in range(len(stamps)):
        dt = (stamps[i + 1] - stamps[i]) if i + 1 < len(stamps) else (1.0 / args.fps)
        durations.append(int(max(20, min(200, dt * 1000))))

    frames[0].save(
        args.out, save_all=True, append_images=frames[1:],
        duration=durations, loop=0, optimize=True, disposal=2,
    )
    import os
    print(f"wrote {args.out}  ({tgt_w}x{tgt_h}, {len(frames)} frames, {os.path.getsize(args.out)//1024} KB)")


if __name__ == "__main__":
    main()
