#!/usr/bin/env python3
"""Convert between native 4DForm JSON and a relational layout JSON."""

from __future__ import annotations

import argparse
import json
import re
import sys
from itertools import combinations
from pathlib import Path
from typing import Any

import jsonschema
import yaml


LAYOUT_FORMAT = "4d-layout"
LAYOUT_VERSION = 1
FRAME_KEYS = ("top", "left", "width", "height", "right", "bottom")
ALIGN_AXES = {"left", "centerX", "right", "top", "centerY", "bottom"}
PLACEMENT_RE = re.compile(r"^(below|above|rightOf|leftOf|centeredIn)\(([^()]+)\)$")
ALIGN_RE = re.compile(r"^alignedWith\(([A-Za-z0-9_@ .:-]+)\.(left|centerX|right|top|centerY|bottom)\)$")
SHORT_ALIGN_RE = re.compile(r"^(left|centerX|right|top|centerY|bottom)$")

SCRIPT_PATH = Path(__file__).resolve()
SKILL_ROOT = SCRIPT_PATH.parents[1]
FORM_SCHEMA_PATH = SKILL_ROOT / "references" / "formsSchema.json"
DESIGN_RULES_PATH = SKILL_ROOT / "references" / "design-rules.md"
VALIDATION_RULES_PATH = SKILL_ROOT / "references" / "validation-rules.yaml"


class ConversionError(Exception):
    """Raised when the layout cannot be converted deterministically."""


LAYOUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["meta", "form", "pages"],
    "additionalProperties": False,
    "properties": {
        "meta": {
            "type": "object",
            "required": ["format", "version"],
            "additionalProperties": True,
            "properties": {
                "format": {"const": LAYOUT_FORMAT},
                "version": {"const": LAYOUT_VERSION},
                "source4d": {"type": "object"},
            },
        },
        "form": {"type": "object"},
        "pages": {
            "type": "array",
            "items": {
                "oneOf": [
                    {"type": "null"},
                    {
                        "type": "object",
                        "required": ["elements"],
                        "additionalProperties": False,
                        "properties": {
                            "name": {"type": "string"},
                            "role": {"enum": ["shared", "page"]},
                            "nullPage": {"type": "boolean"},
                            "elements": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "required": ["id", "type", "props", "layout"],
                                    "additionalProperties": False,
                                    "properties": {
                                        "id": {"type": "string", "minLength": 1},
                                        "type": {"type": "string", "minLength": 1},
                                        "props": {"type": "object"},
                                        "validation": {
                                            "type": "object",
                                            "additionalProperties": False,
                                            "properties": {
                                                "ignoreRules": {
                                                    "type": "array",
                                                    "items": {"type": "string"},
                                                },
                                                "notes": {"type": "string"},
                                            },
                                        },
                                        "layout": {
                                            "type": "object",
                                            "required": ["frame"],
                                            "additionalProperties": False,
                                            "properties": {
                                                "placement": {"type": "string"},
                                                "align": {
                                                    "oneOf": [
                                                        {"type": "string"},
                                                        {
                                                            "type": "array",
                                                            "items": {"type": "string"},
                                                        },
                                                    ]
                                                },
                                                "marginTop": {"type": "integer"},
                                                "marginBottom": {"type": "integer"},
                                                "marginLeft": {"type": "integer"},
                                                "marginRight": {"type": "integer"},
                                                "frame": {
                                                    "type": "object",
                                                    "required": ["width", "height"],
                                                    "additionalProperties": False,
                                                    "properties": {
                                                        "top": {"type": "integer"},
                                                        "left": {"type": "integer"},
                                                        "width": {"type": "integer", "minimum": 0},
                                                        "height": {"type": "integer", "minimum": 0},
                                                        "right": {"type": "integer"},
                                                        "bottom": {"type": "integer"},
                                                    },
                                                },
                                            },
                                        },
                                    },
                                },
                            },
                            "entryOrder": {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                        },
                    },
                ]
            },
        },
    },
}


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def dump_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent="\t", ensure_ascii=True)
        handle.write("\n")


