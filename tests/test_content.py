from __future__ import annotations

import tempfile
import unittest
from datetime import date
from pathlib import Path

from tistory_auto_publisher.content import load_due_posts, parse_filename, parse_post_file


class ContentTests(unittest.TestCase):
    def test_parse_filename_dash_date(self) -> None:
        publish_date, title = parse_filename("2026-05-08_샘플-글.md")
        self.assertEqual(publish_date, date(2026, 5, 8))
        self.assertEqual(title, "샘플-글")

    def test_parse_filename_compact_date(self) -> None:
        publish_date, title = parse_filename("20260508_두번째 글.txt")
        self.assertEqual(publish_date, date(2026, 5, 8))
        self.assertEqual(title, "두번째 글")

    def test_parse_post_file_converts_image_url(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "2026-05-08_이미지.md"
            path.write_text("# 제목\n\nhttps://example.com/a.jpg\n\n본문", encoding="utf-8")
            post = parse_post_file(path)
        self.assertIn("<img", post.html)
        self.assertEqual(post.first_image_url, "https://example.com/a.jpg")

    def test_load_due_posts_ignores_future_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            (folder / "2026-05-08_오늘.md").write_text("본문", encoding="utf-8")
            (folder / "2026-05-09_내일.md").write_text("본문", encoding="utf-8")
            posts, errors = load_due_posts(folder, date(2026, 5, 8), 3)
        self.assertFalse(errors)
        self.assertEqual([post.title for post in posts], ["오늘"])


if __name__ == "__main__":
    unittest.main()
