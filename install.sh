#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CLAUDE_DIR="$HOME/.claude"
HOOKS_DIR="$CLAUDE_DIR/hooks"
SETTINGS="$CLAUDE_DIR/settings.json"

echo "=== Claude Code Statusline & Cost Tracker Installer ==="
echo ""

# --- Dependencies ---
missing=()
for cmd in jq bc git; do
  if ! command -v "$cmd" &>/dev/null; then
    missing+=("$cmd")
  fi
done

if [ ${#missing[@]} -gt 0 ]; then
  echo "Installing missing dependencies: ${missing[*]}"
  if command -v brew &>/dev/null; then
    brew install "${missing[@]}"
  elif command -v apt-get &>/dev/null; then
    if [ "$(id -u)" -eq 0 ]; then
      apt-get update && apt-get install -y "${missing[@]}"
    elif command -v sudo &>/dev/null; then
      sudo apt-get update && sudo apt-get install -y "${missing[@]}"
    else
      echo "ERROR: Not running as root and sudo is not available. Please install manually: ${missing[*]}"
      exit 1
    fi
  else
    echo "ERROR: Could not find brew or apt-get. Please install manually: ${missing[*]}"
    exit 1
  fi
fi

# --- Create directories ---
mkdir -p "$HOOKS_DIR"

# --- Copy files ---
cp "$SCRIPT_DIR/statusline.sh" "$CLAUDE_DIR/statusline.sh"
chmod +x "$CLAUDE_DIR/statusline.sh"
echo "Installed statusline.sh -> $CLAUDE_DIR/statusline.sh"

cp "$SCRIPT_DIR/hooks/session_cost_tracker.py" "$HOOKS_DIR/session_cost_tracker.py"
chmod +x "$HOOKS_DIR/session_cost_tracker.py"
echo "Installed session_cost_tracker.py -> $HOOKS_DIR/session_cost_tracker.py"

# --- Update settings.json ---
if [ ! -f "$SETTINGS" ]; then
  echo '{}' > "$SETTINGS"
fi

# Add statusLine config
updated=$(jq '
  .statusLine = {
    "type": "command",
    "command": "~/.claude/statusline.sh"
  }
  | .hooks.SessionEnd = [
    {
      "hooks": [
        {
          "type": "command",
          "command": "python3 ~/.claude/hooks/session_cost_tracker.py"
        }
      ]
    }
  ]
' "$SETTINGS")

echo "$updated" > "$SETTINGS"
echo "Updated settings.json with statusLine and SessionEnd hook"

echo ""
echo "Done! Restart Claude Code for changes to take effect."
