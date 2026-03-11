"""
Minimal browser session wrapper.

This provides a clean interface to browser automation without exposing
Playwright-specific objects to the rest of the system.

RULES:
- Do NOT expose Playwright objects outside this file
- Keep interface minimal and explicit
- Return only simple Python types (str, dict, list)
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import base64
from pathlib import Path
from datetime import datetime


@dataclass
class BrowserSnapshot:
    """
    Immutable browser state snapshot.

    This is what the environment sees - no Playwright objects exposed.
    """
    url: str
    text: str  # Visible text content
    clickables: List[Dict[str, str]]  # List of clickable elements
    screenshot: Optional[str] = None  # Base64-encoded JPEG screenshot

    def to_dict(self) -> Dict[str, Any]:
        return {
            "url": self.url,
            "text": self.text,
            "clickables": self.clickables,
            "screenshot": self.screenshot
        }


class BrowserSession:
    """
    Minimal browser session for web agent.

    This wraps Playwright but exposes ONLY the necessary methods
    for basic web interaction.
    """

    def __init__(
        self,
        headless: bool = None,
        timeout: int = None,
        viewport_width: int = None,
        viewport_height: int = None,
        screenshot_mode: Optional[str] = None,
        screenshot_dir: Optional[str] = None
    ):
        """
        Initialize browser session.

        Args:
            headless: Run browser in headless mode (defaults from .env: BROWSER_HEADLESS)
            timeout: Default timeout in milliseconds (defaults from .env: BROWSER_TIMEOUT_MS)
            viewport_width: Viewport width (defaults from .env: BROWSER_VIEWPORT_WIDTH)
            viewport_height: Viewport height (defaults from .env: BROWSER_VIEWPORT_HEIGHT)
            screenshot_mode: Screenshot output mode:
                - "base64_jpeg" (default): compact base64 JPEG string
                - "base64_png": base64 PNG string
                - "png_file": save PNG to disk and return file path
            screenshot_dir: Directory for png_file mode (default: data/raw/screenshots)
        """
        # Load from .env if not explicitly provided
        from utils.env import env

        self.headless = headless if headless is not None else env.get_bool("BROWSER_HEADLESS", True)
        self.timeout = timeout if timeout is not None else env.get_int("BROWSER_TIMEOUT_MS", 30000)
        self.viewport_width = viewport_width if viewport_width is not None else env.get_int("BROWSER_VIEWPORT_WIDTH", 1280)
        self.viewport_height = viewport_height if viewport_height is not None else env.get_int("BROWSER_VIEWPORT_HEIGHT", 800)
        self.screenshot_mode = (screenshot_mode or env.get("SCREENSHOT_MODE", "base64_jpeg")).lower()
        self.screenshot_dir = Path(screenshot_dir or env.get("SCREENSHOT_DIR", "data/raw/screenshots"))
        self._screenshot_index = 0

        valid_modes = {"base64_jpeg", "base64_png", "png_file"}
        if self.screenshot_mode not in valid_modes:
            self.screenshot_mode = "base64_jpeg"

        # Playwright internals - NOT exposed outside this class
        self._playwright = None
        self._browser = None
        self._page = None
        self._started = False

    async def __aenter__(self):
        """Async context manager entry"""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()

    async def start(self):
        """Start browser session"""
        if self._started:
            return

        try:
            from playwright.async_api import async_playwright
        except ImportError:
            raise ImportError(
                "Playwright not installed. Run: pip install playwright && playwright install chromium"
            )

        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
            headless=self.headless
        )
        self._page = await self._browser.new_page(
            viewport={"width": self.viewport_width, "height": self.viewport_height}
        )
        self._page.set_default_timeout(self.timeout)
        self._started = True

    async def close(self):
        """Close browser session"""
        if not self._started:
            return

        if self._page:
            await self._page.close()
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()

        self._started = False

    async def open(self, url: str) -> bool:
        """
        Navigate to URL.

        Args:
            url: URL to navigate to

        Returns:
            True if successful, False otherwise
        """
        if not self._started:
            raise RuntimeError("Browser session not started. Call start() first.")

        try:
            await self._page.goto(url, wait_until="domcontentloaded")
            return True
        except Exception as e:
            print(f"Navigation failed: {e}")
            return False

    async def click(self, selector: str) -> bool:
        """
        Click element.

        Args:
            selector: CSS selector

        Returns:
            True if successful, False otherwise
        """
        if not self._started:
            raise RuntimeError("Browser session not started.")

        try:
            await self._page.click(selector)
            # Wait a bit for any navigation/updates
            await self._page.wait_for_timeout(500)
            return True
        except Exception as e:
            print(f"Click failed on '{selector}': {e}")
            return False

    async def type(self, selector: str, text: str) -> bool:
        """
        Type text into element.

        Args:
            selector: CSS selector
            text: Text to type

        Returns:
            True if successful, False otherwise
        """
        if not self._started:
            raise RuntimeError("Browser session not started.")

        try:
            await self._page.fill(selector, text)
            return True
        except Exception as e:
            print(f"Type failed on '{selector}': {e}")
            return False

    async def snapshot(self) -> BrowserSnapshot:
        """
        Take snapshot of current browser state.

        Returns:
            BrowserSnapshot with url, text, and clickables
        """
        if not self._started:
            raise RuntimeError("Browser session not started.")

        # --- SỬA ĐỔI 1: Thêm chờ đợi DOM ---
        try:
            # Chờ tối đa 2 giây để DOM được tải xong (tránh tình trạng body là null)
            await self._page.wait_for_load_state("domcontentloaded", timeout=2000)
        except Exception:
            # Nếu timeout (do mạng chậm hoặc trang đã load rồi), vẫn tiếp tục chạy
            pass

        # Get current URL
        url = self._page.url

        # Capture screenshot for multimodal LLM analysis.
        screenshot_b64 = None
        try:
            if self.screenshot_mode == "base64_png":
                screenshot_bytes = await self._page.screenshot(type="png")
                screenshot_b64 = base64.b64encode(screenshot_bytes).decode("ascii")
            elif self.screenshot_mode == "png_file":
                self.screenshot_dir.mkdir(parents=True, exist_ok=True)
                self._screenshot_index += 1
                timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%S")
                screenshot_path = self.screenshot_dir / f"screen_{timestamp}_{self._screenshot_index:04d}.png"
                await self._page.screenshot(type="png", path=str(screenshot_path))
                screenshot_b64 = str(screenshot_path)
            else:
                screenshot_bytes = await self._page.screenshot(type="jpeg", quality=60)
                screenshot_b64 = base64.b64encode(screenshot_bytes).decode("ascii")
        except Exception as e:
            print(f"Screenshot capture failed: {e}")

        # --- SỬA ĐỔI 2: Kiểm tra document.body tồn tại trước khi lấy text ---
        text = await self._page.evaluate("""
            () => {
                // Kiểm tra nếu body tồn tại thì mới lấy innerText, nếu không trả về chuỗi rỗng
                return document.body ? (document.body.innerText || '') : '';
            }
        """)

        # Get clickable elements
        clickables = await self._page.evaluate("""
            () => {
                // Nếu document chưa sẵn sàng, trả về mảng rỗng ngay lập tức
                if (!document || !document.body) return [];

                const elements = Array.from(document.querySelectorAll('a, button, [role="button"], [onclick]'));
                return elements.map((el, idx) => {
                    const rect = el.getBoundingClientRect();
                    // Only include visible elements
                    if (rect.width === 0 || rect.height === 0) return null;

                    const text = el.innerText || el.textContent || el.value || '';

                    // Xử lý an toàn cho classList và id
                    let selector = el.tagName.toLowerCase();
                    if (el.id) {
                        selector = `#${el.id}`;
                    } else if (el.className && typeof el.className === 'string' && el.className.trim() !== '') {
                        selector = `.${el.className.split(' ')[0]}`;
                    }

                    return {
                        id: `clickable_${idx}`,
                        selector: selector,
                        text: text.trim().substring(0, 50)
                    };
                }).filter(el => el !== null);
            }
        """)

        return BrowserSnapshot(
            url=url,
            text=text.strip(),
            clickables=clickables,
            screenshot=screenshot_b64
        )