def load_yaml(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def native_form_schema() -> dict[str, Any]:
    return load_json(FORM_SCHEMA_PATH)


def validate_native_form(native_form: dict[str, Any]) -> None:
    schema = native_form_schema()
    validator = jsonschema.Draft4Validator(schema)
    errors = sorted(validator.iter_errors(native_form), key=lambda err: list(err.absolute_path))
    if errors:
        first = errors[0]
        path = ".".join(str(part) for part in first.absolute_path) or "<root>"
        raise ConversionError(f"Generated .4DForm does not match schema at {path}: {first.message}")


def validate_layout_shape(layout_doc: dict[str, Any]) -> None:
    validator = jsonschema.Draft202012Validator(LAYOUT_SCHEMA)
    errors = sorted(validator.iter_errors(layout_doc), key=lambda err: list(err.absolute_path))
    if errors:
        first = errors[0]
        path = ".".join(str(part) for part in first.absolute_path) or "<root>"
        raise ConversionError(f"Layout JSON does not match schema at {path}: {first.message}")


def validate_layout_semantics(layout_doc: dict[str, Any]) -> None:
    for page_index, page in enumerate(layout_doc["pages"]):
        if page is None:
            continue
        role = page.get("role")
        if role == "shared" and page_index != 0:
            raise ConversionError("Only page 0 can use role 'shared'")
        elements = page["elements"]
        ids = [element["id"] for element in elements]
        if len(ids) != len(set(ids)):
            raise ConversionError(f"Page {page_index + 1}: duplicate element ids are not allowed")

        for element in elements:
            reserved = (set(FRAME_KEYS) | {"type"}) & set(element["props"])
            if reserved:
                reserved_list = ", ".join(sorted(reserved))
                raise ConversionError(
                    f"Page {page_index + 1}, element '{element['id']}': props contains reserved "
                    f"layout key(s): {reserved_list}"
                )

        if "entryOrder" in page:
            unknown = [name for name in page["entryOrder"] if name not in ids]
            if unknown:
                joined = ", ".join(unknown)
                raise ConversionError(
                    f"Page {page_index + 1}: entryOrder references unknown element id(s): {joined}"
                )

            ignore_rules = element.get("validation", {}).get("ignoreRules", [])
            if len(ignore_rules) != len(set(ignore_rules)):
                raise ConversionError(
                    f"Page {page_index + 1}, element '{element['id']}': validation.ignoreRules "
                    "contains duplicates"
                )


def ordered_frame(frame: dict[str, Any]) -> dict[str, Any]:
    return {key: frame[key] for key in FRAME_KEYS if key in frame}


def normalize_aligns(raw: Any) -> list[str]:
    if raw is None:
        return []
    if isinstance(raw, str):
        return [raw]
    return list(raw)


def compact_align_output(aligns: list[str]) -> Any:
    if not aligns:
        return None
    if len(aligns) == 1:
        return aligns[0]
    return aligns


def parse_placement(expr: str, *, page_index: int, element_id: str) -> tuple[str, str]:
    match = PLACEMENT_RE.fullmatch(expr)
    if not match:
        raise ConversionError(
            f"Page {page_index + 1}, element '{element_id}': invalid placement '{expr}'"
        )
    kind, target = match.groups()
    return kind, target.strip()


def parse_align_rule(
    rule: str,
    *,
    placement_target: str | None,
    page_index: int,
    element_id: str,
) -> tuple[str, str]:
    match = ALIGN_RE.fullmatch(rule)
    if match:
        target_id, axis = match.groups()
        return target_id.strip(), axis
    short = SHORT_ALIGN_RE.fullmatch(rule)
    if short:
        if placement_target is None:
            raise ConversionError(
                f"Page {page_index + 1}, element '{element_id}': shorthand align '{rule}' "
                "requires a placement target"
            )
        return placement_target, short.group(1)
    raise ConversionError(
        f"Page {page_index + 1}, element '{element_id}': invalid align rule '{rule}'"
    )


def normalize_source4d(source4d: Any) -> dict[str, Any]:
    if isinstance(source4d, dict) and source4d:
        return dict(source4d)
    return {"version": "1", "kind": "form"}


def infer_relations(
    current_frame: dict[str, Any],
    previous_elements: list[dict[str, Any]],
    form_props: dict[str, Any],
) -> tuple[str | None, list[str], dict[str, int]]:
    placement = None
    aligns: list[str] = []
    margins: dict[str, int] = {}

    top = current_frame.get("top")
    left = current_frame.get("left")
    width = current_frame.get("width")
    height = current_frame.get("height")
    if top is None or left is None or width is None or height is None:
        return placement, aligns, margins

    form_width = form_props.get("width")
    form_height = form_props.get("height")
    if isinstance(form_width, int) and isinstance(form_height, int):
        centered_x = left * 2 + width == form_width
        centered_y = top * 2 + height == form_height
        if centered_x and centered_y:
            return "centeredIn(parent)", aligns, margins

    vertical_candidates: list[tuple[int, dict[str, Any]]] = []
    horizontal_candidates: list[tuple[int, dict[str, Any]]] = []
    left_candidates: list[dict[str, Any]] = []

    for prev in previous_elements:
        prev_frame = prev["layout"]["frame"]
        prev_top = prev_frame.get("top")
        prev_left = prev_frame.get("left")
        prev_width = prev_frame.get("width")
        prev_height = prev_frame.get("height")
        if None in (prev_top, prev_left, prev_width, prev_height):
            continue
        if prev_left == left:
            gap = top - (prev_top + prev_height)
            if gap >= 0:
                vertical_candidates.append((gap, prev))
            left_candidates.append(prev)
        if prev_top == top:
            gap = left - (prev_left + prev_width)
            if gap >= 0:
                horizontal_candidates.append((gap, prev))

    if vertical_candidates:
        gap, ref = min(vertical_candidates, key=lambda item: item[0])
        placement = f"below({ref['id']})"
        aligns.append(f"alignedWith({ref['id']}.left)")
        if gap:
            margins["marginTop"] = gap
        return placement, aligns, margins

    if horizontal_candidates:
        gap, ref = min(horizontal_candidates, key=lambda item: item[0])
        placement = f"rightOf({ref['id']})"
        aligns.append(f"alignedWith({ref['id']}.top)")
        if gap:
            margins["marginLeft"] = gap
        return placement, aligns, margins

    if left_candidates:
        ref = min(left_candidates, key=lambda item: abs(top - item["layout"]["frame"]["top"]))
        aligns.append(f"alignedWith({ref['id']}.left)")

    return placement, aligns, margins


def native_form_to_layout(native_form: dict[str, Any]) -> dict[str, Any]:
    validate_native_form(native_form)

    meta: dict[str, Any] = {"format": LAYOUT_FORMAT, "version": LAYOUT_VERSION}
    if "$4d" in native_form:
        meta["source4d"] = dict(native_form["$4d"])

    form_props = {
        key: native_form[key]
        for key in native_form
        if key not in {"$4d", "pages"}
    }

    pages_out: list[Any] = []
    for page in native_form.get("pages", []):
        if page is None:
            pages_out.append(None)
            continue

        page_index = len(pages_out)
        page_out: dict[str, Any] = {
            "name": f"page {page_index}",
            "role": "shared" if page_index == 0 else "page",
            "elements": [],
        }
        objects = page.get("objects", {})
        previous_elements: list[dict[str, Any]] = []
        for element_id, native_object in objects.items():
            frame = ordered_frame({key: native_object[key] for key in FRAME_KEYS if key in native_object})
            props = {
                key: native_object[key]
                for key in native_object
                if key not in set(FRAME_KEYS) | {"type"}
            }

            placement, aligns, margins = infer_relations(frame, previous_elements, form_props)
            layout: dict[str, Any] = {}
            if placement is not None:
                layout["placement"] = placement
            compact_align = compact_align_output(aligns)
            if compact_align is not None:
                layout["align"] = compact_align
            layout.update(margins)
            layout["frame"] = frame

            element = {
                "id": element_id,
                "type": native_object["type"],
                "props": props,
                "layout": layout,
            }
            page_out["elements"].append(element)
            previous_elements.append(element)

        if "entryOrder" in page:
            page_out["entryOrder"] = list(page["entryOrder"])
        pages_out.append(page_out)

    return {"meta": meta, "form": form_props, "pages": pages_out}


def ensure_unique_ids(elements: list[dict[str, Any]], page_index: int) -> None:
    seen: set[str] = set()
    for element in elements:
        element_id = element["id"]
        if element_id in seen:
            raise ConversionError(f"Page {page_index + 1}: duplicate element id '{element_id}'")
        seen.add(element_id)


def resolve_parent_center(
    form_props: dict[str, Any],
    axis: str,
    size: int,
    *,
    page_index: int,
    element_id: str,
) -> int:
    form_width = form_props.get("width")
    form_height = form_props.get("height")
    if not isinstance(form_width, int) or not isinstance(form_height, int):
        raise ConversionError(
            f"Page {page_index + 1}, element '{element_id}': centeredIn(parent) requires "
            "form.width and form.height"
        )
    if axis == "x":
        return (form_width - size) // 2
    return (form_height - size) // 2


def resolve_target(
    target_id: str,
    resolved: dict[str, dict[str, int]],
    element_positions: dict[str, int],
    current_index: int,
    *,
    page_index: int,
    element_id: str,
    relation: str,
) -> dict[str, int]:
    if target_id == "parent":
        raise ConversionError(
            f"Page {page_index + 1}, element '{element_id}': '{relation}' cannot target parent here"
        )
    if target_id not in element_positions:
        raise ConversionError(
            f"Page {page_index + 1}, element '{element_id}': target '{target_id}' in '{relation}' does not exist"
        )
    if element_positions[target_id] >= current_index:
        raise ConversionError(
            f"Page {page_index + 1}, element '{element_id}': target '{target_id}' in '{relation}' "
            "must reference an earlier element on the page"
        )
    return resolved[target_id]


def resolve_element_frame(
    element: dict[str, Any],
    resolved: dict[str, dict[str, int]],
    element_positions: dict[str, int],
    current_index: int,
    form_props: dict[str, Any],
    page_index: int,
) -> dict[str, int]:
    element_id = element["id"]
    layout = element["layout"]
    frame_in = layout["frame"]
    width = frame_in["width"]
    height = frame_in["height"]
    top = frame_in.get("top")
    left = frame_in.get("left")
    right = frame_in.get("right")
    bottom = frame_in.get("bottom")
    placement_target: str | None = None

    placement = layout.get("placement")
    if placement:
        kind, target = parse_placement(placement, page_index=page_index, element_id=element_id)
        placement_target = target
        if kind == "centeredIn":
            if target != "parent":
                raise ConversionError(
                    f"Page {page_index + 1}, element '{element_id}': centeredIn only supports parent"
                )
            left = resolve_parent_center(
                form_props, "x", width, page_index=page_index, element_id=element_id
            )
            top = resolve_parent_center(
                form_props, "y", height, page_index=page_index, element_id=element_id
            )
        else:
            ref = resolve_target(
                target,
                resolved,
                element_positions,
                current_index,
                page_index=page_index,
                element_id=element_id,
                relation=placement,
            )
            if kind == "below":
                top = ref["top"] + ref["height"] + layout.get("marginTop", 0)
            elif kind == "above":
                margin = layout.get("marginBottom", layout.get("marginTop", 0))
                top = ref["top"] - height - margin
            elif kind == "rightOf":
                left = ref["left"] + ref["width"] + layout.get("marginLeft", 0)
            elif kind == "leftOf":
                margin = layout.get("marginRight", layout.get("marginLeft", 0))
                left = ref["left"] - width - margin

    for rule in normalize_aligns(layout.get("align")):
        target_id, axis = parse_align_rule(
            rule,
            placement_target=placement_target,
            page_index=page_index,
            element_id=element_id,
        )
        ref = resolve_target(
            target_id,
            resolved,
            element_positions,
            current_index,
            page_index=page_index,
            element_id=element_id,
            relation=rule,
        )
        if axis == "left":
            left = ref["left"]
        elif axis == "centerX":
            left = ref["left"] + (ref["width"] - width) // 2
        elif axis == "right":
            left = ref["left"] + ref["width"] - width
        elif axis == "top":
            top = ref["top"]
        elif axis == "centerY":
            top = ref["top"] + (ref["height"] - height) // 2
        elif axis == "bottom":
            top = ref["top"] + ref["height"] - height

    if top is None:
        raise ConversionError(
            f"Page {page_index + 1}, element '{element_id}': top could not be resolved"
        )
    if left is None:
        raise ConversionError(
            f"Page {page_index + 1}, element '{element_id}': left could not be resolved"
        )

    frame_out = {"top": top, "left": left, "width": width, "height": height}
    if right is not None:
        frame_out["right"] = right
    if bottom is not None:
        frame_out["bottom"] = bottom
    return frame_out


def layout_to_native_form(layout_doc: dict[str, Any]) -> dict[str, Any]:
    root: dict[str, Any] = {"$4d": normalize_source4d(layout_doc["meta"].get("source4d"))}
    for key, value in layout_doc["form"].items():
        root[key] = value

    pages_out, _ = resolve_layout_pages(layout_doc)
    root["pages"] = pages_out
    validate_native_form(root)
    return root


def resolve_layout_pages(layout_doc: dict[str, Any]) -> tuple[list[Any], list[Any]]:
    validate_layout_shape(layout_doc)
    validate_layout_semantics(layout_doc)

    pages_out: list[Any] = []
    resolved_pages: list[Any] = []
    for page_index, page in enumerate(layout_doc["pages"]):
        if page is None or page.get("nullPage"):
            pages_out.append(None)
            resolved_pages.append(None)
            continue

        elements = list(page["elements"])
        ensure_unique_ids(elements, page_index)
        positions = {element["id"]: index for index, element in enumerate(elements)}

        resolved_frames: dict[str, dict[str, int]] = {}
        objects_out: dict[str, Any] = {}
        resolved_elements: list[dict[str, Any]] = []
        for index, element in enumerate(elements):
            frame = resolve_element_frame(
                element,
                resolved_frames,
                positions,
                index,
                layout_doc["form"],
                page_index,
            )
            resolved_frames[element["id"]] = frame
            native_object = {"type": element["type"]}
            native_object.update(frame)
            native_object.update(element["props"])
            objects_out[element["id"]] = native_object
            resolved_element = {
                "id": element["id"],
                "type": element["type"],
                "props": element["props"],
                "layout": element["layout"],
                "resolvedFrame": frame,
            }
            if "validation" in element:
                resolved_element["validation"] = element["validation"]
            resolved_elements.append(resolved_element)

        page_out: dict[str, Any] = {"objects": objects_out}
        if "entryOrder" in page:
            page_out["entryOrder"] = list(page["entryOrder"])
        pages_out.append(page_out)
        resolved_page = {
            "name": page.get("name", f"page {page_index}"),
            "role": page.get("role", "shared" if page_index == 0 else "page"),
            "elements": resolved_elements,
        }
        if "entryOrder" in page:
            resolved_page["entryOrder"] = list(page["entryOrder"])
        resolved_pages.append(resolved_page)

    return pages_out, resolved_pages


def validate_layout(layout_doc: dict[str, Any]) -> dict[str, Any]:
    native = layout_to_native_form(layout_doc)
    return native


def detect_layout_document(document: dict[str, Any]) -> bool:
    meta = document.get("meta")
    return isinstance(meta, dict) and meta.get("format") == LAYOUT_FORMAT


def normalize_input_document(path: Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], str]:
    document = load_json(path)
    if not isinstance(document, dict):
        raise ConversionError(f"Input file '{path}' must contain a JSON object")

    if detect_layout_document(document):
        native = layout_to_native_form(document)
        _, resolved_pages = resolve_layout_pages(document)
        resolved_layout = {
            "meta": document["meta"],
            "form": document["form"],
            "pages": resolved_pages,
        }
        return document, native, resolved_layout, "layout"

    validate_native_form(document)
    layout = native_form_to_layout(document)
    _, resolved_pages = resolve_layout_pages(layout)
    resolved_layout = {
        "meta": layout["meta"],
        "form": layout["form"],
        "pages": resolved_pages,
    }
    return layout, document, resolved_layout, "4dform"


