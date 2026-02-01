#!/usr/bin/env python3
"""
Validate a 4D form file (.4DForm) against the JSON schema.

Usage:
    validate_form.py <form_file>
    validate_form.py <form_file> --schema <schema_file>

Examples:
    validate_form.py Project/Sources/Forms/MyForm/form.4DForm
    validate_form.py form.4DForm --schema /path/to/formsSchema.json
"""

import sys
import json
from pathlib import Path

try:
    import jsonschema
    from jsonschema import validate, ValidationError
except ImportError:
    print("Error: jsonschema package required. Install with: pip install jsonschema or pip3 on macOS")
    sys.exit(1)


def find_schema():
    """Find the schema file in the skill's assets directory."""
    script_dir = Path(__file__).parent
    schema_path = script_dir.parent / "assets" / "formsSchema.json"
    if schema_path.exists():
        return schema_path
    return None


def validate_form(form_path, schema_path=None):
    """
    Validate a 4D form file against the JSON schema.

    Args:
        form_path: Path to the .4DForm file
        schema_path: Optional path to schema file (uses bundled schema if not provided)

    Returns:
        Tuple of (is_valid, errors)
    """
    form_path = Path(form_path)

    if not form_path.exists():
        return False, [f"Form file not found: {form_path}"]

    # Find schema
    if schema_path:
        schema_path = Path(schema_path)
    else:
        schema_path = find_schema()

    if not schema_path or not schema_path.exists():
        return False, ["Schema file not found"]

    # Load files
    try:
        with open(form_path, 'r', encoding='utf-8') as f:
            form_data = json.load(f)
    except json.JSONDecodeError as e:
        return False, [f"Invalid JSON in form file: {e}"]

    try:
        with open(schema_path, 'r', encoding='utf-8') as f:
            schema = json.load(f)
    except json.JSONDecodeError as e:
        return False, [f"Invalid JSON in schema file: {e}"]

    # Validate
    errors = []
    try:
        validate(instance=form_data, schema=schema)
        return True, []
    except ValidationError as e:
        # Collect all errors
        validator = jsonschema.Draft4Validator(schema)
        for error in validator.iter_errors(form_data):
            path = " -> ".join(str(p) for p in error.absolute_path) if error.absolute_path else "root"
            errors.append(f"{path}: {error.message}")
        return False, errors


def main():
    if len(sys.argv) < 2:
        print("Usage: validate_form.py <form_file> [--schema <schema_file>]")
        sys.exit(1)

    form_path = sys.argv[1]
    schema_path = None

    if "--schema" in sys.argv:
        idx = sys.argv.index("--schema")
        if idx + 1 < len(sys.argv):
            schema_path = sys.argv[idx + 1]

    is_valid, errors = validate_form(form_path, schema_path)

    if is_valid:
        print(f"✅ {form_path} is valid")
        sys.exit(0)
    else:
        print(f"❌ {form_path} has {len(errors)} error(s):")
        for error in errors:
            print(f"  - {error}")
        sys.exit(1)


if __name__ == "__main__":
    main()
