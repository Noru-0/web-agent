"""
Browser automation controller.

Handles low-level browser interactions: clicking, typing, scrolling, etc.
Used by both explorers and the core SLM agent.
"""

from typing import Optional, Dict, Any, List
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class BrowserConfig:
    """Configuration for browser automation"""
    headless: bool = False
    timeout: int = 30000  # milliseconds
    viewport_width: int = 1280
    viewport_height: int = 720
    user_agent: Optional[str] = None


class BrowserController(ABC):
    """
    Abstract base class for browser automation.
    
    Implementations can use Playwright, Selenium, or other tools.
    """
    
    def __init__(self, config: Optional[BrowserConfig] = None):
        self.config = config or BrowserConfig()
    
    @abstractmethod
    async def start(self):
        """Initialize browser"""
        pass
    
    @abstractmethod
    async def close(self):
        """Close browser"""
        pass
    
    @abstractmethod
    async def navigate(self, url: str) -> bool:
        """
        Navigate to URL.
        
        Returns:
            True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    async def click(self, selector: str) -> bool:
        """
        Click element.
        
        Args:
            selector: CSS selector or XPath
            
        Returns:
            True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    async def type_text(self, selector: str, text: str) -> bool:
        """
        Type text into element.
        
        Args:
            selector: CSS selector or XPath
            text: Text to type
            
        Returns:
            True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    async def scroll(self, direction: str = "down", amount: int = 100) -> bool:
        """
        Scroll the page.
        
        Args:
            direction: "up", "down", "left", "right"
            amount: Pixels to scroll
            
        Returns:
            True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    async def get_html(self) -> str:
        """Get current page HTML"""
        pass
    
    @abstractmethod
    async def get_url(self) -> str:
        """Get current page URL"""
        pass
    
    @abstractmethod
    async def screenshot(self, path: Optional[str] = None) -> bytes:
        """
        Take screenshot.
        
        Args:
            path: Optional path to save screenshot
            
        Returns:
            Screenshot bytes
        """
        pass
    
    @abstractmethod
    async def get_interactive_elements(self) -> List[Dict[str, Any]]:
        """
        Get list of interactive elements on the page.
        
        Returns:
            List of elements with selector, tag, text, etc.
        """
        pass


class PlaywrightController(BrowserController):
    """
    Playwright-based browser controller.
    
    This is a concrete implementation using Playwright.
    """
    
    def __init__(self, config: Optional[BrowserConfig] = None):
        super().__init__(config)
        self.browser = None
        self.page = None
    
    async def start(self):
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            raise ImportError("Playwright not installed. Run: pip install playwright")
        
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=self.config.headless
        )
        self.page = await self.browser.new_page(
            viewport={
                "width": self.config.viewport_width,
                "height": self.config.viewport_height
            },
            user_agent=self.config.user_agent
        )
    
    async def close(self):
        if self.page:
            await self.page.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
    
    async def navigate(self, url: str) -> bool:
        try:
            await self.page.goto(url, timeout=self.config.timeout)
            return True
        except Exception as e:
            print(f"Navigation failed: {e}")
            return False
    
    async def click(self, selector: str) -> bool:
        try:
            await self.page.click(selector, timeout=self.config.timeout)
            return True
        except Exception as e:
            print(f"Click failed: {e}")
            return False
    
    async def type_text(self, selector: str, text: str) -> bool:
        try:
            await self.page.fill(selector, text, timeout=self.config.timeout)
            return True
        except Exception as e:
            print(f"Type failed: {e}")
            return False
    
    async def scroll(self, direction: str = "down", amount: int = 100) -> bool:
        try:
            if direction == "down":
                await self.page.evaluate(f"window.scrollBy(0, {amount})")
            elif direction == "up":
                await self.page.evaluate(f"window.scrollBy(0, -{amount})")
            elif direction == "left":
                await self.page.evaluate(f"window.scrollBy(-{amount}, 0)")
            elif direction == "right":
                await self.page.evaluate(f"window.scrollBy({amount}, 0)")
            return True
        except Exception as e:
            print(f"Scroll failed: {e}")
            return False
    
    async def get_html(self) -> str:
        return await self.page.content()
    
    async def get_url(self) -> str:
        return self.page.url
    
    async def screenshot(self, path: Optional[str] = None) -> bytes:
        screenshot_bytes = await self.page.screenshot(path=path)
        return screenshot_bytes
    
    async def get_interactive_elements(self) -> List[Dict[str, Any]]:
        """Extract interactive elements from the page"""
        elements = await self.page.evaluate("""
            () => {
                const interactive = document.querySelectorAll('a, button, input, select, textarea, [onclick], [role="button"]');
                return Array.from(interactive).map((el, idx) => ({
                    index: idx,
                    tag: el.tagName.toLowerCase(),
                    id: el.id,
                    class: el.className,
                    text: el.textContent?.trim().substring(0, 100),
                    type: el.type,
                    name: el.name,
                    selector: el.id ? `#${el.id}` : null
                }));
            }
        """)
        return elements
