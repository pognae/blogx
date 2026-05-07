from __future__ import annotations

import html
import re
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Iterable


FILENAME_RE = re.compile(
    r"^(?P<date>\d{4}-?\d{2}-?\d{2})(?:[ _-]+(?P<title>.+?))?\.(?P<ext>md|txt)$",
    re.IGNORECASE,
)
IMAGE_URL_RE = re.compile(
    r"^https?://\S+\.(?:png|jpe?g|gif|webp)(?:\?\S*)?$",
    re.IGNORECASE,
)
MARKDOWN_IMAGE_RE = re.compile(r"!\[(?P<alt>[^\]]*)\]\((?P<url>https?://[^)\s]+)\)")
URL_RE = re.compile(r"https?://[^\s<>()\"']+")


@dataclass(frozen=True)
class Post:
    source_path: Path
    publish_date: date
    title: str
    html: str
    plain_text: str
    first_image_url: str | None = None


def parse_post_file(path: str | Path) -> Post:
    source = Path(path)
    publish_date, title_from_name = parse_filename(source.name)
    raw = source.read_text(encoding="utf-8-sig")
    title = title_from_name or first_heading(raw) or source.stem
    body_html = markdown_to_html(raw, source.suffix.lower())
    return Post(
        source_path=source,
        publish_date=publish_date,
        title=title,
        html=body_html,
        plain_text=html_to_text(body_html),
        first_image_url=extract_first_image(raw, body_html),
    )


def parse_filename(filename: str) -> tuple[date, str]:
    match = FILENAME_RE.match(filename)
    if not match:
        raise ValueError(
            "Unsupported filename. Use YYYY-MM-DD_title.md, YYYYMMDD_title.md, "
            "YYYY-MM-DD_title.txt, or YYYYMMDD_title.txt."
        )
    raw_date = match.group("date")
    if "-" in raw_date:
        publish_date = datetime.strptime(raw_date, "%Y-%m-%d").date()
    else:
        publish_date = datetime.strptime(raw_date, "%Y%m%d").date()
    raw_title = match.group("title") or ""
    title = raw_title.replace("_", " ").strip(" -_")
    return publish_date, title


def load_due_posts(queue_dir: Path, today: date, limit: int) -> tuple[list[Post], list[tuple[Path, str]]]:
    posts: list[Post] = []
    errors: list[tuple[Path, str]] = []
    candidates = sorted(
        [
            path
            for path in queue_dir.iterdir()
            if path.is_file() and path.suffix.lower() in {".md", ".txt"}
        ],
        key=lambda path: path.name,
    )

    for path in candidates:
        try:
            post = parse_post_file(path)
        except Exception as exc:  # noqa: BLE001 - keep bad files visible in logs.
            errors.append((path, str(exc)))
            continue
        if post.publish_date <= today:
            posts.append(post)
        if len(posts) >= limit:
            break

    posts.sort(key=lambda post: (post.publish_date, post.source_path.name))
    return posts, errors


def first_heading(raw: str) -> str | None:
    for line in raw.splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            return stripped[2:].strip()
    return None


def extract_first_image(raw: str, body_html: str) -> str | None:
    markdown_image = MARKDOWN_IMAGE_RE.search(raw)
    if markdown_image:
        return markdown_image.group("url")
    for line in raw.splitlines():
        stripped = line.strip()
        if IMAGE_URL_RE.match(stripped):
            return stripped
    html_image = re.search(r"<img[^>]+src=[\"'](?P<url>https?://[^\"']+)[\"']", body_html)
    if html_image:
        return html_image.group("url")
    return None


def markdown_to_html(raw: str, suffix: str) -> str:
    if suffix == ".txt":
        return text_to_html(raw)
    return md_to_html(raw)


