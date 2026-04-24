#!/usr/bin/env bash
# PreToolUse hook — called before every Bash tool use.
# Reads Claude Code tool input as JSON from stdin.
# Exit 2 to block. Exit 0 to allow.
# Kept minimal for early development — only blocks clearly destructive commands.

input=$(cat)

# Block unconditional recursive deletes at root or repo level
if echo "$input" | grep -qE 'rm\s+-rf\s+/[^/]'; then
  echo "Blocked: rm -rf on root paths is not allowed." >&2
  exit 2
fi

if echo "$input" | grep -qE 'rm\s+-rf\s+\*'; then
  echo "Blocked: rm -rf * is not allowed." >&2
  exit 2
fi

# Block reading secrets and credential files
if echo "$input" | grep -qE 'cat\s+.*\.(env|pem|key|secret)'; then
  echo "Blocked: reading credential files is not allowed." >&2
  exit 2
fi

# Allow everything else
exit 0
