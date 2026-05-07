from __future__ import annotations

import os
import urllib.parse
import urllib.request
from typing import Any


def send_telegram_message(config: dict[str, Any], text: str) -> bool:
    telegram = config.get("telegram", {})
    if not telegram.get("enabled"):
        return False

    token = os.getenv("TELEGRAM_BOT_TOKEN") or telegram.get("bot_token")
    chat_id = os.getenv("TELEGRAM_CHAT_ID") or telegram.get("chat_id")
    if not token or not chat_id:
        return False

    payload = urllib.parse.urlencode({"chat_id": chat_id, "text": text}).encode("utf-8")
    request = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data=payload,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=15) as response:  # noqa: S310 - configured Telegram endpoint.
        return 200 <= response.status < 300
