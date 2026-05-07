---
name: tistory-auto-publisher
description: Maintain and operate a low-resource Windows Tistory auto-publisher that reads .md/.txt files from a queue folder, parses filename dates and titles, uses a persisted Edge/Playwright login session for Tistory web publishing, sends Telegram failure notifications, and installs or troubleshoots a daily Windows Task Scheduler run.
---

# Tistory Auto Publisher

## Core Workflow

Use the project root as the working directory. Prefer the lightweight scheduled CLI flow:

1. Edit `config.json`, especially `blog_name`, `posts_per_run`, and Telegram settings.
2. Run `py -m pip install -r requirements.txt`.
3. Set `PYTHONPATH` to the local `src` directory when running without installation.
4. Run `py -m tistory_auto_publisher auth --config config.json` once so the user can complete Kakao/Tistory login and 2FA manually.
5. Run `py -m tistory_auto_publisher publish --config config.json --dry-run` before the first real publish.
6. Install the daily 14:00 task with `scripts/install_task.ps1`.

Do not try to bypass 2FA. Keep browser session state in `browser-profile/` and ask the user to rerun `auth` if Tistory or Kakao requires a fresh login.

## File Queue Rules

Use `posts/queue` for pending posts. Accepted filenames:

- `YYYY-MM-DD_title.md`
- `YYYYMMDD_title.md`
- `YYYY-MM-DD_title.txt`
- `YYYYMMDD_title.txt`

The date is the first day the post may be published. At each run, publish files with dates less than or equal to today, sorted by date and filename, up to `posts_per_run`.

After a real publish, move the source file to `posts/done`. On non-login publish failure, move it to `posts/failed`. On login failure, keep the file in queue and notify Telegram after the configured retries. Send success notifications only when `telegram.notify_on_success` is true.

## Content Rules

Convert `.md` and `.txt` into HTML before pasting into the Tistory editor.

- A standalone image URL ending in `.jpg`, `.jpeg`, `.png`, `.gif`, or `.webp` becomes an image block.
- Markdown image syntax also becomes an image block.
- The first image URL is the representative image candidate because Tistory commonly uses the first post image as the thumbnail.
- Keep conversion simple and predictable; avoid adding large Markdown dependencies unless the user needs richer syntax.

## Automation Notes

Tistory Open API is no longer a reliable publishing target, so use browser automation against `https://{blog_name}.tistory.com/manage/newpost/0`.

Selectors for the Tistory editor live in `src/tistory_auto_publisher/config.py` defaults and can be overridden in `config.json` under `publish.selectors`. If Tistory changes its editor, update selectors instead of rewriting the publishing flow.

Use Microsoft Edge via Playwright channel `msedge` for Windows 10 and 2GB RAM. This avoids downloading a separate Chromium browser in most cases.

## Validation

Run parser tests locally with:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests
```

Use `doctor` to check configuration:

```bash
PYTHONPATH=src python3 -m tistory_auto_publisher doctor --config config.json
```
