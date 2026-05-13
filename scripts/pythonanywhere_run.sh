#!/usr/bin/env bash
# PythonAnywhere의 Scheduled Tasks가 호출하는 실행 스크립트.
#
# 등록 예시 (Tasks 탭의 Command 필드):
#   bash /home/<YOUR_USER>/blogx/scripts/pythonanywhere_run.sh
#
# 옵션:
#   bash scripts/pythonanywhere_run.sh --dry-run   # 실제 발행 없이 에디터 입력까지만 확인
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
cd "${PROJECT_DIR}"

VENV_DIR="${PROJECT_DIR}/.venv"
if [ -f "${VENV_DIR}/bin/activate" ]; then
  # shellcheck disable=SC1091
  source "${VENV_DIR}/bin/activate"
fi

export PYTHONPATH="${PROJECT_DIR}/src${PYTHONPATH:+:${PYTHONPATH}}"
# Scheduled tasks는 GUI가 없으므로 항상 headless로 강제합니다.
export TISTORY_HEADLESS="${TISTORY_HEADLESS:-1}"

exec python -m tistory_auto_publisher publish --config "${PROJECT_DIR}/config.json" "$@"
