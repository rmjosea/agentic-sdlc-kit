#!/usr/bin/env sh
# Agentic SDLC Kit - one-command installer.
#
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/rmjosea/agentic-sdlc-kit/main/install.sh | sh
#   curl -fsSL https://raw.githubusercontent.com/rmjosea/agentic-sdlc-kit/main/install.sh | sh -s -- --profile full
#   ./install.sh [/path/to/repo] [--profile default|full] [--with NAME] [--init-config] [--dry-run]
#
# Without a target path, the current directory is the target. All options are
# forwarded unchanged to scripts/install.py (run with --help for the list).
#
# Environment:
#   AGENTIC_SDLC_KIT_REPO  Git URL to download from (default: the rmjosea repository).
#   AGENTIC_SDLC_KIT_REF   Branch or tag to download (default: main). Pin a release
#                          tag for reproducible installs.
#
# Requires git and python3 (standard library only). When run from a local clone,
# nothing is downloaded. Exit status is the installer's exit status.
set -eu

command -v python3 >/dev/null 2>&1 || {
  echo "Error: python3 is required but was not found in PATH." >&2
  exit 1
}

KIT_REPO="${AGENTIC_SDLC_KIT_REPO:-https://github.com/rmjosea/agentic-sdlc-kit.git}"
KIT_REF="${AGENTIC_SDLC_KIT_REF:-main}"

# A target was given when any non-option argument appears that is not the value
# of --profile, --with, or --on-conflict. Help also needs no injected target.
HAS_TARGET=0
SKIP_NEXT=0
for arg in "$@"; do
  if [ "$SKIP_NEXT" -eq 1 ]; then
    SKIP_NEXT=0
    continue
  fi
  case "$arg" in
    --profile|--with|--on-conflict) SKIP_NEXT=1 ;;
    -h|--help) HAS_TARGET=1 ;;
    -*) ;;
    *) HAS_TARGET=1 ;;
  esac
done

run_installer() {
  installer="$1"
  shift
  if [ "$HAS_TARGET" -eq 1 ]; then
    python3 "$installer" "$@"
  else
    python3 "$installer" "$(pwd -P)" "$@"
  fi
}

SCRIPT_DIR="$(CDPATH='' cd -- "$(dirname -- "$0")" 2>/dev/null && pwd -P || true)"
if [ -n "$SCRIPT_DIR" ] && [ -f "$SCRIPT_DIR/scripts/install.py" ]; then
  run_installer "$SCRIPT_DIR/scripts/install.py" "$@"
  exit $?
fi

command -v git >/dev/null 2>&1 || {
  echo "Error: git is required to download the kit but was not found in PATH." >&2
  exit 1
}

TMP_DIR="$(mktemp -d "${TMPDIR:-/tmp}/agentic-sdlc-kit.XXXXXX")"
trap 'rm -rf "$TMP_DIR"' EXIT
trap 'exit 130' INT TERM

git clone --quiet --depth 1 --branch "$KIT_REF" "$KIT_REPO" "$TMP_DIR/kit"

status=0
run_installer "$TMP_DIR/kit/scripts/install.py" "$@" || status=$?
exit "$status"
