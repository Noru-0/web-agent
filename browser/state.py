"""
Browser state extraction and representation.
"""

from typing import Optional, Dict, Any
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from schema import State


class BrowserState:
    """
    Manages browser state extraction.
    
    Converts raw browser data into unified State objects.
    """
    
    @staticmethod
    def from_browser(
        url: str,
        html: str,
        screenshot: Optional[bytes] = None,
        interactive_elements: Optional[list] = None,
        viewport: Optional[Dict[str, int]] = None
    ) -> State:
        """
        Create State object from browser data.
        
        Args:
            url: Current URL
            html: Page HTML
            screenshot: Optional screenshot bytes
            interactive_elements: Optional list of interactive elements
            viewport: Optional viewport dimensions
            
        Returns:
            State object
        """
        # Optional: Clean/simplify HTML here
        cleaned_html = BrowserState._clean_html(html)
        
        return State(
            url=url,
            html=cleaned_html,
            screenshot=screenshot,
            interactive_elements=interactive_elements,
            viewport=viewport
        )
    
    @staticmethod
    def _clean_html(html: str) -> str:
        """
        Clean and simplify HTML.
        
        Removes scripts, styles, comments, etc. to reduce size.
        """
        # Simple cleaning - can be enhanced
        import re
        
        # Remove scripts
        html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
        
        # Remove styles
        html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL | re.IGNORECASE)
        
        # Remove comments
        html = re.sub(r'<!--.*?-->', '', html, flags=re.DOTALL)
        
        # Collapse whitespace
        html = re.sub(r'\s+', ' ', html)
        
        return html.strip()
