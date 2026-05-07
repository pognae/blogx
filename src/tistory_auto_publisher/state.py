from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any


class StateStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.data: dict[str, Any] = {"published": []}
        self.load()

    def load(self) -> None:
        if not self.path.exists():
            return
        with self.path.open("r", encoding="utf-8") as handle:
            self.data = json.load(handle)
        self.data.setdefault("published", [])

    def save(self) -> None:
        tmp_path = self.path.with_suffix(".tmp")
        with tmp_path.open("w", encoding="utf-8") as handle:
            json.dump(self.data, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        tmp_path.replace(self.path)

    def mark_published(self, source: Path, title: str, url: str | None) -> None:
        self.data.setdefault("published", []).append(
            {
                "source": str(source),
                "title": title,
                "url": url,
                "published_at": datetime.now().isoformat(timespec="seconds"),
            }
        )
        self.save()