def load_design_rules() -> dict[str, Any]:
    rules = load_yaml(DESIGN_RULES_PATH)
    return rules if isinstance(rules, dict) else {}


def load_validation_rules(path: Path | None) -> dict[str, Any]:
    rules_path = path or VALIDATION_RULES_PATH
    document = load_yaml(rules_path)
    if not isinstance(document, dict):
        raise ConversionError(f"Validation rules file '{rules_path}' must contain an object")
    meta = document.get("meta", {})
    if meta.get("format") != "4d-validation":
        raise ConversionError(f"Validation rules file '{rules_path}' must use meta.format '4d-validation'")
    if meta.get("version") != 1:
        raise ConversionError(f"Validation rules file '{rules_path}' must use meta.version 1")
    rules = document.get("rules")
    if not isinstance(rules, list) or not rules:
        raise ConversionError(f"Validation rules file '{rules_path}' must define a non-empty rules list")
    return document


def selected_rule_names(args: argparse.Namespace, rules_doc: dict[str, Any]) -> list[str]:
    available = [rule["name"] for rule in rules_doc["rules"]]
    if args.all_rules:
        return available
    if args.rule:
        unknown = [name for name in args.rule if name not in available]
        if unknown:
            joined = ", ".join(sorted(unknown))
            raise ConversionError(f"Unknown validation rule(s): {joined}")
        return args.rule
    return []


