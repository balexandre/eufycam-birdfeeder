#!/usr/bin/env bash
# Rebuild every model file and preview render from cad/feeder.py (needs Docker).
set -euo pipefail
cd "$(dirname "$0")/.."
docker build -q -t birdfeeder-cad cad/ >/dev/null
docker run --rm -u "$(id -u):$(id -g)" -e MPLCONFIGDIR=/tmp -e XDG_CACHE_HOME=/tmp \
  -v "$PWD":/work -w /work/cad birdfeeder-cad python export.py
