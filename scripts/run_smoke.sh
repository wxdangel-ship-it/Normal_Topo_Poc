#!/usr/bin/env bash
set -euo pipefail

PYTHONPATH=src python -m normal_topo_poc doctor
PYTHONPATH=src python -m pytest -q
