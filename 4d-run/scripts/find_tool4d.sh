#!/bin/bash
# Find tool4d in standard locations, return path to latest version

# Check if TOOL4D environment variable is set
if [ -n "$TOOL4D" ]; then
    if [ -x "$TOOL4D" ]; then
        echo "$TOOL4D"
        exit 0
    else
        echo "Error: TOOL4D environment variable is set but not executable: $TOOL4D" >&2
        exit 1
    fi
fi

search_paths=(
    "$HOME/Library/Application Support/Code/User/globalStorage/4d.4d-analyzer/tool4d"
    "$HOME/Library/Application Support/Antigravity/User/globalStorage/4d.4d-analyzer/tool4d"
)

for base_path in "${search_paths[@]}"; do
    if [ -d "$base_path" ]; then
        # Find latest tool4d.app by sorting version folders
        tool4d_path=$(find "$base_path" -name "tool4d.app" -type d 2>/dev/null | sort -V | tail -1)
        if [ -n "$tool4d_path" ]; then
            echo "$tool4d_path/Contents/MacOS/tool4d"
            exit 0
        fi
    fi
done

echo "tool4d not found" >&2
exit 1
