from __future__ import annotations

import logging
import shutil
import time
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any

from .browser import LoginRequiredError, TistoryAutomationError, TistoryBrowser
from .config import ensure_folders, folder_path, load_config
from .content import Post, load_due_posts
from .state import StateStore
from .telegram import send_telegram_message


def run_publish(config_path: str | Path, dry_run: bool = False) -> int:
    config, _ = load_config(config_path)
    ensure_folders(config)
    logger = setup_logging(config)
    today = local_today(config)
    limit = int(config.get("posts_per_run", 3))
    effective_dry_run = dry_run or bool(config.get("publish", {}).get("dry_run"))

    posts, errors = load_due_posts(folder_path(config, "queue"), today, limit)
    for path, message in errors:
        logger.warning("Skipped file %s: %s", path.name, message)

    if not posts:
        logger.info("No due posts for %s.", today.isoformat())
        return 0

    state = StateStore(folder_path(config, "data") / "state.json")
    logger.info("Publishing %d post(s). dry_run=%s", len(posts), effective_dry_run)

    with TistoryBrowser(config, logger) as browser:
        for post in posts:
            try:
                result = publish_with_retry(browser, post, config, logger, effective_dry_run)
            except LoginRequiredError as exc:
                message = (
                    "[Tistory Auto Publisher] 로그인 문제\n"
                    f"파일: {post.source_path.name}\n"
                    f"2회 재시도 후 실패: {exc}"
                )
                logger.error(message)
                safe_telegram(config, message, logger)
                return 2
            except Exception as exc:  # noqa: BLE001 - continue with file isolation.
                logger.exception("Publish failed for %s", post.source_path.name)
                move_to(folder_path(config, "failed"), post.source_path)
                safe_telegram(
                    config,
                    "[Tistory Auto Publisher] 발행 실패\n"
                    f"파일: {post.source_path.name}\n"
                    f"오류: {exc}",
                    logger,
                )
                continue

            if effective_dry_run:
                logger.info("Dry run complete, keeping file in queue: %s", post.source_path.name)
                continue

            state.mark_published(post.source_path, post.title, result.get("url"))
            move_to(folder_path(config, "done"), post.source_path)
            if config.get("telegram", {}).get("notify_on_success"):
                safe_telegram(
                    config,
                    "[Tistory Auto Publisher] 발행 완료\n"
                    f"제목: {post.title}\n"
                    f"URL: {result.get('url') or '확인 필요'}",
                    logger,
                )

    return 0


def publish_with_retry(
    browser: TistoryBrowser,
    post: Post,
    config: dict[str, Any],
    logger: logging.Logger,
    dry_run: bool,
) -> dict[str, str | None]:
    max_attempts = int(config["retry"].get("publish_retries", 2)) + 1
    max_login_attempts = int(config["retry"].get("login_retries", 2)) + 1
    delay = int(config["retry"].get("retry_delay_seconds", 60))
    last_error: Exception | None = None
    login_failures = 0

    for attempt in range(1, max_attempts + 1):
        try:
            logger.info("Publishing %s (attempt %d/%d)", post.source_path.name, attempt, max_attempts)
            return browser.publish_post(post, dry_run=dry_run)
        except LoginRequiredError as exc:
            login_failures += 1
            last_error = exc
            logger.warning(
                "Login check failed for %s (%d/%d): %s",
                post.source_path.name,
                login_failures,
                max_login_attempts,
                exc,
            )
            if login_failures < max_login_attempts:
                time.sleep(delay)
                continue
            raise
        except TistoryAutomationError as exc:
            last_error = exc
            logger.warning("Attempt %d failed: %s", attempt, exc)
            if attempt < max_attempts:
                time.sleep(delay)

    assert last_error is not None
    raise last_error


def setup_logging(config: dict[str, Any]) -> logging.Logger:
    logger = logging.getLogger("tistory_auto_publisher")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")

    log_file = folder_path(config, "logs") / "publisher.log"
    file_handler = RotatingFileHandler(log_file, maxBytes=1_000_000, backupCount=3, encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    return logger


def local_today(config: dict[str, Any]):
    timezone_name = config.get("timezone", "")
    try:
        from zoneinfo import ZoneInfo

        return datetime.now(ZoneInfo(timezone_name)).date()
    except Exception:
        return datetime.now().date()


def move_to(target_dir: Path, source: Path) -> Path:
    target_dir.mkdir(parents=True, exist_ok=True)
    target = unique_path(target_dir / source.name)
    shutil.move(str(source), str(target))
    return target


def unique_path(path: Path) -> Path:
    if not path.exists():
        return path
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return path.with_name(f"{path.stem}-{stamp}{path.suffix}")


def safe_telegram(config: dict[str, Any], text: str, logger: logging.Logger) -> None:
    try:
        send_telegram_message(config, text)
    except Exception as exc:  # noqa: BLE001 - notification failure should not crash publish run.
        logger.warning("Telegram notification failed: %s", exc)
