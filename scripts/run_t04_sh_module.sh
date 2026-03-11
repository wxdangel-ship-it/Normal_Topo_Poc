#!/usr/bin/env bash
set -euo pipefail

# Official T04 SH module runner for WSL.
# Defaults target the current intranet SH dataset and write outputs under the repo.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
DATASET_DIR="/mnt/d/TestData/highway_topo_poc_data/Intersection/SH"
OUTPUT_ROOT="${REPO_ROOT}/outputs/_work/t04_intersection_modeling/sh_manual_mode"
COMPUTE_BUFFER_M="200"
MANUAL_OVERRIDE=""
MAINNODEIDS=()
VALIDATE_OVERRIDE="1"

print_help() {
  cat <<'EOF'
Usage:
  bash scripts/run_t04_sh_module.sh [options]

Options:
  --mainnodeid <id...>            Required. One or more mainnodeid values; also accepts comma-separated items
  --mainnodeids <id...>           Legacy plural alias, kept for compatibility
  --dataset-dir <path>            Optional. WSL dataset dir containing RCSDNode / RCSDRoad
                                  Default: /mnt/d/TestData/highway_topo_poc_data/Intersection/SH
  --manual-override <path>        Optional override JSON file or per-mainnodeid override directory
  --output-root <path>            Optional output root under repo outputs
  --compute-buffer-m <meters>     Reserved compute buffer for future optimization only
  --skip-override-validation      Skip override validator before rerun
  --help                          Show this help

Examples:
  bash scripts/run_t04_sh_module.sh --mainnodeid 12113465
  bash scripts/run_t04_sh_module.sh --mainnodeid 12113465 12113466
  bash scripts/run_t04_sh_module.sh --mainnodeid 12113465 --manual-override /mnt/d/override/12113465.json
  bash scripts/run_t04_sh_module.sh --dataset-dir /mnt/d/TestData/highway_topo_poc_data/Intersection/SH --mainnodeid 12113465
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dataset-dir)
      DATASET_DIR="$2"
      shift 2
      ;;
    --mainnodeid|--mainnodeids)
      shift
      MAINNODEIDS=()
      while [[ $# -gt 0 && "${1}" != --* ]]; do
        MAINNODEIDS+=("$1")
        shift
      done
      ;;
    --manual-override)
      MANUAL_OVERRIDE="$2"
      shift 2
      ;;
    --output-root)
      OUTPUT_ROOT="$2"
      shift 2
      ;;
    --compute-buffer-m)
      COMPUTE_BUFFER_M="$2"
      shift 2
      ;;
    --skip-override-validation)
      VALIDATE_OVERRIDE="0"
      shift
      ;;
    --help|-h)
      print_help
      exit 0
      ;;
    *)
      echo "unknown_argument:$1" >&2
      print_help >&2
      exit 1
      ;;
  esac
done

if [[ ${#MAINNODEIDS[@]} -eq 0 ]]; then
  echo "missing_required_argument:--mainnodeid" >&2
  print_help >&2
  exit 1
fi

if [[ ! -d "${DATASET_DIR}" ]]; then
  echo "dataset_dir_not_found:${DATASET_DIR}" >&2
  exit 1
fi

if [[ -x "${REPO_ROOT}/.venv/bin/python" ]]; then
  PYTHON_BIN="${REPO_ROOT}/.venv/bin/python"
else
  PYTHON_BIN="python3"
fi

export PYTHONPATH="${REPO_ROOT}/src${PYTHONPATH:+:${PYTHONPATH}}"

CMD=(
  "${PYTHON_BIN}"
  -m
  normal_topo_poc.modules.t04_intersection_modeling.cli
  --dataset-dir "${DATASET_DIR}"
  --output-dir "${OUTPUT_ROOT}"
  --compute-buffer-m "${COMPUTE_BUFFER_M}"
  --mainnodeid
)
CMD+=("${MAINNODEIDS[@]}")

if [[ -n "${MANUAL_OVERRIDE}" ]]; then
  CMD+=(--manual-override "${MANUAL_OVERRIDE}")
  if [[ "${VALIDATE_OVERRIDE}" == "1" ]]; then
    CMD+=(--validate-override)
  fi
fi

printf 'Running T04 SH module:\n'
printf '  repo_root=%s\n' "${REPO_ROOT}"
printf '  dataset_dir=%s\n' "${DATASET_DIR}"
printf '  mainnodeid=%s\n' "${MAINNODEIDS[*]}"
printf '  output_root=%s\n' "${OUTPUT_ROOT}"
printf '  compute_buffer_m=%s\n' "${COMPUTE_BUFFER_M}"
if [[ -n "${MANUAL_OVERRIDE}" ]]; then
  printf '  manual_override=%s\n' "${MANUAL_OVERRIDE}"
fi

"${CMD[@]}"
