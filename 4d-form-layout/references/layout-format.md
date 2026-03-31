# Layout Format

## Overview

The intermediate format is a lossless, LLM-friendly JSON representation of a 4D form.

- `meta` identifies the layout format.
- `form` stores native root properties except `pages`.
- `pages[].elements[]` replaces `pages[].objects`.
- `pages[].role` makes page 0 semantics explicit for authoring.
- `layout.frame` preserves exact coordinates and dimensions for round-trip safety.
- `placement` and `align` express authoring intent in relational form.

## Canonical Shape

```json
{
  "meta": {
    "format": "4d-layout",
    "version": 1,
    "source4d": {
      "version": "1",
      "kind": "form"
    }
  },
  "form": {
    "windowTitle": "Example",
    "destination": "detailScreen",
    "rightMargin": 20,
    "bottomMargin": 20,
    "width": 400,
    "height": 300
  },
  "pages": [
    {
      "name": "page 0",
      "role": "shared",
      "elements": []
    },
    {
      "name": "page 1",
      "role": "page",
      "elements": [
        {
          "id": "input_email",
          "type": "input",
          "props": {
            "placeholder": "Email"
          },
          "layout": {
            "frame": {
              "top": 40,
              "left": 20,
              "width": 220,
              "height": 24
            }
          }
        },
        {
          "id": "submitButton",
          "type": "button",
          "props": {
            "text": "Submit"
          },
          "layout": {
            "placement": "below(input_email)",
            "align": "left",
            "marginTop": 12,
            "frame": {
              "width": 150,
              "height": 30
            }
          }
        }
      ],
      "entryOrder": [
        "input_email",
        "submitButton"
      ]
    }
  ]
}
```

## Element Fields

- `id`: native object-map key from `.4DForm`
- `type`: native 4D object type
- `props`: every non-layout property preserved verbatim
- `validation`: optional authoring-only validation metadata
- `layout.frame`: fallback frame data
- `layout.placement`: optional positional relation
- `layout.align`: optional axis alignment rule or array of rules

`validation` supports:

- `ignoreRules`: optional list of graphical validation rule names to skip for this element
- `notes`: optional authoring note about why a rule is ignored

## Page Fields

- `name`: optional human-readable page label such as `page 0` or `page 1`
- `role`: optional page meaning, either `shared` or `page`
- `elements`: ordered objects for that page
- `entryOrder`: optional native entry order for that page

For new forms:

- page index `0` is the shared page
- if the form has only one visible page, create an empty shared page 0 and put content on page 1
- if the form has tabs, shared chrome or buttons can live on page 0 and tab-specific content starts on page 1

When importing native `.4DForm`, the converter emits:

- `page 0` with role `shared`
- later pages with role `page`

## Placement Grammar

Supported v1 expressions:

- `below(id)`
- `above(id)`
- `rightOf(id)`
- `leftOf(id)`
- `centeredIn(parent)`

`parent` means the page container and requires `form.width` plus `form.height`.

## Align Grammar

Supported explicit alignment expressions:

- `alignedWith(id.left)`
- `alignedWith(id.centerX)`
- `alignedWith(id.right)`
- `alignedWith(id.top)`
- `alignedWith(id.centerY)`
- `alignedWith(id.bottom)`

Supported shorthand when `placement` already references an anchor:

- `left`
- `centerX`
- `right`
- `top`
- `centerY`
- `bottom`

The shorthand resolves against the `placement` target.

## Margins

Supported offset fields:

- `marginTop`
- `marginBottom`
- `marginLeft`
- `marginRight`

Use the margin that matches the relation direction:

- `below(id)` uses `marginTop`
- `above(id)` uses `marginBottom` or `marginTop`
- `rightOf(id)` uses `marginLeft`
- `leftOf(id)` uses `marginRight` or `marginLeft`

## Determinism Rules

- Keep page order exactly.
- Keep element order exactly.
- Keep `entryOrder` exactly.
- Always emit `id`, `type`, `props`, `layout` in that order.
- Always emit `frame` keys in this order when present:
  `top`, `left`, `width`, `height`, `right`, `bottom`
- Preserve unknown native properties inside `props`.

## Validation Rules

Use `references/validation-rules.yaml` with:

```bash
python skills/4d-form-layout/scripts/convert_4d_form.py \
  validate path/to/form.layout.json --all-rules

python skills/4d-form-layout/scripts/convert_4d_form.py \
  validate path/to/form.4DForm --rule shared_page_required

python skills/4d-form-layout/scripts/convert_4d_form.py \
  validate path/to/form.layout.json \
  --rule no_overlap \
  --rule inside_bounds \
  --rules-file skills/4d-form-layout/references/validation-rules.yaml
```

The graphical rules are opt-in because real forms may intentionally:

- overlap controls and toggle visibility at runtime
- place note text outside a strict visual frame

Use `validation.ignoreRules` on layout elements when a specific exception is intentional.
