"""
Data models for the EXPLORATION pipeline.

SCOPE: Screen Discovery and Semantic Analysis
- Used by: exploration/, workflows/explore.py
- Purpose: Model what exploration discovers (screens, transitions, affordances)

DISTINCTION FROM /schema.py (root):
- This file (exploration/schema.py): Discovery phase models
  * Screen: Semantic representation of UI states
  * ScreenType: Classification (homepage, login, form, etc.)
  * ActionSemantic: High-level action descriptions from LLM
  * Transition: Screen-to-screen navigation patterns
  * ExplorationResult: Complete discovery output

- /schema.py (root): Runtime execution models
  * Action, ActionType: Concrete executable actions
  * State: Runtime observation format
  * TrajectoryStep, Trajectory: Training data format

These serve DIFFERENT purposes and should NOT be merged:
- Exploration discovers "what's possible" (semantic, high-level)
- Runtime executes "what to do" (concrete, low-level)
- Training learns from "what was done" (trajectories)

The 4-phase pipeline bridges these:
  Phase 1-2: Exploration (this schema) → discovers screens + semantic actions
  Phase 3: Task Synthesis → uses semantic actions to generate tasks
  Phase 4: Task Execution → grounds to runtime actions (/schema.py)

================================================================================
SEMANTIC-ONLY CONTROL PRINCIPLE (ENFORCED)
================================================================================

CRITICAL ARCHITECTURE RULE:

1. SEMANTIC DATA controls all decision-making:
   - Action selection
   - Transition following
   - Task synthesis
   - Planning and reasoning

   Semantic fields: intent, object, context, description, confidence, action_id

2. EXECUTABLE DATA is write-only artifact:
   - Logged AFTER execution
   - Never read for decision-making
   - Never passed to LLM
   - Never influences which action is chosen

   Executable fields: selector, xpath, coordinates, dom_path, element_id

3. PHASE-SPECIFIC ENFORCEMENT:
   - Phase 2 (Exploration): Agent receives semantic → executes → logs executable
   - Phase 3 (Task Synthesis): LLM sees semantic ONLY (validated, no leaks)
   - Phase 4 (Task Execution): Agent receives semantic → grounds → executes

4. VALIDATION:
   - SemanticProjector validates no executable leaks to LLM
   - TaskSynthesis validates input is semantic-only
   - Storage preserves both but enforces access boundaries

================================================================================
"""

from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional
from enum import Enum
import hashlib
import json


class ScreenType(str, Enum):
    """Semantic screen types"""
    HOMEPAGE = "homepage"
    SEARCH = "search"
    PRODUCT_DETAIL = "product_detail"
    CART = "cart"
    CHECKOUT = "checkout"
    LOGIN = "login"
    FORM = "form"
    LISTING = "listing"
    ARTICLE = "article"
    NAVIGATION = "navigation"
    OTHER = "other"


