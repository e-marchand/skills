---
name: 4d-catalog
description: Manage 4D base catalog files (.4DCatalog). Use this skill when the user wants to create, inspect, or modify a 4D database catalog — adding/removing tables and fields, viewing structure, or initializing a new catalog from scratch.
license: Apache 2.0
---

# 4D Catalog Manager

Manage `.4DCatalog` XML files that define the structure of a 4D database (tables, fields, relations, indexes).

## Script

```bash
python scripts/catalog.py <command> [args]
```

## Commands

### Create a new catalog

```bash
python scripts/catalog.py create <catalog_path> <base_name>
```

- `catalog_path`: path to `.4DCatalog` file, or a directory (creates `Project/Sources/catalog.4DCatalog` inside)
- `base_name`: name of the 4D base (embedded in the XML)
- UUID is automatically generated

### Inspect a catalog

```bash
python scripts/catalog.py info <catalog_path>
python scripts/catalog.py list-tables <catalog_path>
```

`info` prints a summary (table count, relation count, index count).
`list-tables` lists each table with its fields, types, and flags.

### Add a table

```bash
python scripts/catalog.py add-table <catalog_path> <table_name> [--no-id]
```

By default, creates an `ID` Long Integer field with `autosequence`, `unique`, `not_null`, sets it as primary key, and adds a unique index. Pass `--no-id` to create an empty table.

### Remove a table

```bash
python scripts/catalog.py remove-table <catalog_path> <table_name>
```

Also removes all relations and indexes referencing that table's fields.

### Add a field

```bash
python scripts/catalog.py add-field <catalog_path> <table_name> <field_name> <type> [options]
```

**Field types:**

| Type keyword        | 4D type          | Type ID |
|---------------------|------------------|---------|
| `bool` / `boolean`  | Boolean          | 1       |
| `int` / `integer`   | Integer          | 3       |
| `long` / `longint`  | Long Integer     | 4       |
| `int64`             | Integer 64       | 5       |
| `real` / `float`    | Real             | 6       |
| `date`              | Date             | 8       |
| `time`              | Time             | 9       |
| `alpha`             | Alpha (255 chars)| 10      |
| `text`              | Long Text        | 10      |
| `picture`           | Picture          | 12      |
| `blob`              | BLOB             | 18      |
| `object`            | Object           | 21      |
| `vector`            | Vector (4D.Vector class) | 21 |

**Options:**

| Flag            | Effect                                  |
|-----------------|-----------------------------------------|
| `--unique`      | Adds `unique="true"`                    |
| `--not-null`    | Adds `not_null="true"`                  |
| `--autosequence`| Adds `autosequence="true"`              |
| `--length N`    | Sets `limiting_length` for alpha fields |
| `--primary-key` | Sets field as table primary key         |

### Remove a field

```bash
python scripts/catalog.py remove-field <catalog_path> <table_name> <field_name>
```

Also removes any primary key declaration and indexes referencing this field.

## Catalog path resolution

All commands accept the catalog path in multiple forms:
- `/path/to/catalog.4DCatalog` — direct path
- `/path/to/project/` — directory, resolves to `Project/Sources/catalog.4DCatalog` inside
- `.` — current directory

## Resources

- `scripts/catalog.py` — main management script (no external dependencies)
- `resources/empty_catalog.xml` — template showing the minimal XML structure
- `assets/dtd/base.dtd` — 4D base DTD (references base_core and common)
- `assets/dtd/base_core.dtd` — table, field, index, relation definitions
- `assets/dtd/common.dtd` — shared elements (field_ref, table_ref, etc.)
