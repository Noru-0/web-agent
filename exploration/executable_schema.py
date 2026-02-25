"""
Executable action schema - STRICTLY SEPARATED from semantic.

ARCHITECTURE RULE:
- This module contains ONLY executable browser actions
- NO semantic fields (intent, description, goals, etc.)
- Used ONLY by agents during execution (Phase 2, Phase 4)
- NEVER exposed to LLM or task synthesis (Phase 3)

BRIDGE TO SEMANTICS:
- Linked to ActionSemantic via action_id ONLY
- ActionGrounder maps action_id → ActionExecutable
- NO direct coupling or bundling

USAGE:
- Phase 2 (Exploration): Agents execute these to explore
- Phase 4 (Task Execution): Agents execute these to complete tasks
- Phase 3 (Task Synthesis): NEVER sees these fields
"""

from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional
from enum import Enum


class ActionType(str, Enum):
    """Low-level browser action types"""
    CLICK = "click"
    TYPE = "type"
    SELECT = "select"
    SCROLL = "scroll"
    NAVIGATE = "navigate"
    HOVER = "hover"
    PRESS_KEY = "press_key"
    WAIT = "wait"


@dataclass
class ActionExecutable:
    """
    Pure executable representation - concrete browser commands.
    
    CONTAINS:
    - DOM selectors (CSS/XPath)
    - Action type (click, type, etc.)
    - Values (for input actions)
    - Element info (for verification)
    - Coordinates (if needed)
    
    DOES NOT CONTAIN:
    - Semantic intent
    - Human descriptions
    - Goal information
    - Task context
    
    NEVER pass this to LLM prompts or task synthesis.
    """
    action_id: str  # Unique identifier (links to semantic via ActionGrounder)
    type: ActionType  # click, type, select, etc.
    selector: str  # CSS selector or XPath
    
    # Optional fields
    value: Optional[str] = None  # For type/select actions
    element_text: Optional[str] = None  # Text content (for verification)
    element_type: Optional[str] = None  # button, input, link, etc.
    coordinates: Optional[Dict[str, int]] = None  # {x, y} if selector fails
    
    # Metadata
    confidence: float = 1.0  # Confidence in selector correctness
    source_screen_id: Optional[str] = None  # Screen where discovered
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict"""
        data = asdict(self)
        data['type'] = self.type.value
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ActionExecutable':
        """Deserialize from dict"""
        data = data.copy()
        data['type'] = ActionType(data['type'])
        return cls(**data)
    
    def __repr__(self) -> str:
        """
        String representation showing ONLY executable details.
        NO semantic information.
        """
        parts = [f"{self.type.value}"]
        if self.selector:
            parts.append(f"selector={self.selector[:50]}")
        if self.value:
            parts.append(f"value={self.value[:20]}")
        return f"ActionExecutable({', '.join(parts)})"


# ============================================================================
# STORAGE CONTAINER - Not for direct use, only for persistence
# ============================================================================

@dataclass
class ActionBinding:
    """
    Storage container linking semantic and executable via action_id.
    
    USAGE: ONLY for storage/persistence, NOT for phase logic
    
    This is used ONLY when saving exploration results to disk.
    It allows reconstructing the mapping later.
    
    During phase execution:
    - Phase 2 agents: receive ActionExecutable only
    - Phase 3 LLM: receives semantic fields only
    - Phase 4 grounding: maps action_id between them
    
    NEVER pass this object to agents or LLMs.
    Use ActionGrounder to access the appropriate side.
    """
    action_id: str
    semantic_action_id: str  # Links to ActionSemantic.action_id
    executable_action_id: str  # Links to ActionExecutable.action_id
    
    # Optional metadata about the binding
    confidence: float = 1.0  # Confidence in semantic→executable mapping
    binding_method: str = "heuristic"  # How this was grounded
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ActionBinding':
        return cls(**data)
