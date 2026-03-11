#!/usr/bin/env bash
set -euo pipefail

# Compatibility alias for the official SH module runner.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "${SCRIPT_DIR}/run_t04_sh_module.sh" "$@"
