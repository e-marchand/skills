#!/bin/bash
#
# Find 4D commands matching a search term
#
# Usage:
#   find_command.sh <search_term> [--verbose]
#
# Examples:
#   find_command.sh json
#   find_command.sh json --verbose
#   find_command.sh "file"
#   find_command.sh selection
#

set -e

VERBOSE=0
SEARCH_TERM=""

# Parse arguments
for arg in "$@"; do
    case $arg in
        --verbose|-v)
            VERBOSE=1
            ;;
        *)
            if [ -z "$SEARCH_TERM" ]; then
                SEARCH_TERM="$arg"
            fi
            ;;
    esac
done

if [ -z "$SEARCH_TERM" ]; then
    echo "Usage: find_command.sh <search_term> [--verbose]"
    echo "Example: find_command.sh json"
    echo "         find_command.sh json --verbose"
    exit 1
fi

# Find tool4d.app in standard locations
find_tool4d_app() {
    local search_paths=(
        "$HOME/Library/Application Support/Code/User/globalStorage/4d.4d-analyzer/tool4d"
        "$HOME/Library/Application Support/Antigravity/User/globalStorage/4d.4d-analyzer/tool4d"
    )

    for base_path in "${search_paths[@]}"; do
        if [ -d "$base_path" ]; then
            local tool4d_path=$(find "$base_path" -name "tool4d.app" -type d 2>/dev/null | sort -V | tail -1)
            if [ -n "$tool4d_path" ]; then
                echo "$tool4d_path"
                return 0
            fi
        fi
    done
    return 1
}

# Type code to name mapping
get_type_name() {
    case "$1" in
        R) echo "Real" ;;
        L) echo "Integer" ;;
        S) echo "String" ;;
        B) echo "Boolean" ;;
        D) echo "Date" ;;
        T) echo "Time" ;;
        H) echo "Time" ;;
        o) echo "Object" ;;
        j) echo "Collection" ;;
        E) echo "Expression" ;;
        a|a80|a3|A) echo "Text" ;;
        P) echo "Picture" ;;
        V) echo "Variant" ;;
        v) echo "Pointer" ;;
        C) echo "Field" ;;
        F) echo "Table" ;;
        Y) echo "Variable" ;;
        y) echo "NumericField" ;;
        X) echo "" ;;  # No parameter
        *) echo "$1" ;;
    esac
}

# Category number to name mapping
get_category_name() {
    case "$1" in
        1) echo "Application" ;;
        2) echo "Arrays" ;;
        3) echo "Blobs" ;;
        4) echo "Boolean" ;;
        6) echo "Communications" ;;
        7) echo "Compiler" ;;
        8) echo "Data Entry" ;;
        9) echo "Date and Time" ;;
        11) echo "Entry Control" ;;
        12) echo "Interruptions" ;;
        13) echo "Listbox" ;;
        15) echo "Hierarchical Lists" ;;
        16) echo "Import Export" ;;
        17) echo "Errors" ;;
        18) echo "Language" ;;
        19) echo "Math" ;;
        20) echo "Menus" ;;
        21) echo "Messages" ;;
        23) echo "Objects (Forms)" ;;
        24) echo "Statistics" ;;
        25) echo "Users and Groups" ;;
        26) echo "Pictures" ;;
        27) echo "Printing" ;;
        30) echo "Process" ;;
        31) echo "Record Locking" ;;
        32) echo "Records" ;;
        33) echo "Relations" ;;
        34) echo "Resources" ;;
        35) echo "Queries" ;;
        37) echo "Selection" ;;
        38) echo "Sets" ;;
        39) echo "String" ;;
        40) echo "Structure" ;;
        42) echo "System Documents" ;;
        43) echo "System Environment" ;;
        45) echo "SQL" ;;
        48) echo "User Interface" ;;
        49) echo "Variables" ;;
        50) echo "Web Server" ;;
        51) echo "Windows" ;;
        54) echo "Quick Reports" ;;
        56) echo "Formulas" ;;
        59) echo "System" ;;
        60) echo "Backup" ;;
        61) echo "Forms" ;;
        62) echo "Web Area" ;;
        63) echo "XML DOM" ;;
        64) echo "XML SAX" ;;
        68) echo "Design Object Access" ;;
        71) echo "JSON" ;;
        72) echo "Objects" ;;
        73) echo "Styled Text" ;;
        74) echo "Write Pro" ;;
        76) echo "Cache" ;;
        77) echo "Collections" ;;
        80) echo "License" ;;
        81) echo "FileHandle" ;;
        *) echo "Category $1" ;;
    esac
}