def element_ignores_rule(element: dict[str, Any], rule_name: str) -> bool:
    ignore_rules = element.get("validation", {}).get("ignoreRules", [])
    return rule_name in ignore_rules


def frame_right(frame: dict[str, int]) -> int:
    return frame["left"] + frame["width"]


def frame_bottom(frame: dict[str, int]) -> int:
    return frame["top"] + frame["height"]


def rule_shared_page_required(resolved_layout: dict[str, Any], _: dict[str, Any]) -> list[str]:
    pages = resolved_layout["pages"]
    if len(pages) < 2:
        return ["Form must contain at least 2 pages: shared page 0 and visible page 1"]
    first_page = pages[0]
    if first_page is None:
        return ["Page 0 must exist and be the shared page"]
    if first_page.get("role") != "shared":
        return ["Page 0 must have role 'shared'"]
    if pages[1] is None:
        return ["Page 1 must exist for visible content"]
    return []


def rule_inside_bounds(resolved_layout: dict[str, Any], _: dict[str, Any]) -> list[str]:
    width = resolved_layout["form"].get("width")
    height = resolved_layout["form"].get("height")
    if not isinstance(width, int) or not isinstance(height, int):
        return ["inside_bounds requires form.width and form.height"]

    violations: list[str] = []
    for page_index, page in enumerate(resolved_layout["pages"]):
        if page is None:
            continue
        for element in page["elements"]:
            if element_ignores_rule(element, "inside_bounds"):
                continue
            frame = element["resolvedFrame"]
            if frame["left"] < 0 or frame["top"] < 0 or frame_right(frame) > width or frame_bottom(frame) > height:
                violations.append(
                    f"Page {page_index}, element '{element['id']}' frame is outside form bounds"
                )
    return violations


