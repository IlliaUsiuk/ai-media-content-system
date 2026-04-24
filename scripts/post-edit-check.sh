#!/usr/bin/env bash
# PostToolUse hook — called after every Edit or Write tool use.
# Reads Claude Code tool input as JSON from stdin.
# Exit 2 to signal a problem. Exit 0 to continue.
# Kept minimal for early development — only checks Python syntax on .py files.

input=$(cat)

# Extract file path from JSON input (simple grep, no jq dependency)
file_path=$(echo "$input" | grep -oP '"file_path"\s*:\s*"\K[^"]+')

# If no file path found, allow
if [ -z "$file_path" ]; then
  exit 0
fi

# Check Python syntax for .py files if python is available
if [[ "$file_path" == *.py ]] && command -v python &>/dev/null; then
  if ! python -m py_compile "$file_path" 2>/dev/null; then
    echo "Warning: $file_path has a Python syntax error. Please review." >&2
    # Exit 0 — warn but do not block during early development
  fi
fi

# Allow everything else
exit 0
