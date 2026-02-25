"""
SemanticProjector: Strips executable information for LLM consumption.

PHASE USAGE: Phase 3 (Task Synthesis)

PURPOSE:
- Convert full exploration results (semantic + executable) into pure semantic graph
- Remove ALL selectors, DOM info, coordinates, and executable fields
- Prepare data for LLM-based task synthesis

CRITICAL:
- LLM MUST NOT see any executable details (selectors, DOM, coordinates)
- Output is ONLY for semantic reasoning about user goals and task structure
- Original exploration results are NEVER modified (read-only projection)

VALIDATION:
- Uses exploration.validation utilities for strict enforcement
- Raises exceptions if executable data leaks
"""

from typing import Dict, List, Any
from dataclasses import dataclass, field
import logging

from exploration.action_schema import (
    ExplorationResult,
    ScreenWithActions,
    Transition,
    Action
)
from exploration.validation import validate_semantic_only, FORBIDDEN_EXECUTABLE_FIELDS
from exploration.semantic_normalization import normalize_semantic, safe_get_description

logger = logging.getLogger(__name__)


@dataclass
class SemanticScreen:
    """
    Pure semantic screen representation for LLM consumption.
    
    Contains ONLY:
    - Screen identification
    - Semantic summary
    - Available action intents (NO selectors)
    """
    screen_id: str
    url: str  # Keep URL for context (no DOM paths)
    screen_type: str
    semantic_summary: str
    
    # Actions with ONLY semantic fields
    available_actions: List[Dict[str, Any]]  # List of {action_id, intent, description, category}
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "screen_id": self.screen_id,
            "url": self.url,
            "screen_type": self.screen_type,
            "semantic_summary": self.semantic_summary,
            "available_actions": self.available_actions
        }


@dataclass
class SemanticTransition:
    """
    Pure semantic transition for LLM consumption.
    
    Contains ONLY:
    - Screen IDs
    - Action intent and description (NO selector)
    """
    transition_id: str
    from_screen_id: str
    to_screen_id: str
    action_id: str
    action_intent: str
    action_description: str
    action_category: str
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "transition_id": self.transition_id,
            "from_screen_id": self.from_screen_id,
            "to_screen_id": self.to_screen_id,
            "action_id": self.action_id,
            "action_intent": self.action_intent,
            "action_description": self.action_description,
            "action_category": self.action_category
        }


@dataclass
class SemanticGraph:
    """
    Pure semantic exploration graph for task synthesis.
    
    This is the ONLY representation that LLMs see in Phase 3.
    Contains NO executable information whatsoever.
    """
    screens: Dict[str, SemanticScreen]
    transitions: List[SemanticTransition]
    
    start_url: str
    timestamp: str
    meta: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "screens": {sid: s.to_dict() for sid, s in self.screens.items()},
            "transitions": [t.to_dict() for t in self.transitions],
            "start_url": self.start_url,
            "timestamp": self.timestamp,
            "meta": self.meta
        }
    
    def get_screen_count(self) -> int:
        return len(self.screens)
    
    def get_transition_count(self) -> int:
        return len(self.transitions)