def rule_no_overlap(resolved_layout: dict[str, Any], _: dict[str, Any]) -> list[str]:
    violations: list[str] = []
    for page_index, page in enumerate(resolved_layout["pages"]):
        if page is None:
            continue
        elements = page["elements"]
        for first, second in combinations(elements, 2):
            if element_ignores_rule(first, "no_overlap") or element_ignores_rule(second, "no_overlap"):
                continue
            first_frame = first["resolvedFrame"]
            second_frame = second["resolvedFrame"]
            if first_frame["width"] <= 0 or first_frame["height"] <= 0:
                continue
            if second_frame["width"] <= 0 or second_frame["height"] <= 0:
                continue
            intersects = (
                first_frame["left"] < frame_right(second_frame)
                and frame_right(first_frame) > second_frame["left"]
                and first_frame["top"] < frame_bottom(second_frame)
                and frame_bottom(first_frame) > second_frame["top"]
            )
            if intersects:
                violations.append(
                    f"Page {page_index}, elements '{first['id']}' and '{second['id']}' overlap"
                )
    return violations


def allowed_spacing_values(rules_doc: dict[str, Any]) -> list[int]:
    defaults = rules_doc.get("defaults", {})
    spacing = defaults.get("spacing", {})
    values = spacing.get("allowedValues")
    if isinstance(values, list) and all(isinstance(value, int) for value in values):
        return values

    design_rules = load_design_rules()
    collected: set[int] = set()
    spacing_values = design_rules.get("spacingSystem", {}).get("allowedValues", [])
    collected.update(value for value in spacing_values if isinstance(value, int))
    collected.update(value for value in design_rules.get("forms", {}).get("verticalSpacing", []) if isinstance(value, int))
    collected.update(value for value in design_rules.get("forms", {}).get("labelToInputSpacing", []) if isinstance(value, int))
    collected.update(value for value in design_rules.get("buttons", {}).get("spacing", {}).get("horizontal", []) if isinstance(value, int))
    collected.update(value for value in design_rules.get("buttons", {}).get("spacing", {}).get("vertical", []) if isinstance(value, int))
    return sorted(collected)


