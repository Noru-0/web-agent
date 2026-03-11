"""
Generic web environment for exploration.

This is a simple environment wrapper for exploring any website.
No task-specific logic - just provides the interface for exploration pipeline.
"""

from typing import Dict, Any, Tuple, Optional
import logging
from envs.base_env import WebEnv
from schema import Action
from browser.session import BrowserSession

logger = logging.getLogger(__name__)


class GenericWebEnv(WebEnv):
    """
    Generic web environment for exploration.

    Provides minimal interface for exploring any website without
    task-specific logic. Used by exploration pipeline to discover
    screens and transitions.
    """

    def __init__(
        self,
        start_url: str,
        headless: bool = True,
        max_steps: int = 50,
        screenshot_mode: str = "base64_jpeg",
        screenshot_dir: Optional[str] = None
    ):
        """
        Initialize generic web environment.

        Args:
            start_url: Starting URL for exploration
            headless: Run browser in headless mode
            max_steps: Maximum steps before episode ends
            screenshot_mode: Screenshot output mode for BrowserSession
            screenshot_dir: Directory for PNG screenshot files when using png_file mode
        """
        super().__init__(name="generic_web")
        self.start_url = start_url
        self.max_steps = max_steps
        self._current_url = start_url
        self._browser = BrowserSession(
            headless=headless,
            screenshot_mode=screenshot_mode,
            screenshot_dir=screenshot_dir
        )
        self._started = False

    async def reset(self) -> Dict[str, Any]:
        """
        Reset environment to starting URL.

        Returns:
            Initial observation dict with url, html, dom
        """
        logger.debug(f"Resetting environment to {self.start_url}")

        # Start browser if not started
        if not self._started:
            await self._browser.start()
            self._started = True

        # Navigate to start URL
        success = await self._browser.open(self.start_url)
        if not success:
            raise RuntimeError(f"Failed to open {self.start_url}")

        self._step_count = 0

        return await self.observe()

    async def step(self, action: Action) -> Tuple[Dict[str, Any], bool]:
        """
        Execute action and return observation.

        Args:
            action: Action to execute

        Returns:
            observation: Current state observation
            done: Whether max steps reached
        """
        logger.debug(f"Executing action: {action.type}")

        # Execute action via browser
        success = await self._execute_action(action)

        self._increment_step()

        # Get observation
        obs = await self.observe()
        obs['action_success'] = success

        # Check if done
        done = self._step_count >= self.max_steps

        return obs, done

    async def observe(self) -> Dict[str, Any]:
        """
        Get current observation.

        Returns:
            Dict with url, html, visible_text, dom_elements
        """
        if not self._started:
            raise RuntimeError("Environment not started. Call reset() first.")

        # Get browser snapshot
        snapshot = await self._browser.snapshot()

        self._current_url = snapshot.url

        return {
            'url': snapshot.url,
            'html': snapshot.text,  # BrowserSession.snapshot() returns text, not full HTML
            'visible_text': snapshot.text,
            'dom_elements': snapshot.clickables,
            'screenshot': snapshot.screenshot,
            'step_count': self._step_count
        }

    async def close(self):
        """Clean up browser resources"""
        logger.debug("Closing environment")
        if self._started:
            try:
                await self._browser.close()
                self._started = False
            except Exception as e:
                logger.error(f"Error closing browser: {e}")

    async def _execute_action(self, action: Action) -> bool:
        """
        Execute action via browser session.

        Args:
            action: Action to execute

        Returns:
            True if successful, False otherwise
        """
        from schema import ActionType

        try:
            if action.type == ActionType.CLICK:
                return await self._browser.click(action.target)

            elif action.type == ActionType.TYPE:
                return await self._browser.type(action.target, action.value or "")

            elif action.type == ActionType.NAVIGATE:
                return await self._browser.open(action.target)

            elif action.type == ActionType.SCROLL:
                # BrowserSession doesn't have scroll yet
                logger.warning("SCROLL action not yet implemented in BrowserSession")
                return False

            elif action.type == ActionType.SELECT:
                logger.warning("SELECT action not yet implemented")
                return False

            elif action.type == ActionType.HOVER:
                logger.warning("HOVER action not yet implemented")
                return False

            else:
                logger.warning(f"Unknown action type: {action.type}")
                return False

        except Exception as e:
            logger.error(f"Error executing action: {e}")
            return False