@dataclass
class GroundingHints:
    """
    Soft grounding hints for executor agents.

    CRITICAL: These are NON-BINDING guidance signals, NOT hard constraints.
    The executor agent uses these to bias attention/prioritization, but remains
    responsible for all DOM grounding and action execution decisions.

    WHAT HINTS ARE:
    - Semantic constraints (keywords, affordances, regions)
    - Attention biases for the executor's policy
    - Interpretable signals within the agent's training distribution

    WHAT HINTS ARE NOT:
    - Element IDs, CSS selectors, XPath, DOM indices
    - Hard constraints that override executor policy
    - Specific element coordinates or identifiers

    Fields (all optional / arrays):
    - target_role: UI element types to look for (e.g., ["search_input", "search_button"])
    - element_affordance: Interaction types (e.g., ["type", "submit", "click"])
    - keywords: Words likely in element text/placeholder (lowercase)
    - exclude_keywords: Words indicating wrong elements (lowercase)
    - preferred_region: Screen areas to focus (e.g., ["header", "main_content"])
    - interaction_order: Sequence hint (e.g., "initial", "follow_up", "final")
    - sub_instance: Multi-step pattern (e.g., ["focus", "type", "submit"])

    Example usage by executor:
        for element in dom_elements:
            score = base_score(element)
            # Apply hint-based modifiers
            if any(kw in element.text for kw in hints.keywords):
                score *= 1.5  # Boost matching keywords
            if any(kw in element.text for kw in hints.exclude_keywords):
                score *= 0.3  # Penalize exclusions
            if element.region in hints.preferred_region:
                score *= 1.2  # Prefer suggested region
    """

    target_role: List[str] = field(default_factory=list)
    element_affordance: List[str] = field(default_factory=list)
    keywords: List[str] = field(default_factory=list)
    exclude_keywords: List[str] = field(default_factory=list)
    preferred_region: List[str] = field(default_factory=list)
    interaction_order: Optional[str] = None
    sub_instance: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'GroundingHints':
        """Create from dictionary."""
        data = data.copy()
        # Backward compatibility with older hint field names.
        if 'element_role' in data and 'target_role' not in data:
            role = data.get('element_role')
            data['target_role'] = [role] if isinstance(role, str) else (role or [])
        if 'interaction_type' in data and 'element_affordance' not in data:
            interaction = data.get('interaction_type')
            data['element_affordance'] = [interaction] if isinstance(interaction, str) else (interaction or [])

        valid_fields = {'target_role', 'element_affordance', 'keywords', 'exclude_keywords',
                       'preferred_region', 'interaction_order', 'sub_instance'}
        filtered_data = {k: v for k, v in data.items() if k in valid_fields}

        # Normalize to list if model returned a single string.
        list_fields = {
            'target_role', 'element_affordance', 'keywords',
            'exclude_keywords', 'preferred_region', 'sub_instance'
        }
        for field_name in list_fields:
            value = filtered_data.get(field_name)
            if isinstance(value, str):
                filtered_data[field_name] = [value]

        return cls(**filtered_data)

    @property
    def element_role(self) -> Optional[str]:
        """Backward-compatible alias for older hint schema."""
        return self.target_role[0] if self.target_role else None

    @property
    def interaction_type(self) -> Optional[str]:
        """Backward-compatible alias for older hint schema."""
        return self.element_affordance[0] if self.element_affordance else None

    def is_empty(self) -> bool:
        """Check if hints provide any guidance."""
        return (
            not self.target_role and
            not self.element_affordance and
            not self.keywords and
            not self.exclude_keywords and
            not self.preferred_region and
            not self.interaction_order and
            not self.sub_instance
        )


