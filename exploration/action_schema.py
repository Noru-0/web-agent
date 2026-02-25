"""
Dual-representation action schema for exploration pipeline.

================================================================================
DEPRECATION WARNING - DO NOT USE IN NEW CODE
================================================================================

This file contains the OLD bundled Action class that violates the
semantic/executable separation principle.

USE INSTEAD:
- exploration.schema.ActionSemantic (semantic representation)
- exploration.executable_schema.ActionExecutable (executable representation)

The Action class that bundles both together is NOW DEPRECATED.
It will be removed once all code is migrated to proper separation.

For proper architecture, see:
- exploration/schema.py - Semantic models
- exploration/executable_schema.py - Executable models
- exploration/action_grounder.py - Bridges between them via action_id

================================================================================

CRITICAL DESIGN:
- Actions contain BOTH semantic (for LLM) and executable (for agent)
- Phase 1-2: Collect both representations
- Phase 3: Task synthesis uses ONLY semantic (LLM must not see selectors)
- Phase 4: Task execution uses executable to run actions

NEVER mix these concerns. The separation is by design.
"""

from dataclasses import dataclass, field, asdict
from typing import Dict, Any, Optional, List
from enum import Enum
import hashlib

from exploration.semantic_normalization import safe_get_description


class ActionCategory(str, Enum):
    """High-level action categories for semantic understanding"""
    NAVIGATION = "navigation"
    FORM_INPUT = "form_input"
    SELECTION = "selection"
    SEARCH = "search"
    SUBMISSION = "submission"
    FILTER = "filter"
    VIEW = "view"
    OTHER = "other"


@dataclass
class ActionExecutable:
    """
    Executable representation of an action.
    
    USAGE: Phase 2 (action execution) and Phase 4 (task execution)
    NEVER expose to LLM in Phase 3 (task synthesis)
    
    Contains concrete browser automation details:
    - DOM selectors
    - Element types
    - Coordinates (if needed)
    """
    type: str  # click, type, select, scroll, navigate, etc.
    selector: str  # CSS selector or XPath
    value: Optional[str] = None  # For type/select actions
    
    # Optional additional grounding info
    element_text: Optional[str] = None  # Text content of element
    element_type: Optional[str] = None  # button, input, link, etc.
    coordinates: Optional[Dict[str, int]] = None  # {x, y} if needed
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ActionExecutable':
        data = data.copy()
        return cls(**data)


@dataclass
class ActionSemantic:
    """
    Semantic representation of an action.
    
    USAGE: Phase 3 (task synthesis) - LLM consumes this ONLY
    
    Contains high-level intent and description:
    - Human-readable description
    - Intent category
    - NO selectors, NO DOM info, NO executable details
    """
    intent: str  # High-level intent: "checkout", "add_to_cart", "search_product"
    description: str  # Human-readable: "Proceed to checkout"
    category: ActionCategory
    
    # Optional semantic metadata (still no selectors!)
    expected_outcome: Optional[str] = None  # e.g., "Navigate to checkout page"
    prerequisites: Optional[List[str]] = None  # e.g., ["cart must have items"]
    
    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['category'] = self.category.value
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ActionSemantic':
        data = data.copy()
        data['category'] = ActionCategory(data['category'])
        return cls(**data)


