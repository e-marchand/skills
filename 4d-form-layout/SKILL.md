---
name: 4d-form-layout
description: Design or refactor 4D forms through a relational intermediate JSON format and deterministic Python conversion to or from `.4DForm`. Use when Codex needs to create a new 4D form, convert an existing `.4DForm` into an LLM-friendly ordered layout file, preserve round-trip fidelity while editing positions relationally, or validate generated forms against the bundled schema reference.
---

# 4D Form Layout

Use this skill to author 4D forms in a lossless intermediate JSON format, then convert that format back to native `.4DForm`.

## Quick Start

1. Start from a native form or a new layout JSON.
2. Convert with `scripts/convert_4d_form.py`.
3. Validate the layout and generated `.4DForm`.
4. Validate the layout against the bundled schema.

```bash
python skills/4d-form-layout/scripts/convert_4d_form.py \
  form-to-layout path/to/form.4DForm path/to/form.layout.json

python skills/4d-form-layout/scripts/convert_4d_form.py \
  layout-to-form path/to/form.layout.json path/to/form.4DForm

python skills/4d-form-layout/scripts/convert_4d_form.py \
  validate path/to/form.layout.json

python skills/4d-form-layout/scripts/convert_4d_form.py \
  validate path/to/form.4DForm --all-rules

python skills/4d-form-layout/scripts/convert_4d_form.py \
  validate path/to/form.layout.json --rule no_overlap --rule inside_bounds
```

## Workflow

When converting an existing `.4DForm`:

- Keep root form metadata in `form`.
- Keep page order and object order exactly.
- Convert each object key in `pages[].objects` into `elements[].id`.
- Move positional keys into `layout.frame`.
- Infer `placement` and `align` heuristically when relations are obvious.
- Preserve `layout.frame` for every element so round-trip remains exact.

When authoring a new layout JSON:

- Model pages explicitly. Use page 0 as the shared page.
- If the form has one visible page, create an empty shared page 0 and put visible content on page 1.
- If the form uses tabs, keep shared chrome or shared buttons on page 0 and start tab content on page 1.
- Define `id`, `type`, `props`, and `layout` for each element.
- Use `layout.placement` for positional relations such as `below(input_email)`.
- Use `layout.align` for axis alignment. Accept `alignedWith(target.left)` and shorthand such as `left` or `top` when the placement target is the anchor.
- Always provide `layout.frame.width` and `layout.frame.height`.
- Add `layout.frame.top` or `layout.frame.left` only when a relation does not determine that axis.
- Use `references/design-rules.md` as a reference for spacing and alignment best practices.

## Validation

Use these bundled sources while designing or reviewing a form:

- Schema: `references/formsSchema.json`
- Default property reference: `references/defaultJsonForm.json`
- Layout format reference: `references/layout-format.md`
- Graphical validation rules: `references/validation-rules.yaml`

`validate` checks:

- the intermediate layout JSON shape
- semantic relation rules and anchor resolution
- the generated native `.4DForm` against `references/formsSchema.json`
- optional graphical rules against either a layout JSON input or a native `.4DForm` input

Graphical validation is opt-in:

- `--rule rule_name` runs one or more named rules
- `--all-rules` runs every rule in `references/validation-rules.yaml`
- `--rules-file path/to/file.yaml` uses a custom `4d-validation` rule file

Current bundled graphical rules:

- `shared_page_required`
- `no_overlap`
- `consistent_spacing`
- `alignment_consistency`
- `inside_bounds`

## Notes

- Keep the intermediate file JSON-only in v1.
- Prefer editing the layout file, not absolute coordinates in `.4DForm`.
- Preserve unsupported properties verbatim in `props`; do not redesign them.
- Treat page 0 as the shared page when generating new forms.
- Treat relation targets as ordered dependencies: reference earlier elements on the same page.
- Graphical rules are heuristics. Use them selectively and ignore them per element when a form intentionally breaks a visual rule.
