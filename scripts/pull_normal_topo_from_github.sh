#!/usr/bin/env bash
set -euo pipefail

# Clone or fast-forward pull Normal_Topo_Poc from GitHub under WSL.

REPO_DIR="/mnt/d/Work/Normal_Topo_Poc"
REMOTE_URL="git@github.com:wxdangel-ship-it/Normal_Topo_Poc.git"
BRANCH="main"

print_help() {
  cat <<'EOF'
Usage:
  bash scripts/pull_normal_topo_from_github.sh [options]

Options:
  --repo-dir <path>              Optional. WSL repo dir. Default: /mnt/d/Work/Normal_Topo_Poc
  --remote-url <url>             Optional. Git remote URL. Default: git@github.com:wxdangel-ship-it/Normal_Topo_Poc.git
  --branch <name>                Optional. Branch to clone/pull. Default: main
  --help                         Show this help

Behavior:
  1. If repo dir does not exist, clone from GitHub.
  2. If repo dir exists and is a git repo, fetch + checkout target branch + pull --ff-only.
  3. If working tree is dirty, abort instead of overwriting local changes.

Examples:
  bash scripts/pull_normal_topo_from_github.sh
  bash scripts/pull_normal_topo_from_github.sh --branch main
  bash scripts/pull_normal_topo_from_github.sh --repo-dir /mnt/d/Work/Normal_Topo_Poc
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --repo-dir)
      REPO_DIR="$2"
      shift 2
      ;;
    --remote-url)
      REMOTE_URL="$2"
      shift 2
      ;;
    --branch)
      BRANCH="$2"
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

PARENT_DIR="$(dirname "${REPO_DIR}")"

printf 'GitHub sync target:\n'
printf '  repo_dir=%s\n' "${REPO_DIR}"
printf '  remote_url=%s\n' "${REMOTE_URL}"
printf '  branch=%s\n' "${BRANCH}"

mkdir -p "${PARENT_DIR}"

if [[ ! -d "${REPO_DIR}" ]]; then
  printf 'Repo not found. Cloning...\n'
  git clone --branch "${BRANCH}" "${REMOTE_URL}" "${REPO_DIR}"
  printf 'Clone complete.\n'
  exit 0
fi

if [[ ! -d "${REPO_DIR}/.git" ]]; then
  echo "repo_dir_exists_but_not_git_repo:${REPO_DIR}" >&2
  exit 1
fi

cd "${REPO_DIR}"

if [[ -n "$(git status --porcelain)" ]]; then
  echo "working_tree_dirty:${REPO_DIR}" >&2
  echo "Please commit or stash local changes before pulling." >&2
  exit 1
fi

printf 'Fetching origin...\n'
git fetch --prune origin

CURRENT_BRANCH="$(git branch --show-current || true)"
if [[ "${CURRENT_BRANCH}" != "${BRANCH}" ]]; then
  printf 'Switching branch: %s -> %s\n' "${CURRENT_BRANCH:-detached}" "${BRANCH}"
  git checkout "${BRANCH}"
fi

printf 'Pulling latest commits...\n'
git pull --ff-only origin "${BRANCH}"

if command -v git-lfs >/dev/null 2>&1; then
  printf 'Running git lfs pull...\n'
  git lfs pull
fi

printf 'GitHub sync complete.\n'
