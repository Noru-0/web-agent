"""
State encoder: converts State objects into feature representations for the SLM.
"""

from typing import Dict, Any, Optional
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from schema import State, EncodedState


class StateEncoder:
    """
    Encodes State objects into features for the SLM.
    
    This is where we define how the agent "sees" the world.
    """
    
    def __init__(
        self,
        max_html_length: int = 10000,
        include_screenshot: bool = False,
        include_dom_tree: bool = False
    ):
        self.max_html_length = max_html_length
        self.include_screenshot = include_screenshot
        self.include_dom_tree = include_dom_tree
    
    def encode(self, state: State) -> EncodedState:
        """
        Encode state into features.
        
        Args:
            state: State object
            
        Returns:
            Dictionary of encoded features
        """
        encoded = {
            "url": state.url,
            "html_truncated": state.html[:self.max_html_length],
            "html_length": len(state.html),
        }
        
        # Add interactive elements summary
        if state.interactive_elements:
            encoded["num_interactive"] = len(state.interactive_elements)
            encoded["interactive_types"] = self._summarize_elements(
                state.interactive_elements
            )
        
        # Optionally include screenshot
        if self.include_screenshot and state.screenshot:
            encoded["screenshot"] = state.screenshot
        
        # Optionally include DOM tree
        if self.include_dom_tree and state.dom_tree:
            encoded["dom_tree"] = state.dom_tree
        
        # Add viewport info
        if state.viewport:
            encoded["viewport"] = state.viewport
        
        return encoded
    
    def _summarize_elements(self, elements: list) -> Dict[str, int]:
        """Summarize interactive elements by type"""
        summary = {}
        for elem in elements:
            elem_type = elem.get("tag", "unknown")
            summary[elem_type] = summary.get(elem_type, 0) + 1
        return summary
    
    def encode_for_model(self, state: State) -> str:
        """
        Encode state as text for language model input.
        
        This creates a textual representation that an SLM can process.
        """
        parts = [
            f"URL: {state.url}",
            f"\nHTML (truncated to {self.max_html_length} chars):",
            state.html[:self.max_html_length]
        ]
        
        if state.interactive_elements:
            parts.append(f"\n\nInteractive Elements ({len(state.interactive_elements)}):")
            for i, elem in enumerate(state.interactive_elements[:20]):  # Show first 20
                tag = elem.get("tag", "?")
                text = elem.get("text", "")[:50]  # First 50 chars
                selector = elem.get("selector", elem.get("id", ""))
                parts.append(f"  [{i}] {tag}: {text} ({selector})")
        
        return "\n".join(parts)


class VisionEncoder:
    """
    Encodes screenshots/visual information for vision-language models.
    
    Optional: Use if your SLM supports vision.
    """
    
    def __init__(self, image_size: int = 224):
        self.image_size = image_size
    
    def encode_screenshot(self, screenshot_bytes: bytes) -> Any:
        """
        Encode screenshot for vision model.
        
        Returns:
            Encoded image tensor or features
        """
        # TODO: Implement vision encoding
        # This would use a vision encoder like CLIP, ResNet, etc.
        raise NotImplementedError("Vision encoding not yet implemented")
