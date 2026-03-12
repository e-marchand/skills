---
name: 4d-find-command
description: Find 4D commands by keyword. Use this skill when the user wants to search for, find, or discover 4D commands matching a term. Searches the gram.4dsyntax file from tool4d.app to list matching command names and uses bundled syntax metadata for readable signatures and summaries. Filters out deprecated commands.
license: Apache 2.0
---

# 4D Command Finder

Search for 4D commands by keyword.

## Prerequisites

Requires tool4d to access the `gram.4dsyntax` file:
- Install [4D-Analyzer extension](https://marketplace.visualstudio.com/items?itemName=4D.4d-analyzer) in VS Code/Antigravity, OR
- Set `TOOL4D` environment variable to point to tool4d executable

## Usage

```bash
python3 scripts/find_command.py <search_term> [--verbose]
```

## Options

- `--verbose` or `-v`: Add category, summary, and parameter details for each command
- `--summary`: Add summary lines without verbose categories

## Examples

```bash
# Simple search
python3 scripts/find_command.py json

# Verbose output with category + parameter details
python3 scripts/find_command.py json --verbose

# Signature + summary only
python3 scripts/find_command.py json --summary
```

## Output

Simple mode (typed signature, using bundled 4D syntax metadata when available):
```
JSON Parse ( jsonString : Text {; type : Integer}{; *} ) : any
JSON Stringify ( value : Object, any {; *} ) : Text
JSON Validate ( vJson : Object ; vSchema : Object ) : Object
```

Summary mode:
```
JSON Parse ( jsonString : Text {; type : Integer}{; *} ) : any
  The JSON Parse command parses the contents of a JSON-formatted string and extracts values that you can store in a 4D field or variable.
```

Verbose mode (adds category, summary, and parameter details):
```
JSON Parse ( jsonString : Text {; type : Integer}{; *} ) : any [JSON]
  The JSON Parse command parses the contents of a JSON-formatted string and extracts values that you can store in a 4D field or variable.
  jsonString [Text, ->]: JSON string to parse
  type [Integer, ->]: Type in which to convert the values
  * [Operator, ->]: Adds line position and offset of each property if returned value is an object
  result [any, <-]: Values extracted from JSON string
```