def rule_consistent_spacing(resolved_layout: dict[str, Any], rules_doc: dict[str, Any]) -> list[str]:
    allowed = set(allowed_spacing_values(rules_doc))
    if not allowed:
        return ["consistent_spacing requires at least one allowed spacing value"]

    violations: list[str] = []
    for page_index, page in enumerate(resolved_layout["pages"]):
        if page is None:
            continue
        by_left: dict[int, list[dict[str, Any]]] = {}
        by_top: dict[int, list[dict[str, Any]]] = {}
        for element in page["elements"]:
            frame = element["resolvedFrame"]
            by_left.setdefault(frame["left"], []).append(element)
            by_top.setdefault(frame["top"], []).append(element)

        for group in by_left.values():
            ordered = sorted(group, key=lambda item: item["resolvedFrame"]["top"])
            for first, second in zip(ordered, ordered[1:]):
                if element_ignores_rule(first, "consistent_spacing") or element_ignores_rule(second, "consistent_spacing"):
                    continue
                gap = second["resolvedFrame"]["top"] - frame_bottom(first["resolvedFrame"])
                if gap > 0 and gap not in allowed:
                    violations.append(
                        f"Page {page_index}, spacing {gap} between '{first['id']}' and '{second['id']}' "
                        f"is not in allowed values {sorted(allowed)}"
                    )

        for group in by_top.values():
            ordered = sorted(group, key=lambda item: item["resolvedFrame"]["left"])
            for first, second in zip(ordered, ordered[1:]):
                if element_ignores_rule(first, "consistent_spacing") or element_ignores_rule(second, "consistent_spacing"):
                    continue
                gap = second["resolvedFrame"]["left"] - frame_right(first["resolvedFrame"])
                if gap > 0 and gap not in allowed:
                    violations.append(
                        f"Page {page_index}, spacing {gap} between '{first['id']}' and '{second['id']}' "
                        f"is not in allowed values {sorted(allowed)}"
                    )
    return violations