# Parse parameters string to human readable format
# Input: "L ; L" or "a ; L'" or "X"
# Output: "(Integer, Integer)" or "(Text, Integer?)" or "()"
parse_params() {
    local params="$1"

    # Remove everything after // (comments)
    params=$(echo "$params" | sed 's|//.*||')

    # Skip if empty or just X (no params)
    if [ -z "$params" ] || [ "$params" = "X" ]; then
        echo "()"
        return
    fi

    # Parse each parameter separated by ;
    local result=""
    local IFS=';'
    for param in $params; do
        # Trim whitespace
        param=$(echo "$param" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')

        # Skip empty, X, *, |, {, }, (, )
        if [ -z "$param" ] || [[ "$param" =~ ^[X\*\|\{\}\(\)]$ ]]; then
            continue
        fi

        # Check if optional (ends with ')
        local optional=""
        if [[ "$param" == *"'" ]]; then
            optional="?"
            param="${param%\'}"
        fi

        # Get the base type (first letter/word)
        local base_type=$(echo "$param" | grep -oE '^[A-Za-z0-9]+' | head -1)

        if [ -n "$base_type" ]; then
            local type_name=$(get_type_name "$base_type")
            if [ -n "$type_name" ]; then
                if [ -n "$result" ]; then
                    result="$result, $type_name$optional"
                else
                    result="$type_name$optional"
                fi
            fi
        fi
    done

    if [ -n "$result" ]; then
        echo "($result)"
    else
        echo "()"
    fi
}

# Find tool4d.app
TOOL4D_APP=$(find_tool4d_app)

if [ -z "$TOOL4D_APP" ]; then
    echo "Error: tool4d.app not found"
    echo "Install 4D-Analyzer extension in VS Code or Antigravity"
    exit 1
fi

SYNTAX_FILE="$TOOL4D_APP/Contents/Resources/gram.4dsyntax"

if [ ! -f "$SYNTAX_FILE" ]; then
    echo "Error: gram.4dsyntax not found at $SYNTAX_FILE"
    exit 1
fi

# Search for commands (case insensitive)
# Filter out:
#   - Lines starting with @ (markers)
#   - Lines starting with _O_ (deprecated commands)
#   - Lines starting with _4D (internal)
#   - Lines not starting with a letter

if [ "$VERBOSE" -eq 1 ]; then
    # Verbose output with type info and parameters
    grep -i "$SEARCH_TERM" "$SYNTAX_FILE" | \
        sed 's/^[[:space:]]*//' | \
        grep -v "^@" | \
        grep -v "^_O_" | \
        grep -v "_O_" | \
        grep -v "^_4D" | \
        grep -v "^[^A-Za-z]" | \
        while IFS= read -r line; do
            # Parse line format: [ReturnType <==] CommandName[,alias] : Category : Args
            if [[ "$line" =~ ^([A-Za-z0-9]+)[[:space:]]+\<==(.+) ]]; then
                return_type="${BASH_REMATCH[1]}"
                rest="${BASH_REMATCH[2]}"
            else
                return_type=""
                rest="$line"
            fi

            # Extract command name (before comma or colon)
            cmd_name=$(echo "$rest" | sed 's/,.*//' | cut -d':' -f1 | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')

            # Extract category number (second field)
            category=$(echo "$rest" | cut -d':' -f2 | sed 's/[[:space:]]//g')

            # Extract parameters (third field onwards)
            params=$(echo "$rest" | cut -d':' -f3-)
            params_str=$(parse_params "$params")

            if [ -n "$cmd_name" ] && [ "$cmd_name" != "" ]; then
                cat_name=$(get_category_name "$category")
                if [ -n "$return_type" ]; then
                    type_name=$(get_type_name "$return_type")
                    echo "$cmd_name$params_str -> $type_name [$cat_name]"
                else
                    echo "$cmd_name$params_str [$cat_name]"
                fi
            fi
        done | sort -u
else
    # Simple output: signature without category
    grep -i "$SEARCH_TERM" "$SYNTAX_FILE" | \
        sed 's/^[[:space:]]*//' | \
        grep -v "^@" | \
        grep -v "^_O_" | \
        grep -v "_O_" | \
        grep -v "^_4D" | \
        grep -v "^[^A-Za-z]" | \
        while IFS= read -r line; do
            # Parse line format: [ReturnType <==] CommandName[,alias] : Category : Args
            if [[ "$line" =~ ^([A-Za-z0-9]+)[[:space:]]+\<==(.+) ]]; then
                return_type="${BASH_REMATCH[1]}"
                rest="${BASH_REMATCH[2]}"
            else
                return_type=""
                rest="$line"
            fi

            # Extract command name (before comma or colon)
            cmd_name=$(echo "$rest" | sed 's/,.*//' | cut -d':' -f1 | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')

            # Extract parameters (third field onwards)
            params=$(echo "$rest" | cut -d':' -f3-)
            params_str=$(parse_params "$params")

            if [ -n "$cmd_name" ] && [ "$cmd_name" != "" ]; then
                if [ -n "$return_type" ]; then
                    type_name=$(get_type_name "$return_type")
                    echo "$cmd_name$params_str -> $type_name"
                else
                    echo "$cmd_name$params_str"
                fi
            fi
        done | sort -u
fi
