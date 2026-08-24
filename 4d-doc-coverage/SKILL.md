---
name: 4d-doc-coverage
description: 'Check that public 4D class methods/functions are documented and report documentation gaps. Use when the user asks whether public API is documented, to find undocumented methods/functions/properties, audit doc coverage before a release/PR, or verify a new public member was added to Documentation/Classes. Runs a Python script that compares Project/Sources/Classes against Documentation/Classes.'
argument-hint: '[optional: class name to focus on]'
---

# 4D Documentation Coverage

## When to Use

- The user asks "is this public method/function documented?" or "did we forget to document X?".
- Auditing documentation gaps before a release or in a PR review.
- After adding or renaming a public class member, to confirm the Markdown docs were updated.
- Wiring a CI check that fails when a public member is undocumented.

## What It Checks

The repo convention this skill relies on:

| Concept | Rule |
|---------|------|
| Public class | `.4dm` file in `Project/Sources/Classes/` **not** starting with `_`. |
| Public member | `Function <name>` (or `Function get/set <name>` property) **not** starting with `_`. `Class constructor` is ignored. |
| Documentation | `Documentation/Classes/<ClassName>.md`. A member counts as documented when its name appears as a `### name` heading, a `**name**` bold signature, or a `` `name` `` inline-code cell in a property table. |

A "gap" is a public member with no matching entry in its class doc, or a public class with no doc file at all.

## Procedure

1. Run the checker from the repository root:

   ```bash
   python3 $SKILL_DIR/scripts/check_doc_coverage.py
   ```

   Add `--json` for machine-readable output, or `--root <path>` to point at a different checkout. The script exits `1` when any gap is found (CI-friendly), `0` when everything is documented.

2. Read the report. Each class is either `✓` (fully documented) or `✗` with the undocumented members listed as `name (kind, line N)`.

3. For each reported gap, decide with the user:
   - **Real gap** → open `Documentation/Classes/<ClassName>.md` and add a section for the member, following the existing style in that file (method → `### name()` + `**name**(...)` signature + tables; property → a row in the Properties/Computed properties table). Match the closest existing entry.
   - **Intentional** → if the member is public only for technical reasons and should not be documented, leave it; note the decision so it is not re-flagged repeatedly.

4. Re-run the script to confirm the gap is closed (exit `0`, class shows `✓`).

## Notes & Limitations

- Detection is heuristic (name presence, not signature accuracy). It confirms a member is *mentioned*, not that the signature or parameters are correct — a human should sanity-check the actual content.
- A member documented only in unrelated prose that happens to contain its name may be counted as documented; prefer real headings/tables when writing docs.
- The private convention is the leading underscore `_`; adjust the script arguments if a project uses a different convention.

See the implementation in [check_doc_coverage.py](./scripts/check_doc_coverage.py).
