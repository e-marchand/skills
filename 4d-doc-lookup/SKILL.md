---
name: 4d-doc-lookup
description: Look up 4D documentation for commands, classes, or language concepts. Use when the user asks about a 4D command's syntax, parameters, or usage, needs class API reference, or wants to understand a 4D language concept. Resolves names to developer.4d.com URLs and optionally fetches page content.
---

# 4D Doc Lookup

Look up documentation from developer.4d.com for commands, classes, and topics.

## Usage

```bash
# Get URL only (fast, no network needed)
python3 scripts/doc_lookup.py "JSON Parse"

# Fetch and extract page content
python3 scripts/doc_lookup.py "collection" --fetch

# Limit extracted text length
python3 scripts/doc_lookup.py "ORDA" --fetch --max-chars 2000
```

## Query Types

The script auto-detects the query type:

| Query | Resolves to | Example URL |
|-------|-------------|-------------|
| Command name | `/commands/<slug>` | `ALERT` → `/commands/alert` |
| Class name | `/API/<ClassName>` | `collection` → `/API/CollectionClass` |
| `4D.File`, `cs.DataStore` | `/API/<ClassName>` | `4D.File` → `/API/FileClass` |
| Topic keyword | `/Concepts/<path>` | `orda` → `/ORDA/overview` |

## Output

```json
{
  "query": "JSON Parse",
  "type": "command",
  "url": "https://developer.4d.com/docs/commands/json-parse"
}
```

With `--fetch`, adds `"content"` field with extracted text.

## Supported Topics

`orda`, `variables`, `methods`, `classes`, `parameters`, `shared`, `error handling`, `data types`, `collections`, `objects`, `forms`, `listbox`, `web server`, `rest`, `compiler`, `components`, `architecture`

## Combining with 4d-find-command

Use `4d-find-command` to discover command names, then `4d-doc-lookup` to get full documentation:

```bash
# Step 1: Find commands
scripts/find_command.sh json

# Step 2: Look up specific command
python3 scripts/doc_lookup.py "JSON Parse" --fetch
```
