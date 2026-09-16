#!/bin/sh
# Humanize installer: clone (or update) the repo into ~/.humanize/app and bring up the dashboard.
#   curl -fsSL https://raw.githubusercontent.com/0xArx/Humanize/main/install.sh | sh
#   curl -fsSL https://raw.githubusercontent.com/0xArx/Humanize/main/install.sh | sh -s -- --name "Ari Vale"
set -e
D="${HUMANIZE_DIR:-$HOME/.humanize/app}"
command -v git >/dev/null 2>&1 || { echo "git is required"; exit 1; }
command -v python3 >/dev/null 2>&1 || { echo "python3 is required"; exit 1; }
if [ -d "$D/.git" ]; then
  git -C "$D" pull -q --ff-only || true
else
  mkdir -p "$(dirname "$D")"
  git clone -q https://github.com/0xArx/Humanize.git "$D"
fi
if [ -d "$HOME/.claude" ] && [ ! -e "$HOME/.claude/skills/humanize" ]; then
  mkdir -p "$HOME/.claude/skills" && ln -s "$D" "$HOME/.claude/skills/humanize" 2>/dev/null || true
fi
exec python3 "$D/humanize.py" init "$@"