def text_to_html(raw: str) -> str:
    blocks: list[str] = []
    paragraph: list[str] = []

    def flush_paragraph() -> None:
        if paragraph:
            blocks.append("<p>" + "<br>".join(html.escape(line) for line in paragraph) + "</p>")
            paragraph.clear()

    for line in raw.splitlines():
        stripped = line.strip()
        if not stripped:
            flush_paragraph()
            continue
        if IMAGE_URL_RE.match(stripped):
            flush_paragraph()
            blocks.append(image_html(stripped, ""))
            continue
        paragraph.append(line)
    flush_paragraph()
    return "\n".join(blocks)


def md_to_html(raw: str) -> str:
    blocks: list[str] = []
    paragraph: list[str] = []
    list_items: list[str] = []
    in_code = False
    code_lines: list[str] = []

    def flush_paragraph() -> None:
        if paragraph:
            text = " ".join(part.strip() for part in paragraph)
            blocks.append(f"<p>{inline_markdown(text)}</p>")
            paragraph.clear()

    def flush_list() -> None:
        if list_items:
            blocks.append("<ul>\n" + "\n".join(list_items) + "\n</ul>")
            list_items.clear()

    def flush_code() -> None:
        if code_lines:
            blocks.append("<pre><code>" + html.escape("\n".join(code_lines)) + "</code></pre>")
            code_lines.clear()

    for line in raw.splitlines():
        stripped = line.strip()

        if stripped.startswith("```"):
            if in_code:
                flush_code()
                in_code = False
            else:
                flush_paragraph()
                flush_list()
                in_code = True
            continue

        if in_code:
            code_lines.append(line)
            continue

        if not stripped:
            flush_paragraph()
            flush_list()
            continue

        image_match = MARKDOWN_IMAGE_RE.fullmatch(stripped)
        if image_match:
            flush_paragraph()
            flush_list()
            blocks.append(image_html(image_match.group("url"), image_match.group("alt")))
            continue

        if IMAGE_URL_RE.match(stripped):
            flush_paragraph()
            flush_list()
            blocks.append(image_html(stripped, ""))
            continue

        if looks_like_raw_html(stripped):
            flush_paragraph()
            flush_list()
            blocks.append(stripped)
            continue

        heading = re.match(r"^(#{1,3})\s+(.+)$", stripped)
        if heading:
            flush_paragraph()
            flush_list()
            level = len(heading.group(1))
            blocks.append(f"<h{level}>{inline_markdown(heading.group(2))}</h{level}>")
            continue

        item = re.match(r"^[-*]\s+(.+)$", stripped)
        if item:
            flush_paragraph()
            list_items.append(f"<li>{inline_markdown(item.group(1))}</li>")
            continue

        paragraph.append(line)

    flush_paragraph()
    flush_list()
    if in_code:
        flush_code()
    return "\n".join(blocks)


def inline_markdown(text: str) -> str:
    escaped = html.escape(text)
    escaped = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", escaped)
    escaped = re.sub(r"`(.+?)`", r"<code>\1</code>", escaped)
    escaped = re.sub(
        r"\[(?P<label>[^\]]+)\]\((?P<url>https?://[^)\s]+)\)",
        lambda match: f'<a href="{html.escape(match.group("url"), quote=True)}">{match.group("label")}</a>',
        escaped,
    )
    return escaped


def image_html(url: str, alt: str) -> str:
    safe_url = html.escape(url, quote=True)
    safe_alt = html.escape(alt, quote=True)
    return f'<figure><img src="{safe_url}" alt="{safe_alt}"></figure>'


def looks_like_raw_html(line: str) -> bool:
    return line.startswith("<") and line.endswith(">") and bool(re.match(r"^</?[a-zA-Z][^>]*>$", line))


def html_to_text(body_html: str) -> str:
    text = re.sub(r"<br\s*/?>", "\n", body_html, flags=re.IGNORECASE)
    text = re.sub(r"</p\s*>", "\n\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    text = html.unescape(text)
    return "\n".join(line.rstrip() for line in text.splitlines()).strip()


def extract_urls(lines: Iterable[str]) -> list[str]:
    urls: list[str] = []
    for line in lines:
        urls.extend(URL_RE.findall(line))
    return urls
