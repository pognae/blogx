#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd -- "${SCRIPT_DIR}/.." && pwd)"

cd "${PROJECT_DIR}"

if [ -n "${PYTHON:-}" ]; then
  PY="${PYTHON}"
elif command -v python3 >/dev/null 2>&1; then
  PY="python3"
elif command -v python >/dev/null 2>&1; then
  PY="python"
else
  echo "Python을 찾을 수 없습니다. Python 3.9+를 설치한 뒤 다시 실행하세요." >&2
  exit 1
fi

export PYTHONPATH="${PROJECT_DIR}/src${PYTHONPATH:+:${PYTHONPATH}}"

exec "${PY}" -m unittest discover -s tests -v "$@"
