#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

# Use the system python (3.14.4) explicitly — pyliblo3 0.17.0 is known-good
# on it, and the PATH python3 may be a different interpreter.
PYTHON="/usr/bin/python3"

# 1. SuperCollider runtime (scsynth + sclang)
if ! command -v scsynth >/dev/null 2>&1 || ! command -v sclang >/dev/null 2>&1; then
    echo "installing supercollider..."
    sudo apt-get update
    sudo apt-get install -y supercollider
fi

# 2. Project venv (idempotent)
if [ ! -x ".venv/bin/python" ]; then
    echo "creating .venv..."
    "$PYTHON" -m venv .venv
fi

# 3. Editable install + dev deps (idempotent)
.venv/bin/pip install -q --upgrade pip
.venv/bin/pip install -q -e ".[dev]"

echo "done. run: .venv/bin/python -m super_quneo_collider.server"
