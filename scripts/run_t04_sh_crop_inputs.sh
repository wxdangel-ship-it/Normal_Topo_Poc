#!/usr/bin/env bash
set -euo pipefail

# T04 cropped-input export runner for SH dataset under WSL.
# Main outputs: <repo>/outputs/_work/t04_intersection_modeling/sh_cropped_inputs/

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
DATASET_DIR="/mnt/d/TestData/highway_topo_poc_data/Intersection/SH"
OUTPUT_ROOT="${REPO_ROOT}/outputs/_work/t04_intersection_modeling/sh_cropped_inputs"
CROP_BUFFER_M="80"
MAINNODEIDS=()

print_help() {
  cat <<'EOF'
Usage:
  bash scripts/run_t04_sh_crop_inputs.sh [options]

Options:
  --mainnodeid <id...>            Required. One or more mainnodeid values; also accepts comma-separated items
  --mainnodeids <id...>           Legacy plural alias, kept for compatibility
  --dataset-dir <path>            Optional. WSL dataset dir containing RCSDNode / RCSDRoad
  --output-root <path>            Optional. Output root under repo outputs
  --crop-buffer-m <meters>        Optional. BBox padding used for clipped export
  --help                          Show this help

Defaults:
  repo_root   = /mnt/d/Work/Normal_Topo_Poc
  dataset_dir = /mnt/d/TestData/highway_topo_poc_data/Intersection/SH
  output_root = /mnt/d/Work/Normal_Topo_Poc/outputs/_work/t04_intersection_modeling/sh_cropped_inputs

Examples:
  bash scripts/run_t04_sh_crop_inputs.sh --mainnodeid 12113465
  bash scripts/run_t04_sh_crop_inputs.sh --mainnodeid 12113465 12113466 --crop-buffer-m 120
  bash scripts/run_t04_sh_crop_inputs.sh --mainnodeid 12113465 --output-root /mnt/d/Tmp/t04_crop_check
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --mainnodeid|--mainnodeids)
      shift
      MAINNODEIDS=()
      while [[ $# -gt 0 && "${1}" != --* ]]; do
        MAINNODEIDS+=("$1")
        shift
      done
      ;;
    --dataset-dir)
      DATASET_DIR="$2"
      shift 2
      ;;
    --output-root)
      OUTPUT_ROOT="$2"
      shift 2
      ;;
    --crop-buffer-m)
      CROP_BUFFER_M="$2"
      shift 2
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
  --crop-inputs-only
  --output-dir "${OUTPUT_ROOT}"
  --crop-buffer-m "${CROP_BUFFER_M}"
  --mainnodeid
)
CMD+=("${MAINNODEIDS[@]}")

printf 'Running T04 cropped-input export:\n'
printf '  repo_root=%s\n' "${REPO_ROOT}"
printf '  dataset_dir=%s\n' "${DATASET_DIR}"
printf '  mainnodeid=%s\n' "${MAINNODEIDS[*]}"
printf '  output_root=%s\n' "${OUTPUT_ROOT}"
printf '  crop_buffer_m=%s\n' "${CROP_BUFFER_M}"

"${CMD[@]}"
