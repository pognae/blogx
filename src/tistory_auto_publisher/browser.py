from __future__ import annotations

import logging
import sys
from typing import Any

from .config import folder_path
from .content import Post


class TistoryAutomationError(RuntimeError):
    pass


class LoginRequiredError(TistoryAutomationError):
    pass


class PublishError(TistoryAutomationError):
    pass


class TistoryBrowser:
    def __init__(self, config: dict[str, Any], logger: logging.Logger) -> None:
        self.config = config
        self.logger = logger
        self.playwright: Any = None
        self.context: Any = None

    def __enter__(self) -> "TistoryBrowser":
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:
            raise TistoryAutomationError(
                "Playwright is not installed. Run: py -m pip install -r requirements.txt"
            ) from exc

        browser_config = self.config["browser"]
        profile_dir = folder_path(self.config, "browser_profile")
        profile_dir.mkdir(parents=True, exist_ok=True)
        self.playwright = sync_playwright().start()
        self.context = self._launch_persistent_context(profile_dir, browser_config)
        self.context.set_default_timeout(int(browser_config.get("timeout_ms", 45000)))
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        if self.context is not None:
            self.context.close()
        if self.playwright is not None:
            self.playwright.stop()

    def auth(self) -> None:
        page = self._page()
        page.goto(self.editor_url(), wait_until="domcontentloaded")
        self.logger.info("Browser opened for manual login: %s", page.url)
        print("브라우저에서 카카오/티스토리 로그인을 완료하고 2단계 인증까지 끝낸 뒤 Enter를 누르세요.")
        input()
        page.goto(self.editor_url(), wait_until="domcontentloaded")
        if self._looks_like_login(page):
            raise LoginRequiredError("Login still appears to be required.")
        self.logger.info("Login session looks ready.")

    def publish_post(self, post: Post, dry_run: bool = False) -> dict[str, str | None]:
        page = self._page()
        page.goto(self.editor_url(), wait_until="domcontentloaded")
        self._settle(page)
        if self._looks_like_login(page):
            raise LoginRequiredError("Tistory/Kakao login is required.")

        self._fill_title(page, post.title)
        self._fill_body(page, post.html, post.plain_text)

        if dry_run:
            screenshot_path = folder_path(self.config, "logs") / f"dry-run-{post.source_path.stem}.png"
            page.screenshot(path=str(screenshot_path), full_page=True)
            self.logger.info("Dry run screenshot saved: %s", screenshot_path)
            return {"url": None}

        self._complete_publish(page)
        self._settle(page, wait_ms=int(self.config["browser"].get("success_wait_ms", 8000)))
        return {"url": page.url}

    def editor_url(self) -> str:
        blog_name = self.config["blog_name"].replace("https://", "").replace("http://", "")
        blog_name = blog_name.replace(".tistory.com", "").strip("/")
        if not blog_name or blog_name == "your-blog-name":
            raise TistoryAutomationError("config.json의 blog_name을 실제 티스토리 블로그 이름으로 바꿔주세요.")
        return f"https://{blog_name}.tistory.com/manage/newpost/0"

    def _page(self) -> Any:
        if self.context is None:
            raise TistoryAutomationError("Browser context is not open.")
        if self.context.pages:
            return self.context.pages[0]
        return self.context.new_page()

    def _settle(self, page: Any, wait_ms: int = 1500) -> None:
        try:
            page.wait_for_load_state("networkidle", timeout=15000)
        except Exception:
            pass
        page.wait_for_timeout(wait_ms)

    def _looks_like_login(self, page: Any) -> bool:
        current_url = page.url.lower()
        if "accounts.kakao.com" in current_url or "/auth/login" in current_url:
            return True
        for selector in ("input[type='password']", "button:has-text('로그인')", "text=카카오계정"):
            try:
                if page.locator(selector).first.is_visible(timeout=1000):
                    return True
            except Exception:
                continue
        return False

    def _fill_title(self, page: Any, title: str) -> None:
        locator = self._find_first(page, self.config["publish"]["selectors"]["title"])
        if locator is None:
            raise PublishError("Could not find the Tistory title field.")
        try:
            locator.fill(title)
        except Exception:
            locator.click()
            page.keyboard.press(self._select_all_shortcut())
            page.keyboard.insert_text(title)
        self._dispatch_input(locator)
        self.logger.info("Title filled: %s", title)

    def _fill_body(self, page: Any, body_html: str, plain_text: str) -> None:
        editor = self._find_largest_editor(page, self.config["publish"]["selectors"]["body"])
        if editor is None:
            raise PublishError("Could not find the Tistory body editor.")
        editor.click()
        if not self._paste_html(page, editor, body_html, plain_text):
            self._insert_html(editor, body_html)
        self.logger.info("Body inserted (%d HTML chars).", len(body_html))

    def _complete_publish(self, page: Any) -> None:
        complete_clicked = self._click_first(page, self.config["publish"]["selectors"]["complete_buttons"])
        if not complete_clicked:
            raise PublishError("Could not find the first publish/complete button.")
        self._settle(page, wait_ms=1200)

        self._click_first(page, self.config["publish"]["selectors"]["public_controls"], optional=True)
        self._settle(page, wait_ms=500)

        final_clicked = self._click_first(
            page,
            self.config["publish"]["selectors"]["final_publish_buttons"],
            optional=True,
        )
        if final_clicked:
            self.logger.info("Final publish button clicked.")
        else:
            self.logger.info("No second publish button found; assuming the first click submitted.")

    def _find_first(self, page: Any, selectors: list[str]) -> Any | None:
        for frame in page.frames:
            for selector in selectors:
                try:
                    locator = frame.locator(selector).first
                    if locator.count() > 0 and locator.is_visible(timeout=1000):
                        return locator
                except Exception:
                    continue
        return None

    def _find_largest_editor(self, page: Any, selectors: list[str]) -> Any | None:
        best_locator = None
        best_area = 0.0
        for frame in page.frames:
            for selector in selectors:
                try:
                    locators = frame.locator(selector)
                    count = min(locators.count(), 12)
                except Exception:
                    continue
                for index in range(count):
                    locator = locators.nth(index)
                    try:
                        if not locator.is_visible(timeout=500):
                            continue
                        box = locator.bounding_box()
                        if not box:
                            continue
                        area = float(box["width"]) * float(box["height"])
                        if area > best_area:
                            best_area = area
                            best_locator = locator
                    except Exception:
                        continue
        return best_locator

    def _click_first(self, page: Any, selectors: list[str], optional: bool = False) -> bool:
        locator = self._find_first(page, selectors)
        if locator is None:
            if optional:
                return False
            return False
        locator.click()
        return True

    def _paste_html(self, page: Any, editor: Any, body_html: str, plain_text: str) -> bool:
        try:
            clipboard_ready = page.evaluate(
                """
                async ({html, text}) => {
                  if (!navigator.clipboard || !window.ClipboardItem) return false;
                  const item = new ClipboardItem({
                    "text/html": new Blob([html], { type: "text/html" }),
                    "text/plain": new Blob([text], { type: "text/plain" })
                  });
                  await navigator.clipboard.write([item]);
                  return true;
                }
                """,
                {"html": body_html, "text": plain_text},
            )
            if not clipboard_ready:
                return False
            editor.click()
            page.keyboard.press(self.config["browser"].get("paste_shortcut", "Control+V"))
            page.wait_for_timeout(1000)
            return True
        except Exception as exc:
            self.logger.debug("Clipboard HTML paste failed: %s", exc)
            return False

    def _insert_html(self, editor: Any, body_html: str) -> None:
        editor.evaluate(
            """
            (el, html) => {
              el.focus();
              el.innerHTML = "";
              const doc = el.ownerDocument;
              const win = doc.defaultView;
              const range = doc.createRange();
              range.selectNodeContents(el);
              range.collapse(false);
              const selection = win.getSelection();
              selection.removeAllRanges();
              selection.addRange(range);
              const inserted = doc.execCommand("insertHTML", false, html);
              if (!inserted) el.innerHTML = html;
              el.dispatchEvent(new InputEvent("input", { bubbles: true, inputType: "insertHTML", data: html }));
              el.dispatchEvent(new Event("change", { bubbles: true }));
            }
            """,
            body_html,
        )

    def _dispatch_input(self, locator: Any) -> None:
        try:
            locator.evaluate(
                """
                (el) => {
                  el.dispatchEvent(new Event("input", { bubbles: true }));
                  el.dispatchEvent(new Event("change", { bubbles: true }));
                }
                """
            )
        except Exception:
            pass

    def _select_all_shortcut(self) -> str:
        shortcut = self.config.get("browser", {}).get("select_all_shortcut")
        if shortcut:
            return str(shortcut)
        return "Meta+A" if sys.platform == "darwin" else "Control+A"

    def _launch_persistent_context(self, profile_dir: Any, browser_config: dict[str, Any]) -> Any:
        channel = browser_config.get("channel")
        base_kwargs = dict(
            user_data_dir=str(profile_dir),
            headless=bool(browser_config.get("headless", False)),
            slow_mo=int(browser_config.get("slow_mo_ms", 0)),
            viewport={"width": 1280, "height": 900},
            args=[
                "--disable-background-networking",
                "--disable-background-timer-throttling",
                "--disable-extensions",
                "--disable-notifications",
                "--disable-dev-shm-usage",
                "--no-first-run",
            ],
        )

        try:
            if channel:
                return self.playwright.chromium.launch_persistent_context(channel=channel, **base_kwargs)
            return self.playwright.chromium.launch_persistent_context(**base_kwargs)
        except Exception as exc:
            # Common on macOS/Linux when 'msedge' channel is configured but not installed.
            if channel:
                self.logger.warning("Browser launch failed with channel=%r; retrying without channel. (%s)", channel, exc)
                return self.playwright.chromium.launch_persistent_context(**base_kwargs)
            raise
