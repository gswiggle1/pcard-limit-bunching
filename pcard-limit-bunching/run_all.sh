#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/src"
python load.py
python analysis.py
python figures.py