def rule_alignment_consistency(resolved_layout: dict[str, Any], _: dict[str, Any]) -> list[str]:
    violations: list[str] = []
    for page_index, page in enumerate(resolved_layout["pages"]):
        if page is None:
            continue
        element_map = {element["id"]: element for element in page["elements"]}
        for element in page["elements"]:
            if element_ignores_rule(element, "alignment_consistency"):
                continue
            placement = element["layout"].get("placement")
            if not placement:
                continue
            kind, target = parse_placement(
                placement,
                page_index=page_index,
                element_id=element["id"],
            )
            if kind not in {"below", "above"} or target == "parent":
                continue
            reference = element_map.get(target)
            if reference is None:
                continue
            if element_ignores_rule(reference, "alignment_consistency"):
                continue
            if element["resolvedFrame"]["left"] != reference["resolvedFrame"]["left"]:
                violations.append(
                    f"Page {page_index}, element '{element['id']}' is vertically grouped with "
                    f"'{target}' but their left edges do not align"
                )
    return violations


GRAPHICAL_RULE_DISPATCH = {
    "shared_page_required": rule_shared_page_required,
    "no_overlap": rule_no_overlap,
    "consistent_spacing": rule_consistent_spacing,
    "alignment_consistency": rule_alignment_consistency,
    "inside_bounds": rule_inside_bounds,
}