@dataclass
class Screen:
    """
    Represents a unique UI state.
    Defined semantically, not just by DOM.
    """
    screen_id: str  # Unique identifier (generated)
    url: str
    dom_snapshot: str  # Cleaned HTML
    visible_text: str  # Extracted visible text
    semantic_summary: str  # LLM-generated summary
    screen_type: ScreenType
    timestamp: str  # When captured
    screenshot: Optional[str] = None  # Base64 or path
    dom_fingerprint: Optional[str] = None  # For deduplication
    meta: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Generate screen_id and fingerprint if not provided"""
        if not self.screen_id:
            self.screen_id = self._generate_id()
        if not self.dom_fingerprint:
            self.dom_fingerprint = self._generate_fingerprint()

    def _generate_id(self) -> str:
        """Generate unique screen ID from content"""
        content = f"{self.url}::{self.semantic_summary}::{self.screen_type}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def _generate_fingerprint(self) -> str:
        """Generate DOM fingerprint for deduplication"""
        # Use URL pattern + key DOM features
        url_pattern = self._extract_url_pattern()
        dom_hash = hashlib.md5(self.dom_snapshot.encode()).hexdigest()[:8]
        text_hash = hashlib.md5(self.visible_text.encode()).hexdigest()[:8]
        return f"{url_pattern}::{dom_hash}::{text_hash}"

    def _extract_url_pattern(self) -> str:
        """Extract URL pattern (remove IDs, query params)"""
        from urllib.parse import urlparse
        parsed = urlparse(self.url)
        # Simple pattern: domain + path structure
        path = parsed.path
        # Replace numeric IDs with placeholder
        import re
        path = re.sub(r'\d+', '{id}', path)
        return f"{parsed.netloc}{path}"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        data = asdict(self)
        data['screen_type'] = self.screen_type.value
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Screen':
        """Create Screen from dictionary"""
        data = data.copy()
        data['screen_type'] = ScreenType(data['screen_type'])
        return cls(**data)


@dataclass
class ActionSemantic:
    """
    Structured semantic action representation with soft execution hints.

    Domain-agnostic, machine-parseable action intent without execution details.
    No selectors, no coordinates, no DOM references - pure semantic intent.

    NEW: Includes ActionHints for soft executor guidance
    - Hints are NON-BINDING signals
    - Executor uses them as attention biases, not hard constraints
    - Clean separation: LLM provides intent+hints, executor grounds+executes

    FLEXIBLE FORMAT:
    - Can store structured (intent+object+context) OR free-text (description only)
    - All fields are optional except action_id (auto-generated)
    - Description is generated if not provided
    - Hints are optional (None means no guidance)

    Format:
        intent: Verb phrase (e.g., "search", "navigate", "filter", "view") [Optional]
        object: Noun phrase from screen content (e.g., "items", "authentication flow") [Optional]
        context: Optional additional meaning (e.g., "via text input") [Optional]
        description: Free-text description (auto-generated if not provided) [Optional]
        hints: Soft execution hints for executor agent [Optional]
        confidence: Float 0.0-1.0 indicating certainty of action inference

    Examples:
        - {
            "intent": "view",
            "object": "product details",
            "grounding_hints": {
              "target_role": ["product_link", "view_button"],
              "element_affordance": ["click"],
              "keywords": ["view", "details", "product"],
              "exclude_keywords": ["login", "cart"],
              "preferred_region": ["main_content"],
              "interaction_order": "initial"
            },
            "confidence": 0.85
          }
        - {"description": "click login button", "confidence": 0.5}
    """
    intent: Optional[str] = None  # Verb phrase describing what to do
    object: Optional[str] = None  # Noun phrase - what the intent acts on
    context: Optional[str] = None  # Optional additional meaning
    description: Optional[str] = None  # Free-text description
    grounding_hints: Optional[GroundingHints] = None  # Soft grounding hints for executor (NEW)
    confidence: float = 0.75  # Confidence score 0.0-1.0
    action_id: str = ""  # Generated unique ID

    def __post_init__(self):
        # Generate description if not provided
        if not self.description:
            self.description = self._generate_description()

        # Generate action_id from content
        if not self.action_id:
            content = f"{self.intent}::{self.object}::{self.context}::{self.description}"
            self.action_id = hashlib.sha256(content.encode()).hexdigest()[:12]

        # Validate confidence range
        if not 0.0 <= self.confidence <= 1.0:
            self.confidence = max(0.0, min(1.0, self.confidence))

    def _generate_description(self) -> str:
        """Generate human-readable description from fields."""
        # If structured fields available, use them
        if self.intent and self.object:
            if self.context:
                return f"{self.intent} {self.object} ({self.context})"
            return f"{self.intent} {self.object}"

        # If only intent
        if self.intent:
            return self.intent

        # If only object
        if self.object:
            return f"interact with {self.object}"

        # Fallback
        return "unknown action"

    def get_description(self) -> str:
        """Safely get description (never None)."""
        return self.description or self._generate_description()

    @property
    def hints(self) -> Optional[GroundingHints]:
        """Backward-compatible alias for legacy code paths."""
        return self.grounding_hints

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "intent": self.intent,
            "object": self.object,
            "context": self.context,
            "description": self.get_description(),
            "confidence": self.confidence,
            "action_id": self.action_id
        }
        # Include grounding_hints if present
        if self.grounding_hints is not None:
            result["grounding_hints"] = self.grounding_hints.to_dict()
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ActionSemantic':
        """Create ActionSemantic from dictionary, filtering only valid constructor fields."""
        valid_fields = {'intent', 'object', 'context', 'description', 'confidence', 'action_id'}
        filtered_data = {k: v for k, v in data.items() if k in valid_fields}

        # Handle grounding_hints separately
        if 'grounding_hints' in data and data['grounding_hints'] is not None:
            if isinstance(data['grounding_hints'], dict):
                filtered_data['grounding_hints'] = GroundingHints.from_dict(data['grounding_hints'])
            elif isinstance(data['grounding_hints'], GroundingHints):
                filtered_data['grounding_hints'] = data['grounding_hints']

        return cls(**filtered_data)

    @classmethod
    def from_string(cls, description: str, confidence: float = 0.5) -> 'ActionSemantic':
        """Create ActionSemantic from free-text description."""
        return cls(
            description=description,
            intent=None,
            object=None,
            context=None,
            confidence=confidence
        )


@dataclass
class Action:
    """
    Unified action representation for STORAGE ONLY.

    CRITICAL: This bundles semantic + executable for persistence.
    During phase execution, these are accessed separately:
    - Phase 2/4: Agents read ONLY executable
    - Phase 3: LLM reads ONLY semantic
    - ActionGrounder maps between them via action_id

    NEVER pass this object directly to agents or LLM.
    Use appropriate projections instead.
    """
    action_id: str
    semantic: ActionSemantic
    executable: 'ActionExecutable'  # Reference to executable_schema
    source_screen_id: str  # Screen where action was discovered
    confidence: float = 1.0
    meta: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "action_id": self.action_id,
            "semantic": self.semantic.to_dict(),
            "executable": self.executable.to_dict(),
            "source_screen_id": self.source_screen_id,
            "confidence": self.confidence,
            "meta": self.meta
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Action':
        from exploration.executable_schema import ActionExecutable
        data = data.copy()
        data['semantic'] = ActionSemantic.from_dict(data['semantic'])
        data['executable'] = ActionExecutable.from_dict(data['executable'])
        return cls(**data)


@dataclass
class Transition:
    """
    State transition record.

    CRITICAL: Stores ONLY action_id reference, NOT the full action.
    To get action details, look up in ExplorationResult.actions[action_id].

    This enforces single source of truth for actions.
    """
    from_screen_id: str
    action_id: str  # Reference to Action (not embedded)
    to_screen_id: str
    transition_id: str = ""
    success: bool = True
    meta: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.transition_id:
            content = f"{self.from_screen_id}::{self.action_id}::{self.to_screen_id}"
            self.transition_id = hashlib.sha256(content.encode()).hexdigest()[:16]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "transition_id": self.transition_id,
            "from_screen_id": self.from_screen_id,
            "action_id": self.action_id,  # Only ID, not full action
            "to_screen_id": self.to_screen_id,
            "success": self.success,
            "meta": self.meta
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Transition':
        return cls(**data)


@dataclass
class ExplorationResult:
    """
    Complete exploration session results.

    ARCHITECTURE:
    - screens: Screen objects with semantic info
    - actions: Single source of truth for all actions (semantic + executable)
    - transitions: References to actions via action_id

    PHASE ACCESS:
    - Phase 2 (Exploration): actions[id].executable → agent
    - Phase 3 (Task Synthesis): actions[id].semantic → LLM
    - Phase 4 (Grounding): action_id mapping → executable
    """
    screens: Dict[str, Screen]  # screen_id -> Screen
    actions: Dict[str, Action]  # action_id -> Action (single source of truth)
    transitions: List[Transition]  # References actions via action_id
    explorer_name: str
    start_url: str
    timestamp: str
    meta: Dict[str, Any] = field(default_factory=dict)

    def add_screen(self, screen: Screen):
        """Add screen to collection"""
        self.screens[screen.screen_id] = screen

    def add_action(self, action: Action):
        """Add action to collection (single source of truth)"""
        self.actions[action.action_id] = action

    def add_transition(self, transition: Transition):
        """Add transition to collection"""
        self.transitions.append(transition)

    def get_unique_screen_count(self) -> int:
        """Get number of unique screens discovered"""
        return len(self.screens)

    def get_action_count(self) -> int:
        """Get number of actions discovered"""
        return len(self.actions)

    def get_transition_count(self) -> int:
        """Get number of transitions discovered"""
        return len(self.transitions)

    def get_actions_for_screen(self, screen_id: str) -> List[Action]:
        """Get all actions available from a screen"""
        return [
            action for action in self.actions.values()
            if action.source_screen_id == screen_id
        ]

    def validate_separation(self) -> bool:
        """Validate semantic/executable separation is maintained"""
        # Check no semantic contains selectors
        for action in self.actions.values():
            sem_dict = action.semantic.to_dict()
            if any(key in sem_dict for key in ['selector', 'element_type', 'coordinates']):
                return False
        return True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "screens": {sid: s.to_dict() for sid, s in self.screens.items()},
            "actions": {aid: a.to_dict() for aid, a in self.actions.items()},
            "transitions": [t.to_dict() for t in self.transitions],
            "explorer_name": self.explorer_name,
            "start_url": self.start_url,
            "timestamp": self.timestamp,
            "meta": self.meta
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ExplorationResult':
        data = data.copy()
        data['screens'] = {sid: Screen.from_dict(s) for sid, s in data['screens'].items()}
        data['actions'] = {aid: Action.from_dict(a) for aid, a in data['actions'].items()}
        data['transitions'] = [Transition.from_dict(t) for t in data['transitions']]
        # Ensure actions dict exists for backward compatibility
        if 'actions' not in data:
            data['actions'] = {}
        return cls(**data)
