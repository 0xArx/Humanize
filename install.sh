#!/bin/sh
# Humanize installer. The repository is private, so git needs to be able to read it:
#   GITHUB_TOKEN=<token that can read 0xArx/Humanize> sh install.sh [--name "Ari Vale"]
# or run it from inside a clone you already have. It clones (or updates) ~/.humanize/app, links it as a
# Claude Code skill when Claude Code is present, then runs `humanize.py init`, which creates the identity,
# draws the avatar and opens the dashboard.
#
# Variables: HUMANIZE_REPO, HUMANIZE_REF (branch or tag, default main), HUMANIZE_DIR (default ~/.humanize/app)
set -eu

REPO="${HUMANIZE_REPO:-https://github.com/0xArx/Humanize.git}"
REF="${HUMANIZE_REF:-main}"
DIR="${HUMANIZE_DIR:-$HOME/.humanize/app}"

need() { command -v "$1" >/dev/null 2>&1 || { echo "$1 is required but was not found" >&2; exit 1; }; }
need git
need python3

# Give git the token through the environment, so it never appears in the process list or in .git/config.
g() {
  if [ -n "${GITHUB_TOKEN:-}" ]; then
    b=$(printf 'x-access-token:%s' "$GITHUB_TOKEN" | base64 | tr -d '\n')
    GIT_TERMINAL_PROMPT=0 GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0="http.https://github.com/.extraheader" \
      GIT_CONFIG_VALUE_0="AUTHORIZATION: basic $b" git "$@"
  else
    git "$@"
  fi
}

here=$(cd "$(dirname "$0")" 2>/dev/null && pwd || echo "")
if [ -n "$here" ] && [ -f "$here/humanize.py" ] && [ -f "$here/SKILL.md" ]; then
  DIR="$here"                                   # already inside a clone: use it as it is
elif [ -d "$DIR/.git" ]; then
  g -C "$DIR" fetch -q origin "$REF"
  g -C "$DIR" checkout -q "$REF"
  g -C "$DIR" merge -q --ff-only "origin/$REF" 2>/dev/null || true
else
  mkdir -p "$(dirname "$DIR")"
  g clone -q -b "$REF" "$REPO" "$DIR" || { echo "could not clone $REPO. It is private: set GITHUB_TOKEN or sign in to git first." >&2; exit 1; }
fi

if [ -d "$HOME/.claude" ] && [ ! -e "$HOME/.claude/skills/humanize" ]; then
  mkdir -p "$HOME/.claude/skills" && ln -s "$DIR" "$HOME/.claude/skills/humanize"
fi

exec python3 "$DIR/humanize.py" init "$@"
