# Tistory Auto Publisher

구형 Windows 10 미니PC(2GB RAM)를 기준으로 만든 티스토리 자동 발행 도구입니다. 하루 종일 켜둔 PC에서 Windows 작업 스케줄러가 매일 오후 2시에 실행하고, `posts/queue` 폴더에 있는 `.md` 또는 `.txt` 글을 최대 3개까지 발행합니다.

티스토리 Open API는 공식 문서에 종료 안내가 있어 이 프로젝트는 API 대신 브라우저 자동화를 사용합니다. 카카오/티스토리 2단계 인증은 자동 우회하지 않고, 최초 1회 사용자가 직접 로그인한 Edge 프로필을 저장해 재사용합니다.

## 구조

```text
src/tistory_auto_publisher/   Python 소스
posts/queue/                  발행 대기 글
posts/done/                   발행 완료 글
posts/failed/                 발행 실패 글
logs/                         실행 로그와 dry-run 스크린샷
data/                         발행 기록
browser-profile/              Edge 로그인 세션 저장 폴더
scripts/                      Windows(.bat/.ps1) · macOS/Linux(.sh) · PythonAnywhere 실행 스크립트
skills/tistory-auto-publisher/ Codex용 스킬 파일
```

## 설치

Windows PowerShell 또는 CMD에서 프로젝트 폴더로 이동한 뒤 실행합니다.

```bat
py -m pip install -r requirements.txt
copy config.example.json config.json
```

macOS(또는 Linux)에서는 Terminal에서 다음을 실행합니다. Python 3.9 이상이 필요합니다.

```bash
python3 -m pip install -r requirements.txt
cp config.example.json config.json
```

> macOS에는 기본적으로 Microsoft Edge가 없습니다. 코드가 자동으로 `msedge` 채널 설정을 무시하고 Playwright 기본 Chromium으로 폴백하므로 추가 작업이 필요한 경우 한 번만 `python3 -m playwright install chromium`을 실행하세요. 키보드 단축키(`Meta+V`, `Meta+A`)도 자동으로 macOS에 맞게 보정됩니다.

`config.json`에서 아래 값을 바꿉니다.

```json
{
  "blog_name": "내-티스토리-블로그이름",
  "posts_per_run": 3,
  "telegram": {
    "enabled": true,
    "bot_token": "",
    "chat_id": "",
    "notify_on_success": false
  }
}
```

Telegram 토큰은 파일에 직접 적어도 되지만, 환경변수 사용을 권장합니다.

```bat
setx TELEGRAM_BOT_TOKEN "123456:ABC..."
setx TELEGRAM_CHAT_ID "123456789"
```

## 최초 로그인

2단계 인증 때문에 최초 1회는 사람이 직접 로그인해야 합니다.

Windows:

```bat
scripts\auth.bat
```

macOS/Linux:

```bash
scripts/auth.sh
```

브라우저가 열리면 카카오/티스토리 로그인과 2단계 인증을 완료하고, 터미널에서 Enter를 누릅니다. 이 세션은 `browser-profile/`에 저장됩니다.

## 글 파일 작성

파일명에서 날짜와 제목을 가져옵니다.

```text
2026-05-08_첫 번째 글.md
20260508_두번째 글.txt
```

규칙:

- 날짜가 오늘 이하인 파일만 발행합니다.
- 매 실행마다 `posts_per_run` 개수까지만 발행합니다. 기본값은 3개입니다.
- 직접 이미지 URL 한 줄을 넣으면 이미지 블록으로 변환합니다.
- 첫 번째 이미지 URL은 대표 이미지 후보가 되도록 본문에 삽입됩니다.

예:

```md
# 본문 안 제목

첫 문단입니다.

https://example.com/image.jpg

마지막 문단입니다.
```

## 단위 테스트 실행

파싱과 변환 로직에 대한 단위 테스트는 OS에 관계없이 같은 코드를 사용합니다. 외부 의존성(Playwright, 네트워크)이 없어 설치 직후에도 바로 실행할 수 있습니다.

Windows:

```bat
scripts\run_tests.bat
```

macOS/Linux:

```bash
scripts/run_tests.sh
```

스크립트가 자동으로 `PYTHONPATH=src`를 설정하고 `python3`(없으면 `python`)으로 `unittest`를 실행합니다. 특정 인터프리터를 강제하려면 `PYTHON=python3.12 scripts/run_tests.sh` 처럼 환경변수로 지정할 수 있습니다.

직접 명령으로 실행하고 싶다면 다음과 동일합니다.

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

## 발행 테스트 실행

처음에는 실제 발행 전에 dry-run으로 에디터 입력까지만 확인하세요.

Windows:

```bat
scripts\run_dry_run.bat
```

macOS/Linux:

```bash
scripts/run_dry_run.sh
```

문제가 없으면 1회 실제 발행을 테스트합니다.