def run_graphical_validation(
    resolved_layout: dict[str, Any],
    rules_doc: dict[str, Any],
    selected_rules: list[str],
) -> list[str]:
    violations: list[str] = []
    for rule_name in selected_rules:
        checker = GRAPHICAL_RULE_DISPATCH.get(rule_name)
        if checker is None:
            raise ConversionError(f"Rule '{rule_name}' is not implemented")
        for violation in checker(resolved_layout, rules_doc):
            violations.append(f"[{rule_name}] {violation}")
    return violations


def cmd_form_to_layout(args: argparse.Namespace) -> None:
    native = load_json(Path(args.input))
    layout = native_form_to_layout(native)
    dump_json(Path(args.output), layout)


def cmd_layout_to_form(args: argparse.Namespace) -> None:
    layout = load_json(Path(args.input))
    native = layout_to_native_form(layout)
    dump_json(Path(args.output), native)


def cmd_validate(args: argparse.Namespace) -> None:
    layout, native, resolved_layout, input_kind = normalize_input_document(Path(args.input))

    rules_doc = load_validation_rules(Path(args.rules_file) if args.rules_file else None)
    selected_rules = selected_rule_names(args, rules_doc)
    if selected_rules:
        violations = run_graphical_validation(resolved_layout, rules_doc, selected_rules)
        if violations:
            joined = "\n".join(violations)
            raise ConversionError(f"Graphical validation failed for {input_kind} input:\n{joined}")
        if args.native_output:
            dump_json(Path(args.native_output), native)
        print(f"Validation passed for {input_kind} input with rules: {', '.join(selected_rules)}")
        return

    if args.native_output:
        dump_json(Path(args.native_output), native)
    print(f"Validation passed for {input_kind} input.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Convert between .4DForm and a relational 4D layout JSON."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    form_to_layout = subparsers.add_parser("form-to-layout")
    form_to_layout.add_argument("input", help="Input .4DForm JSON file")
    form_to_layout.add_argument("output", help="Output layout JSON file")
    form_to_layout.set_defaults(func=cmd_form_to_layout)

    layout_to_form = subparsers.add_parser("layout-to-form")
    layout_to_form.add_argument("input", help="Input layout JSON file")
    layout_to_form.add_argument("output", help="Output .4DForm JSON file")
    layout_to_form.set_defaults(func=cmd_layout_to_form)

    validate = subparsers.add_parser("validate")
    validate.add_argument("input", help="Input layout JSON or .4DForm file")
    validate.add_argument(
        "--native-output",
        help="Optional path to write the generated native form after validation",
    )
    validate.add_argument(
        "--rule",
        action="append",
        help="Run one graphical validation rule by name. Repeat to run multiple rules.",
    )
    validate.add_argument(
        "--all-rules",
        action="store_true",
        help="Run all bundled graphical validation rules.",
    )
    validate.add_argument(
        "--rules-file",
        help="Optional path to a 4d-validation YAML file. Defaults to the bundled validation rules.",
    )
    validate.set_defaults(func=cmd_validate)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        args.func(args)
    except ConversionError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except jsonschema.SchemaError as exc:
        print(f"Schema error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