@dataclass
class Action:
    """
    Complete action with BOTH semantic and executable representations.
    
    STORAGE: This is the persisted form in exploration results
    CONSUMPTION: Different phases access different fields
    
    Phase 1-2: Both fields populated during exploration
    Phase 3: Only semantic exposed to LLM (via SemanticProjector)
    Phase 4: Executable used for actual action execution (via ActionGrounder)
    """
    action_id: str  # Unique identifier
    executable: ActionExecutable  # For agent execution
    semantic: ActionSemantic  # For LLM reasoning
    
    # Metadata
    source_screen_id: Optional[str] = None  # Screen where action was discovered
    confidence: float = 1.0  # Confidence in executable correctness
    meta: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Generate action_id if not provided"""
        if not self.action_id:
            self.action_id = self._generate_id()
    
    def _generate_id(self) -> str:
        """Generate unique action ID from semantic content"""
        intent = getattr(self.semantic, 'intent', None) or ''
        desc = safe_get_description(self.semantic)
        content = f"{intent}::{desc}"
        return "a_" + hashlib.sha256(content.encode()).hexdigest()[:12]
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize with BOTH representations"""
        return {
            "action_id": self.action_id,
            "executable": self.executable.to_dict(),
            "semantic": self.semantic.to_dict(),
            "source_screen_id": self.source_screen_id,
            "confidence": self.confidence,
            "meta": self.meta
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Action':
        """Deserialize with BOTH representations"""
        data = data.copy()
        data['executable'] = ActionExecutable.from_dict(data['executable'])
        data['semantic'] = ActionSemantic.from_dict(data['semantic'])
        return cls(**data)
    
    def to_semantic_only(self) -> Dict[str, Any]:
        """
        Export ONLY semantic fields for LLM consumption.
        
        USAGE: Phase 3 (task synthesis)
        CRITICAL: This strips ALL executable information
        """
        return {
            "action_id": self.action_id,
            "intent": getattr(self.semantic, 'intent', None),
            "description": safe_get_description(self.semantic),
            "category": getattr(self.semantic, 'category', None).value if hasattr(self.semantic, 'category') else "other",
            "expected_outcome": getattr(self.semantic, 'expected_outcome', None)
        }


@dataclass
class ScreenWithActions:
    """
    Screen containing list of available actions.
    
    This is the enriched screen representation used in Phase 2.
    Actions list contains FULL Action objects (semantic + executable).
    """
    screen_id: str
    url: str
    screen_type: str
    semantic_summary: str  # LLM-generated summary
    actions: List[Action]  # Full actions with both representations
    
    # Metadata
    timestamp: str
    meta: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "screen_id": self.screen_id,
            "url": self.url,
            "screen_type": self.screen_type,
            "semantic_summary": self.semantic_summary,
            "actions": [a.to_dict() for a in self.actions],
            "timestamp": self.timestamp,
            "meta": self.meta
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ScreenWithActions':
        data = data.copy()
        data['actions'] = [Action.from_dict(a) for a in data['actions']]
        return cls(**data)
    
    def to_semantic_only(self) -> Dict[str, Any]:
        """
        Export screen with ONLY semantic action info.
        
        USAGE: Phase 3 (task synthesis)
        Strips executable details from all actions.
        """
        return {
            "screen_id": self.screen_id,
            "url": self.url,
            "screen_type": self.screen_type,
            "semantic_summary": self.semantic_summary,
            "actions": [a.to_semantic_only() for a in self.actions],
            "timestamp": self.timestamp
        }


@dataclass
class Transition:
    """
    Transition between screens via an action.
    
    IMPORTANT: Stores only action_id and semantic representation.
    Executable details are retrieved from Screen.actions when needed.
    """
    transition_id: str
    from_screen_id: str
    to_screen_id: str
    action_id: str  # Reference to action
    action_semantic: ActionSemantic  # Denormalized for convenience
    
    success: bool = True
    timestamp: Optional[str] = None
    meta: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "transition_id": self.transition_id,
            "from_screen_id": self.from_screen_id,
            "to_screen_id": self.to_screen_id,
            "action_id": self.action_id,
            "action_semantic": self.action_semantic.to_dict(),
            "success": self.success,
            "timestamp": self.timestamp,
            "meta": self.meta
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Transition':
        data = data.copy()
        data['action_semantic'] = ActionSemantic.from_dict(data['action_semantic'])
        return cls(**data)
    
    def to_semantic_only(self) -> Dict[str, Any]:
        """
        Export ONLY semantic transition info.
        
        USAGE: Phase 3 (task synthesis)
        """
        category_val = "other"
        if hasattr(self.action_semantic, 'category') and self.action_semantic.category:
            category_val = self.action_semantic.category.value
        
        return {
            "transition_id": self.transition_id,
            "from_screen_id": self.from_screen_id,
            "to_screen_id": self.to_screen_id,
            "action_id": self.action_id,
            "intent": getattr(self.action_semantic, 'intent', None),
            "description": safe_get_description(self.action_semantic),
            "category": category_val
        }


@dataclass
class ExplorationResult:
    """
    Complete exploration result with screens and transitions.
    
    STORAGE: Persists FULL data (semantic + executable)
    CONSUMPTION: Different projections for different phases
    """
    screens: Dict[str, ScreenWithActions]  # screen_id -> Screen
    transitions: List[Transition]
    
    explorer_name: str
    start_url: str
    timestamp: str
    meta: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "screens": {sid: s.to_dict() for sid, s in self.screens.items()},
            "transitions": [t.to_dict() for t in self.transitions],
            "explorer_name": self.explorer_name,
            "start_url": self.start_url,
            "timestamp": self.timestamp,
            "meta": self.meta
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ExplorationResult':
        data = data.copy()
        data['screens'] = {
            sid: ScreenWithActions.from_dict(s) 
            for sid, s in data['screens'].items()
        }
        data['transitions'] = [Transition.from_dict(t) for t in data['transitions']]
        return cls(**data)
    
    def get_action_by_id(self, action_id: str) -> Optional[Action]:
        """
        Retrieve full action (semantic + executable) by ID.
        
        Searches through all screen actions to find matching action_id.
        """
        for screen in self.screens.values():
            for action in screen.actions:
                if action.action_id == action_id:
                    return action
        return None