Windows:

```bat
scripts\run_publish_once.bat
```

macOS/Linux:

```bash
scripts/run_publish_once.sh
```

## 매일 오후 2시 스케줄 등록

Windows에서는 PowerShell을 관리자 권한으로 열고 실행합니다.

```powershell
powershell -ExecutionPolicy Bypass -File scripts\install_task.ps1 -Time 14:00
```

등록 후 Windows 작업 스케줄러에서 `TistoryAutoPublisher` 작업을 확인할 수 있습니다.

macOS는 `launchd`나 `cron`을 사용해 같은 효과를 낼 수 있습니다. 예시(매일 14:00 실행, `cron` 사용):

```bash
crontab -e
# 아래 줄을 추가하세요. PATH/경로는 환경에 맞게 수정합니다.
0 14 * * * cd /Users/<you>/work/GitHub/blogx && /usr/bin/env bash scripts/run_publish_once.sh >> logs/cron.log 2>&1
```

> macOS는 본 프로젝트의 1차 타깃이 아니므로 스케줄러 설치 스크립트는 제공하지 않습니다. 개발/테스트 용도로 사용하세요.

## PythonAnywhere에서 운영

PC를 켜둘 수 없을 때 [pythonanywhere.com](https://www.pythonanywhere.com) Bash 콘솔 + Scheduled Tasks를 이용해 같은 방식으로 매일 자동 발행할 수 있습니다.

### 1. 플랜과 제약 (무료 플랜 기준)

이 가이드는 **무료(Beginner) 플랜**을 전제로 합니다. 무료 플랜은 외부 네트워크가 화이트리스트로 제한되므로 다음 사항을 먼저 확인하세요.

- `github.com`은 기본 허용되므로 `git clone`은 됩니다.
- `python -m playwright install chromium`은 Playwright CDN을 사용하므로 차단될 수 있습니다. 차단되면 화이트리스트에 등록 요청하거나, 유료 플랜으로 업그레이드해야 합니다.
- 실행 시 접근하는 `*.tistory.com`, `*.kakao.com`, Telegram API(`api.telegram.org`)도 화이트리스트에 없으면 차단됩니다. 발행 전 Bash 콘솔에서 `curl -I https://<도메인>` 으로 확인하고, 막히면 PythonAnywhere 포럼/지원팀에 화이트리스트 추가를 요청하세요.

### 2. 업로드할 파일 목록 (무료 플랜용 최소 구성)

저장소 전체를 올릴 필요가 없습니다. PythonAnywhere의 홈 디렉터리 아래(`~/blogx/`)에 **아래 항목만** 두면 충분합니다.

| 경로 | 필수 | 설명 |
| --- | --- | --- |
| `src/tistory_auto_publisher/` (폴더 전체) | 필수 | Python 소스 8개 파일 (`__init__.py`, `__main__.py`, `browser.py`, `config.py`, `content.py`, `publisher.py`, `state.py`, `telegram.py`) |
| `requirements.txt` | 필수 | 의존성 목록 (Playwright) |
| `scripts/pythonanywhere_setup.sh` | 필수 | 1회 셋업 스크립트 |
| `scripts/pythonanywhere_run.sh` | 필수 | Scheduled Tasks가 호출하는 진입점 |
| `config.json` | 필수 | 로컬에서 한 번 편집해서 그대로 업로드 (`blog_name`, `headless: true` 등) |
| `browser-profile/` (폴더 전체) | 필수 | 로컬에서 `auth`로 로그인한 뒤 만들어진 세션 디렉터리 |
| `posts/queue/<날짜>_<제목>.md` | 필수 | 발행 대기 글 |
| `config.example.json` | 선택 | 참고용. 없어도 동작에 영향 없음 |
| `README.md` | 선택 | 콘솔에서 참고용 |

**업로드하지 않아도 되는 항목** (무료 플랜에서는 불필요)

- `.git/`, `.DS_Store`, `__pycache__/`
- `tests/`, `examples/`, `skills/`
- `pyproject.toml` (`requirements.txt`만으로 설치 가능)
- `scripts/` 안의 다른 파일들: `auth.bat`, `auth.sh`, `install_task.ps1`, `run_dry_run.bat`, `run_dry_run.sh`, `run_publish_once.bat`, `run_publish_once.sh`, `run_tests.bat`, `run_tests.sh` (모두 로컬용)
- `data/`, `logs/`, `posts/done/`, `posts/failed/` (셋업 스크립트가 자동 생성)

업로드 후 최종 디렉터리 구조 예시:

```text
~/blogx/
├── src/tistory_auto_publisher/   # 소스 8개 .py
├── scripts/
│   ├── pythonanywhere_setup.sh
│   └── pythonanywhere_run.sh
├── browser-profile/              # 로컬에서 만들어 업로드
├── posts/queue/                  # 발행할 .md, .txt
├── config.json
└── requirements.txt
```

### 3. 업로드 방법

PythonAnywhere의 **Bash console**에서 git clone으로 받는 게 가장 간단하지만, 위 표의 항목만 추리고 싶다면 두 가지 방법 중 골라 쓰세요.

방법 A — git clone 후 불필요 파일 삭제(가장 간단):

```bash
git clone https://github.com/<YOUR_GITHUB>/blogx.git
cd blogx
rm -rf tests examples skills pyproject.toml
find scripts -type f ! -name 'pythonanywhere_*.sh' -delete
```

방법 B — 로컬에서 압축해 Files 탭으로 업로드:

```bash
# 로컬 PC에서:
tar czf blogx-upload.tgz \
  src/tistory_auto_publisher \
  scripts/pythonanywhere_setup.sh \
  scripts/pythonanywhere_run.sh \
  requirements.txt \
  config.json \
  browser-profile \
  posts/queue
# blogx-upload.tgz 를 PythonAnywhere 'Files' 탭에서 업로드한 뒤 콘솔에서:
mkdir -p ~/blogx && cd ~/blogx
tar xzf ~/blogx-upload.tgz
```

### 4. 셋업 실행

```bash
cd ~/blogx
bash scripts/pythonanywhere_setup.sh
```

`scripts/pythonanywhere_setup.sh`가 자동으로 다음을 수행합니다.

- `.venv/` 가상환경 생성
- `requirements.txt` 설치
- `python -m playwright install chromium` 실행 (무료 플랜에서 차단되면 위 1번 항목 참고)
- 누락된 작업 폴더(`posts/done`, `posts/failed`, `logs`, `data`) 자동 생성

특정 Python 버전을 강제하려면 `PYTHON=python3.10 bash scripts/pythonanywhere_setup.sh` 처럼 환경변수로 지정합니다.

### 5. 업로드 전 로컬 PC에서 준비

PythonAnywhere에는 GUI가 없으므로 카카오/티스토리의 2단계 인증을 거기서 직접 통과할 수 없습니다. 업로드 전에 로컬에서 두 가지를 끝내야 합니다.

**(a) 로그인 세션 만들기.** 로컬에서 한 번만 실행해 `browser-profile/` 폴더를 만들고, 그 폴더 자체를 업로드합니다.

```bash
# Windows
scripts\auth.bat
# macOS/Linux
scripts/auth.sh
```

**(b) `config.json` 편집.** PythonAnywhere에서는 반드시 **headless**로 띄워야 합니다.

- `config.json`에서 `"browser.headless": true` 로 변경
- 또는 환경변수 `TISTORY_HEADLESS=1` 지정 (스케줄러 스크립트가 자동으로 1을 세팅하므로 안 바꿔도 됩니다)

```json
{
  "blog_name": "내-티스토리-블로그이름",
  "posts_per_run": 3,
  "browser": {
    "headless": true,
    "extra_args": []
  },
  "telegram": {
    "enabled": true,
    "bot_token": "",
    "chat_id": "",
    "notify_on_success": false
  }
}
```

> 코드가 Linux + headless를 감지하면 `--no-sandbox`, `--disable-gpu`, `--disable-software-rasterizer` 플래그를 자동으로 추가합니다. 추가 인자가 필요하면 `browser.extra_args`에 문자열 리스트로 넣으면 됩니다(예: `["--proxy-server=http://..."]`).

### 6. dry-run 확인

```bash
cd ~/blogx
bash scripts/pythonanywhere_run.sh --dry-run
```

- 성공 시 `logs/publisher.log`와 `logs/dry-run-<파일명>.png` 스크린샷이 남습니다.
- 로그인 페이지 스크린샷이 찍히면 `browser-profile/` 업로드가 잘못된 경우이므로 다시 확인하세요.

### 7. 매일 14:00 스케줄 등록

PythonAnywhere 상단 메뉴의 **Tasks** 탭으로 이동해 새 Scheduled task를 추가합니다.

- **Time(UTC)**: 한국 시간 14:00 = UTC 05:00 으로 등록 (PythonAnywhere의 Tasks는 UTC 기준입니다)
- **Command**:

```bash
bash /home/<YOUR_USER>/blogx/scripts/pythonanywhere_run.sh
```

> `<YOUR_USER>`를 본인 PythonAnywhere 계정명으로 바꾸세요. 등록 후 Tasks 화면의 "Run now" 버튼으로 즉시 한 번 실행해 동작을 확인하세요.

`scripts/pythonanywhere_run.sh`가 자동으로 다음을 처리합니다.

- 프로젝트 루트로 `cd`
- `.venv` activate
- `PYTHONPATH=src` 설정
- `TISTORY_HEADLESS=1` 지정
- `python -m tistory_auto_publisher publish --config config.json` 실행

### 8. 로그/문제 해결

- 실행 로그: `~/blogx/logs/publisher.log`
- PythonAnywhere Tasks의 표준출력 로그: Tasks 화면의 각 작업 행에서 "log" 링크로 확인 가능
- 흔한 오류:
  - `LoginRequiredError`: `browser-profile/`이 비어 있거나, 세션이 만료되었습니다. 로컬에서 다시 `auth`를 돌린 뒤 재업로드하세요.
  - `Browser closed unexpectedly`: 메모리 부족일 가능성. 무료 플랜의 task당 메모리 한도가 낮으니 `posts_per_run`을 1~2로 줄이고, 큐에 들어 있는 글의 본문 길이도 함께 줄여 보세요.
  - `Playwright is not installed` / 브라우저 다운로드 실패: 무료 플랜의 화이트리스트에 Playwright CDN이 막혀 발생합니다. 콘솔에서 `source .venv/bin/activate && python -m playwright install chromium` 을 다시 시도하거나, PythonAnywhere 측에 화이트리스트 추가를 요청하세요.
  - `Net::ERR_CONNECTION_REFUSED` 등 `*.tistory.com` 접근 실패: 무료 플랜 화이트리스트에 도메인이 없는 경우입니다. 동일하게 화이트리스트 추가 요청이 필요합니다.

## 실패 처리

- 로그인 문제가 있으면 2번 재시도 후 Telegram으로 알림을 보냅니다.
- 로그인 문제인 경우 글 파일은 `posts/queue`에 그대로 둡니다.
- 발행 조작 실패나 에디터 셀렉터 실패는 해당 파일을 `posts/failed`로 이동하고 Telegram으로 알립니다.
- 성공 알림은 기본적으로 보내지 않습니다. 필요하면 `telegram.notify_on_success`를 `true`로 바꾸세요.
- 로그는 `logs/publisher.log`에 남습니다.

## 저사양 운용 팁

- 프로그램은 상주하지 않고, 작업 스케줄러가 오후 2시에만 실행합니다.
- Playwright는 별도 Chromium 다운로드 대신 Windows 10 기본 Edge(`msedge`)를 사용합니다.
- PC 절전 모드는 꺼두고, 작업 스케줄러의 “가능한 빨리 실행” 옵션을 유지하세요.

## 작업내역

2026-05-07:

- 티스토리 Open API 종료 상태를 확인하고 브라우저 자동화 방식으로 설계했습니다.
- `.md`, `.txt` 파일명에서 발행 가능일과 제목을 파싱하는 큐 기반 발행기를 작성했습니다.
- 이미지 URL을 HTML 이미지 블록으로 변환하고 첫 이미지를 대표 이미지 후보로 배치하도록 했습니다.
- Playwright + Microsoft Edge persistent profile 방식의 로그인/발행 자동화를 작성했습니다.
- 로그인 실패 2회 재시도, Telegram 알림, 완료/실패 폴더 이동, 발행 기록 저장을 추가했습니다.
- Windows 배치 파일과 매일 14:00 작업 스케줄러 등록 PowerShell 스크립트를 추가했습니다.
- Codex용 `skills/tistory-auto-publisher/SKILL.md` 스킬 파일을 만들었습니다.
- 파일 파싱과 변환 로직에 대한 기본 단위 테스트를 추가했습니다.

2026-05-14:

- macOS/Linux에서 테스트와 발행 스크립트를 실행할 수 있도록 `scripts/run_tests.sh`, `scripts/run_dry_run.sh`, `scripts/run_publish_once.sh`, `scripts/auth.sh`를 추가했습니다.
- 일관성을 위해 Windows용 `scripts/run_tests.bat`도 함께 추가했습니다.
- README에 macOS 설치/테스트/dry-run/발행/스케줄 운용 절차를 정리했습니다.
- PythonAnywhere 운영 지원을 추가했습니다.
  - Linux + headless 환경에서 `--no-sandbox`, `--disable-gpu`, `--disable-software-rasterizer` 플래그를 자동 보강합니다.
  - `browser.extra_args` 설정 값과 `TISTORY_HEADLESS` 환경변수로 headless를 외부에서 강제할 수 있습니다.
  - `scripts/pythonanywhere_setup.sh`(venv·pip·playwright·폴더 자동 셋업), `scripts/pythonanywhere_run.sh`(Scheduled tasks용 진입점)를 추가했습니다.
  - README에 무료 플랜 기준 업로드 파일 목록과 전체 운영 절차(플랜 제약, 업로드, 로컬 준비, dry-run, 스케줄, 로그)를 정리했습니다.

## 참고

- 티스토리 Open API 종료 안내: https://tistory.github.io/document-tistory-apis/
- 기존 글 작성 API 문서: https://tistory.github.io/document-tistory-apis/apis/v1/post/write.html
