#!/usr/bin/env bash
# Bootstrap local development dependencies for OpenRoleRadar.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "==> OpenRoleRadar bootstrap"

if ! command -v uv >/dev/null 2>&1; then
  echo "Installing uv..."
  curl -LsSf https://astral.sh/uv/install.sh | sh
  # shellcheck disable=SC1091
  [[ -f "$HOME/.local/bin/env" ]] && source "$HOME/.local/bin/env"
fi

if ! command -v pnpm >/dev/null 2>&1; then
  echo "Enabling pnpm via corepack..."
  command -v node >/dev/null 2>&1 || {
    echo "Node.js 22+ is required. Install from https://nodejs.org/" >&2
    exit 1
  }
  corepack enable
  corepack prepare pnpm@9 --activate
fi

echo "==> Python engine"
(cd engine && uv sync --all-extras --dev)

echo "==> Astro site"
(cd site && pnpm install)

echo "==> Validate seed sources"
uv run --directory engine python ../scripts/validate-sources.py

cat <<EOF

Bootstrap complete.

Next steps:
  cd engine && uv run openroleradar sync --sample
  cd site && pnpm dev
EOF
