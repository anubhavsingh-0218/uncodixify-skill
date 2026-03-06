#!/usr/bin/env bash
set -euo pipefail

PACKAGE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ $# -lt 1 ]]; then
  echo "Usage: ./bin/run-uncodixify.sh <path-to-file>" >&2
  exit 1
fi

TARGET_FILE="$1"
npx tsx "$PACKAGE_DIR/toolchain/uncodixify.ts" "$TARGET_FILE"
