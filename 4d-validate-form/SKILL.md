---
name: 4d-validate-form
description: Validate 4D form files (.4DForm) against the official JSON schema. Use this skill when the user wants to validate, check, or verify a 4D form file for errors. Detects invalid properties, missing required fields, and type mismatches.
license: Apache 2.0
---

# 4D Form Validator

Validate `.4DForm` files against the 4D forms JSON schema.

## Usage

```bash
python scripts/validate_form.py <path/to/form.4DForm>
```

Requires `jsonschema` package: `pip install jsonschema`

## Resources

- `scripts/validate_form.py` - Validation script
- `assets/formsSchema.json` - Official 4D forms JSON schema
