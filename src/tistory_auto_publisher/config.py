from __future__ import annotations

import json
import os
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any


DEFAULT_CONFIG: dict[str, Any] = {
    "blog_name": "your-blog-name",
    "timezone": "Asia/Seoul",
    "posts_per_run": 3,
    "folders": {
        "queue": "posts/queue",
        "done": "posts/done",
        "failed": "posts/failed",
        "logs": "logs",
        "data": "data",
        "browser_profile": "browser-profile",
    },
    "browser": {
        "channel": "msedge",
        "headless": False,
        "slow_mo_ms": 0,
        "timeout_ms": 45000,
        "success_wait_ms": 8000,
        "paste_shortcut": "Control+V",
        "select_all_shortcut": "Control+A",
        "extra_args": [],
    },
    "publish": {
        "dry_run": False,
        "visibility": "public",
        "selectors": {
            "title": [
                "textarea[placeholder*='제목']",
                "input[placeholder*='제목']",
                "#post-title-inp",
                "textarea[name='title']",
                "input[name='title']",
            ],
            "body": [
                "div[contenteditable='true']",
                "[contenteditable='true']",
                ".ProseMirror",
                ".editor [contenteditable='true']",
            ],
            "complete_buttons": [
                "button:has-text('완료')",
                "a:has-text('완료')",
                "[role=button]:has-text('완료')",
                "button:has-text('발행')",
            ],
            "public_controls": [
                "input[type='radio'][value='20']",
                "input[type='radio'][value='public']",
                "label:text-is('공개')",
                "button:text-is('공개')",
            ],
            "final_publish_buttons": [
                "button:has-text('발행')",
                "button:has-text('공개 발행')",
                "[role=button]:has-text('발행')",
            ],
        },
    },
    "retry": {
        "login_retries": 2,
        "publish_retries": 2,
        "retry_delay_seconds": 60,
    },
    "telegram": {
        "enabled": False,
        "bot_token": "",
        "chat_id": "",
        "notify_on_success": False,
    },
}


def load_config(config_path: str | Path) -> tuple[dict[str, Any], Path]:
    path = Path(config_path).expanduser().resolve()
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")

    with path.open("r", encoding="utf-8") as handle:
        user_config = json.load(handle)

    config = deep_merge(DEFAULT_CONFIG, user_config)
    normalize_runtime_defaults(config)
    config["_config_path"] = str(path)
    config["_base_dir"] = str(path.parent)
    return config, path.parent


def normalize_runtime_defaults(config: dict[str, Any]) -> None:
    """
    Make config safer across OSes without requiring user edits.
    - 'msedge' channel is primarily for Windows; on non-Windows, fall back to Playwright default.
    - Keyboard shortcuts differ on macOS (Meta) vs Windows/Linux (Control).
    - Environment variables let hosted environments (e.g. PythonAnywhere) override safely.
    """

    browser = config.setdefault("browser", {})

    if sys.platform != "win32" and str(browser.get("channel") or "").lower() == "msedge":
        browser["channel"] = None

    if sys.platform == "darwin":
        if browser.get("paste_shortcut") in (None, "", "Control+V"):
            browser["paste_shortcut"] = "Meta+V"
        if browser.get("select_all_shortcut") in (None, "", "Control+A"):
            browser["select_all_shortcut"] = "Meta+A"
    else:
        if browser.get("paste_shortcut") in (None, ""):
            browser["paste_shortcut"] = "Control+V"
        if browser.get("select_all_shortcut") in (None, ""):
            browser["select_all_shortcut"] = "Control+A"

    headless_env = os.getenv("TISTORY_HEADLESS")
    if headless_env is not None:
        truthy = headless_env.strip().lower() in {"1", "true", "yes", "on"}
        falsy = headless_env.strip().lower() in {"0", "false", "no", "off"}
        if truthy:
            browser["headless"] = True
        elif falsy:
            browser["headless"] = False

    if "extra_args" not in browser or browser["extra_args"] is None:
        browser["extra_args"] = []


def write_default_config(path: str | Path) -> Path:
    target = Path(path).expanduser().resolve()
    if target.exists():
        raise FileExistsError(f"Config already exists: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8") as handle:
        json.dump(DEFAULT_CONFIG, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    return target


def deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    result = deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def resolve_path(base_dir: str | Path, value: str | Path) -> Path:
    raw = os.path.expandvars(os.path.expanduser(str(value)))
    path = Path(raw)
    if not path.is_absolute():
        path = Path(base_dir) / path
    return path.resolve()


def folder_path(config: dict[str, Any], key: str) -> Path:
    return resolve_path(config["_base_dir"], config["folders"][key])


def ensure_folders(config: dict[str, Any]) -> None:
    for key in ("queue", "done", "failed", "logs", "data", "browser_profile"):
        folder_path(config, key).mkdir(parents=True, exist_ok=True)
