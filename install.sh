#!/usr/bin/env bash
# install.sh — put foodnomsctl on PATH.
#
# One Python file with no third-party dependencies, so installing is a copy.
# PREFIX defaults to ~/.local; set it to install elsewhere.
set -euo pipefail

PREFIX="${PREFIX:-$HOME/.local}"
BIN="$PREFIX/bin"
SRC="$(cd "$(dirname "$0")" && pwd)"

mkdir -p "$BIN"
install -m 0755 "$SRC/foodnomsctl" "$BIN/foodnomsctl"
echo "installed $BIN/foodnomsctl"

case ":$PATH:" in
    *":$BIN:"*) ;;
    *)
        echo
        echo "PATH action required — add this to your shell profile, then open a new terminal:"
        echo "  export PATH=\"$BIN:\$PATH\""
        ;;
esac

echo
echo "Next: foodnomsctl doctor"
