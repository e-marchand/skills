---
name: 4d-check-syntax
description: Check syntax and compile a 4D project to find errors and type issues. Use this skill when the user wants to compile, check syntax, or validate a 4D project. Creates a _compile method if not present, then runs it using tool4d. Returns compilation errors in JSON format for easy parsing.
license: Apache 2.0
---

# 4D Syntax Checker

Compile a 4D project to check for syntax errors and type mismatches.

## Prerequisites

Uses the **4d-run** skill to execute the compilation method. Ensure tool4d is available.

## The _compile Method

Compilation requires a `_compile` method in the project. If not present, create it:

### Create _compile.4dm

Location: `Project/Sources/Methods/_compile.4dm`

```4d
//%attributes = {}

var $options:=New object
$options.targets:=[]
$options.generateSymbols:=False
$options.generateSyntaxFile:=True
$options.generateTypingMethods:=False

var $components:=Folder(fk database folder).folders().filter(Formula($1.value.extension=".4dbase"))
var $lock:=Folder(fk database folder).folder("userPreferences."+Current system user).file("dependencies-lock.json")
If ($lock.exists)
	var $lockData:=JSON Parse($lock.getText())
	$lockData.dependencies:=$lockData.dependencies || {}
	var $key : Text
	For each ($key; $lockData.dependencies)
		If (Length(String($lockData.dependencies[$key].path))>0)

			var $folder:=Try(Folder(String($lockData.dependencies[$key].path); fk platform path))
			If ($folder=Null)
				$folder:=Try(Folder(String($lockData.dependencies[$key].path); fk posix path))
			End if
			If ($folder#Null)
				$components.push($folder)
			End if

		End if
	End for each
End if

// Find component project files, prefer .4DProject over .4DZ to avoid duplicates
// .4DProject is in Component.4dbase/Project/Component.4DProject
// .4DZ is in Component.4dbase/Component.4DZ
var $projectFiles : Collection:=$components.flatMap(Formula($1.value.files(fk recursive).filter(Formula($1.value.extension=".4DProject"))))
var $zFiles : Collection:=$components.flatMap(Formula($1.value.files(fk recursive).filter(Formula($1.value.extension=".4DZ"))))
// Get component names that have .4DProject files
var $projectNames : Collection:=$projectFiles.map(Formula($1.value.parent.parent.name))
// Keep only .4DZ files for components without .4DProject
$zFiles:=$zFiles.filter(Formula(Not($projectNames.includes($1.value.parent.name))))
$components:=$projectFiles.combine($zFiles)
$options.components:=$components

var $result : Object:=Compile project($options)

ALERT(JSON Stringify($result))
```

### Method Features

- **Dependency support**: Reads `dependencies-lock.json` to include component paths
- **Component detection**: Finds `.4dbase` folders and external dependencies
- **Duplicate prevention**: Prefers `.4DProject` over `.4DZ` when both exist
- **Cross-platform paths**: Tries both platform and POSIX path formats

## Compilation Output

### Success

```json
{"success":true,"errors":[]}
```

### Errors

```json
{
  "success": false,
  "errors": [
    {
      "message": "Syntax error",
      "isError": true,
      "code": {
        "type": "classFunction",
        "className": "MyClass",
        "functionName": "myMethod",
        "path": "[class]/MyClass/myMethod",
        "file": "[object File]"
      },
      "line": 10,
      "lineInFile": 42
    }
  ]
}
```

### Error Properties

- `message`: Error description
- `isError`: true for errors, false for warnings
- `code.type`: "projectMethod", "classFunction", etc.
- `code.className`: Class name (for class methods)
- `code.functionName`: Function name
- `line`: Line within the function
- `lineInFile`: Absolute line in the file

## Workflow

1. **Check for _compile method**: Look in `Project/Sources/Methods/_compile.4dm`
2. **Create if missing**: Write the _compile method using the template above
3. **Find tool4d**: Use 4d-run skill to locate tool4d
4. **Run compilation**: Execute `_compile` method with `--dataless`
5. **Parse results**: Extract JSON from ALERT output

## Running Compilation

```bash
"<tool4d_path>" --project="<project_path>" --startup-method=_compile --dataless 2>&1
```

Output format:
```
tool4d.HDLS ([Call of Forbidden Method] ALERT: {"success":true,"errors":[]})[...]
```

Extract the JSON between `ALERT: ` and `)[`.

## Common Compilation Errors

| Error | Cause | Fix |
|-------|-------|-----|
| "Syntax error" | Invalid 4D syntax | Check line for typos |
| "Object syntax is not valid" | Invalid object property access | Use `[index]` for 4D.Blob properties |
| "Cannot make an assignment with those types" | Type mismatch | Check variable types |
| "Undeclared property 'X' used" | Missing property declaration | Add `property X : Type` to class |
| "The variable $X has not been explicitly declared" | Missing var declaration | Add `var $X : Type` |
| "signed integer overflow handling differs" | PCH cache issue | Not a code error, can ignore |

## Integration Example

```bash
# Find tool4d
TOOL4D=$(".claude/skills/4d-run/scripts/find_tool4d.sh")

# Run compilation
OUTPUT=$("$TOOL4D" --project="/path/to/Project/MyProject.4DProject" --startup-method=_compile --dataless 2>&1)

# Extract JSON result
RESULT=$(echo "$OUTPUT" | grep -o 'ALERT: {.*}' | sed 's/ALERT: //')
echo "$RESULT" | jq .
```
