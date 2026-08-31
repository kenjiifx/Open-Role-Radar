#!/usr/bin/env bash
# Wrapper around the OpenRoleRadar sync command for CI and local use.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT/engine"

if ! command -v uv >/dev/null 2>&1; then
  echo "uv is required. Run scripts/bootstrap.sh first." >&2
  exit 1
fi

uv sync --all-extras --dev
exec uv run openroleradar sync "$@"
