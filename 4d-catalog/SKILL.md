---
name: 4d-catalog
description: Create and edit 4D database catalog files (.4DCatalog) — tables, fields, primary keys, indexes.
license: Apache 2.0
---

# 4D Catalog Manager

`<project>` is the 4D project root. The script resolves to `<project>/Project/Sources/catalog.4DCatalog`. A path ending in `.4DCatalog` overrides.

## Commands

```bash
python scripts/catalog.py create     <project> <base_name>
python scripts/catalog.py info       <project>
python scripts/catalog.py add-table  <project> <table> [field_spec ...] [--no-id]
python scripts/catalog.py remove-table <project> <table>
python scripts/catalog.py add-field  <project> <table> <field_spec> [field_spec ...]
python scripts/catalog.py remove-field <project> <table> <field>
```

`add-table` adds an auto-incrementing `ID` Long Integer as primary key by default; pass `--no-id` to skip.

## Field spec

```
name:type[:flag,flag,...]
```

**Types:** `bool`, `int`, `long`, `int64`, `real`, `date`, `time`, `alpha`, `text`, `picture`, `blob`, `object`, `vector`

**Flags:** `unique`, `not-null`, `autosequence`, `pk`, `length=N` (alpha only)

## Examples

```bash
python scripts/catalog.py create . "My Base"
python scripts/catalog.py add-table . People Name:alpha:length=128 Age:int Vec:vector
python scripts/catalog.py add-field . People Email:alpha:unique,not-null,length=255
python scripts/catalog.py info .
```

## Validation

Catalogs can be validated against the bundled DTD:

```bash
xmllint --nonet --dtdvalid assets/dtd/base.dtd --noout <project>/Project/Sources/catalog.4DCatalog
```

## Resources

- `scripts/catalog.py` — management script (stdlib only)
- `resources/empty_catalog.xml` — template with `{{basename}}` / `{{uuid}}` placeholders
- `assets/dtd/{base,base_core,common}.dtd` — 4D DTDs, local refs for offline validation