class SemanticProjector:
    """
    Projects full exploration results into pure semantic representation.
    
    USAGE:
        projector = SemanticProjector()
        semantic_graph = projector.project(exploration_result)
        # semantic_graph contains NO executable info
        # Safe to send to LLM for task synthesis
    
    GUARANTEES:
    - Output contains NO selectors
    - Output contains NO DOM information
    - Output contains NO coordinates or element details
    - Output is ONLY semantic intents and descriptions
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def project(self, exploration_result: ExplorationResult) -> SemanticGraph:
        """
        Project exploration result to pure semantic graph.
        
        CRITICAL ENFORCEMENT:
        - Strips ALL executable information
        - Validates output to ensure no leaks
        - Raises exception if validation fails
        
        Args:
            exploration_result: Full exploration result (semantic + executable)
            
        Returns:
            SemanticGraph with ONLY semantic information
            
        Raises:
            ValueError: If semantic projection contains executable leaks
        """
        self.logger.info("Projecting exploration result to semantic graph...")
        self.logger.info(f"Input: {len(exploration_result.screens)} screens, "
                        f"{len(exploration_result.transitions)} transitions")
        
        # Project screens
        semantic_screens = {}
        for screen_id, screen in exploration_result.screens.items():
            semantic_screens[screen_id] = self._project_screen(screen)
        
        # Project transitions
        semantic_transitions = [
            self._project_transition(t) 
            for t in exploration_result.transitions
        ]
        
        semantic_graph = SemanticGraph(
            screens=semantic_screens,
            transitions=semantic_transitions,
            start_url=exploration_result.start_url,
            timestamp=exploration_result.timestamp,
            meta={
                "projected_from": exploration_result.explorer_name,
                "original_screen_count": len(exploration_result.screens),
                "original_transition_count": len(exploration_result.transitions)
            }
        )
        
        self.logger.info(f"Projection complete: {semantic_graph.get_screen_count()} screens, "
                        f"{semantic_graph.get_transition_count()} transitions")
        
        # CRITICAL: Validate no executable information leaked
        if not self.validate_projection(semantic_graph):
            raise ValueError(
                "SEMANTIC PROJECTION FAILED: Executable data leaked into semantic graph. "
                "This violates the semantic-only control principle. Check logs for details."
            )
        
        self.logger.info("All executable information stripped. Safe for LLM consumption.")
        
        return semantic_graph
    
    def _project_screen(self, screen: ScreenWithActions) -> SemanticScreen:
        """
        Project screen to semantic-only representation.
        
        Strips:
        - DOM snapshot
        - Visible text details
        - Action executables (selectors, coordinates, etc.)
        
        Keeps:
        - Screen identification
        - Semantic summary
        - Action intents and descriptions
        """
        # Extract ONLY semantic fields from actions
        available_actions = []
        for action in screen.actions:
            # CRITICAL: Only include semantic fields, NO executable
            semantic_action = {
                "action_id": action.action_id,
                "intent": action.semantic.intent if hasattr(action.semantic, 'intent') else None,
                "description": safe_get_description(action.semantic),
                "category": action.semantic.category.value if hasattr(action.semantic, 'category') else "other"
            }
            
            # Optional semantic metadata (still no selectors!)
            if action.semantic.expected_outcome:
                semantic_action["expected_outcome"] = action.semantic.expected_outcome
            
            available_actions.append(semantic_action)
        
        return SemanticScreen(
            screen_id=screen.screen_id,
            url=screen.url,  # Keep URL for context (contains no DOM details)
            screen_type=screen.screen_type,
            semantic_summary=screen.semantic_summary,
            available_actions=available_actions
        )
    
    def _project_transition(self, transition: Transition) -> SemanticTransition:
        """
        Project transition to semantic-only representation.
        
        Strips:
        - Executable action details
        
        Keeps:
        - Screen connections
        - Action semantic information
        """
        return SemanticTransition(
            transition_id=transition.transition_id,
            from_screen_id=transition.from_screen_id,
            to_screen_id=transition.to_screen_id,
            action_id=transition.action_id,
            action_intent=transition.action_semantic.intent if hasattr(transition.action_semantic, 'intent') else None,
            action_description=safe_get_description(transition.action_semantic),
            action_category=transition.action_semantic.category.value if hasattr(transition.action_semantic, 'category') else "other"
        )
    
    def validate_projection(self, semantic_graph: SemanticGraph) -> bool:
        """
        Validate that projection contains NO executable information.
        
        STRICT ENFORCEMENT using validation utilities:
        - Checks for forbidden executable fields
        - Validates structure recursively
        - Fails HARD if violations found
        
        Returns:
            True if validation passes (no executable info found)
        """
        graph_dict = semantic_graph.to_dict()
        
        try:
            # Use centralized validation
            validate_semantic_only(
                graph_dict,
                context="SemanticGraph",
                raise_on_violation=True
            )
            self.logger.info("Validation PASSED: No executable information detected")
            return True
        
        except ValueError as e:
            self.logger.error(f"Validation FAILED: {e}")
            return False
