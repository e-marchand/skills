#!/usr/bin/env python3
"""Widen an anchor object (typically a listbox) in a 4D .4DForm and reflow the rest.

Horizontal rules, relative to the anchor's original [left, right]:
  - the anchor itself                      -> width += delta
  - object starting at/after anchor right   -> left  += delta        (shifted)
  - object spanning the anchor horizontally -> width += delta        (full size)
    (or any sizingX "grow" object ending after the anchor)
  - other object ending after anchor right  -> left  += delta // 2   (centered)
  - everything else (left of the anchor)    -> unchanged
Form-level windowMinWidth / width grow by delta. A listbox column absorbs the
extra width (--column, default: the widest column).

Usage: widen.py FORM.4DForm ANCHOR DELTA [--column NAME] [--dry-run]
"""
import argparse
import json
import sys


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("form")
    ap.add_argument("anchor")
    ap.add_argument("delta", type=int)
    ap.add_argument("--column", help="listbox column receiving the extra width")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    d = args.delta

    with open(args.form, encoding="utf-8") as fh:
        raw = fh.read()
    form = json.loads(raw)

    pages = [p for p in form.get("pages", []) if p]
    anchor = next((p["objects"][args.anchor] for p in pages if args.anchor in p.get("objects", {})), None)
    if anchor is None:
        sys.exit(f"anchor object '{args.anchor}' not found")
    a_left = anchor["left"]
    a_right = a_left + anchor["width"]

    def shift(name, o, dx):
        o["left"] += dx
        if "right" in o:
            o["right"] += dx
        print(f"  shift  {name:28} left {o['left'] - dx} -> {o['left']}")

    def grow(name, o, dw):
        o["width"] += dw
        if "right" in o:
            o["right"] += dw
        print(f"  grow   {name:28} width {o['width'] - dw} -> {o['width']}")

    for page in pages:
        for name, o in page.get("objects", {}).items():
            if "left" not in o or "width" not in o:
                continue
            left, right = o["left"], o["left"] + o["width"]
            if o is anchor:
                grow(name, o, d)
                if o.get("type") == "listbox" and o.get("columns"):
                    cols = o["columns"]
                    col = next((c for c in cols if c.get("name") == args.column), None) if args.column \
                        else max(cols, key=lambda c: c.get("width", 0))
                    if col is None:
                        sys.exit(f"column '{args.column}' not found")
                    grow(f"{name}.{col.get('name')}", col, d)
            elif left >= a_right:
                shift(name, o, d)
            elif right <= a_right:
                continue
            elif left <= a_left or o.get("sizingX") == "grow":
                grow(name, o, d)
            else:
                shift(name, o, d // 2)

    for key in ("windowMinWidth", "width"):
        if key in form:
            form[key] += d
            print(f"  form   {key:28} {form[key] - d} -> {form[key]}")

    out = json.dumps(form, indent="\t", ensure_ascii=False)
    if raw.endswith("\n"):
        out += "\n"
    if not args.dry_run:
        with open(args.form, "w", encoding="utf-8") as fh:
            fh.write(out)


if __name__ == "__main__":
    main()
