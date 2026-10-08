---
name: 4d-form-widen
description: Widen a listbox (or any anchor object) in a 4D .4DForm and reflow the other objects horizontally — full-width objects grow, objects to its right shift, centered ones move by half. Use when the user wants more room for a list/listbox in a form.
license: Apache 2.0
---

# Widen a 4D form around an anchor object

Run the script (it rewrites the form in place, keeping 4D's tab-indented JSON):

```bash
python3 scripts/widen.py Project/Sources/Forms/<FORM>/form.4DForm <anchorName> <deltaPx> [--column <colName>] [--dry-run]
```

- Start with `--dry-run` to print what moves.
- For a listbox, the extra width goes to `--column` (default: widest column).
- Negative delta shrinks.

Rules applied to every page (page 0 included), relative to the anchor's original edges:

| Object                                   | Change               |
|------------------------------------------|----------------------|
| anchor                                   | width + delta        |
| starts at/after anchor right             | left + delta         |
| spans the anchor (left ≤ anchor left), or `sizingX: grow` | width + delta |
| starts inside, ends after (centered)     | left + delta/2       |
| ends before anchor right                 | unchanged            |

`windowMinWidth`/`width` on the form also grow by delta.

After running, check the form class and methods for hard-coded coordinates
(`OBJECT SET COORDINATES`, literal x positions) and adjust them by hand.
