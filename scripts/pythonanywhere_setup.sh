#!/usr/bin/env bash
# PythonAnywhere(Ubuntu Bash console)에서 1회 실행하는 셋업 스크립트.
# - .venv 가상환경 생성
# - requirements.txt 설치
# - Playwright용 Chromium 다운로드
# - config.json이 없으면 예시에서 복사
#
# 사용법:
#   bash scripts/pythonanywhere_setup.sh
#   PYTHON=python3.10 bash scripts/pythonanywhere_setup.sh    # 인터프리터 강제 지정
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
cd "${PROJECT_DIR}"

VENV_DIR="${PROJECT_DIR}/.venv"

if [ -n "${PYTHON:-}" ]; then
  PY="${PYTHON}"
elif command -v python3.10 >/dev/null 2>&1; then
  PY="python3.10"
elif command -v python3 >/dev/null 2>&1; then
  PY="python3"
else
  echo "Python 3을 찾을 수 없습니다. PythonAnywhere 'Files' 탭에서 사용 가능한 인터프리터를 확인하세요." >&2
  exit 1
fi

echo "[setup] interpreter: ${PY} ($(${PY} --version 2>&1))"

if [ ! -d "${VENV_DIR}" ]; then
  echo "[setup] creating venv at ${VENV_DIR}"
  "${PY}" -m venv "${VENV_DIR}"
fi

# shellcheck disable=SC1091
source "${VENV_DIR}/bin/activate"

python -m pip install --upgrade pip
python -m pip install -r requirements.txt

# PythonAnywhere 무료 플랜은 외부 다운로드가 화이트리스트로 제한됩니다.
# Playwright의 Chromium 다운로드가 막히면 유료 플랜으로 업그레이드해야 합니다.
python -m playwright install chromium

if [ ! -f "${PROJECT_DIR}/config.json" ]; then
  cp "${PROJECT_DIR}/config.example.json" "${PROJECT_DIR}/config.json"
  echo "[setup] config.json 생성. blog_name, telegram 등을 편집하세요."
fi

mkdir -p "${PROJECT_DIR}/posts/queue" \
         "${PROJECT_DIR}/posts/done" \
         "${PROJECT_DIR}/posts/failed" \
         "${PROJECT_DIR}/logs" \
         "${PROJECT_DIR}/data" \
         "${PROJECT_DIR}/browser-profile"

echo "[setup] 완료."
echo
echo "다음 단계:"
echo "  1) 로컬 PC에서 'scripts/auth.sh' 또는 'scripts\\auth.bat'으로 카카오 2단계 인증까지 완료한 뒤"
echo "     'browser-profile/' 폴더 내용을 PythonAnywhere의 같은 위치로 업로드하세요."
echo "  2) config.json에서 \"headless\": true 로 변경하세요. (또는 TISTORY_HEADLESS=1 환경변수 사용)"
echo "  3) 한 번 dry-run으로 확인: bash scripts/pythonanywhere_run.sh --dry-run"
echo "  4) PythonAnywhere 'Tasks' 탭에서 매일 14:00에"
echo "       bash ${PROJECT_DIR}/scripts/pythonanywhere_run.sh"
echo "     를 등록하세요."
