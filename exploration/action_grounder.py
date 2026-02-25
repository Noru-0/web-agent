"""
ActionGrounder: Maps semantic action intents to executable actions.

PHASE USAGE: Phase 4 (Task Execution)

PURPOSE:
- Given a task step intent (e.g., "checkout")
- And current screen's available actions
- Find and return the executable action (type + selector)

CRITICAL:
- Phase 3 (task synthesis) produces high-level task steps with intents
- Phase 4 (task execution) needs concrete executables to run
- ActionGrounder bridges the semantic → executable gap

DESIGN:
- Matches by semantic.intent (primary)
- Falls back to description matching (secondary)
- Fails softly if no match found (returns None, logs warning)
"""

from typing import Optional, List, Dict, Any
import logging
from difflib import SequenceMatcher

from exploration.action_schema import (
    Action,
    ActionExecutable,
    ActionSemantic,
    ScreenWithActions,
)
from exploration.semantic_normalization import safe_get_description
from exploration.schema import (
    ExplorationResult
)

logger = logging.getLogger(__name__)


class ActionGrounder:
    """
    Grounds semantic action intents to executable actions.
    
    USAGE:
        grounder = ActionGrounder(exploration_result)
        
        # During task execution
        executable = grounder.ground(
            intent="checkout",
            current_screen_id="screen_123"
        )
        
        if executable:
            # Execute the action
            env.step(executable)
    
    MATCHING STRATEGY:
    1. Exact intent match (primary)
    2. Fuzzy description match (fallback)
    3. Category + keyword match (last resort)
    """
    
    def __init__(self, exploration_result: Optional[ExplorationResult] = None):
        """
        Initialize action grounder.
        
        Args:
            exploration_result: Full exploration result with actions
                               If None, must call set_exploration_result() later
        """
        self.exploration_result = exploration_result
        self.logger = logging.getLogger(__name__)
        
        # Build intent → action lookup index for fast matching
        self._intent_index: Dict[str, List[Action]] = {}
        if exploration_result:
            self._build_intent_index()
    
    def set_exploration_result(self, exploration_result: ExplorationResult):
        """
        Set exploration result and rebuild index.
        
        Use this if exploration_result not provided at initialization.
        """
        self.exploration_result = exploration_result
        self._build_intent_index()
    
    def _build_intent_index(self):
        """
        Build intent → actions lookup index.
        
        This speeds up grounding by pre-indexing all actions by intent.
        """
        self._intent_index = {}
        
        if not self.exploration_result:
            return
        
        for screen in self.exploration_result.screens.values():
            for action in screen.actions:
                intent = action.semantic.intent.lower()
                if intent not in self._intent_index:
                    self._intent_index[intent] = []
                self._intent_index[intent].append(action)
        
        self.logger.info(f"Built intent index: {len(self._intent_index)} unique intents")
    
    def ground(
        self,
        intent: str,
        current_screen_id: str,
        description: Optional[str] = None,
        category: Optional[str] = None
    ) -> Optional[ActionExecutable]:
        """
        Ground semantic intent to executable action.
        
        SEMANTIC-ONLY CONTROL:
        - Matches using ONLY semantic fields (intent, description, category)
        - NO executable data used for matching decisions
        - Returns executable ONLY for agent execution, not decision-making
        
        Args:
            intent: Action intent (e.g., "checkout", "add_to_cart")
            current_screen_id: Current screen ID
            description: Optional action description for fallback matching
            category: Optional action category for fallback matching
            
        Returns:
            ActionExecutable if match found, None otherwise
            
        Note:
            This is used in Phase 4 (Task Execution) to convert semantic
            task steps into executable actions for agent execution.
        """
        if not self.exploration_result:
            self.logger.error("No exploration result set. Cannot ground action.")
            return None
        
        # Get current screen's actions
        screen = self.exploration_result.screens.get(current_screen_id)
        if not screen:
            self.logger.error(f"Screen {current_screen_id} not found in exploration result")
            return None
        
        if not screen.actions:
            self.logger.warning(f"Screen {current_screen_id} has no actions")
            return None
        
        # Strategy 1: Exact intent match (semantic field only)
        matched_action = self._match_by_intent(intent, screen.actions)
        if matched_action:
            self.logger.info(f"Grounded intent '{intent}' via exact intent match")
            return matched_action.executable
        
        # Strategy 2: Fuzzy description match (semantic field only)
        if description:
            matched_action = self._match_by_description(description, screen.actions)
            if matched_action:
                self.logger.info(f"Grounded intent '{intent}' via description match")
                return matched_action.executable
        
        # Strategy 3: Category + keyword match (last resort)
        if category:
            matched_action = self._match_by_category_and_keywords(
                intent, category, screen.actions
            )
            if matched_action:
                self.logger.info(f"Grounded intent '{intent}' via category match")
                return matched_action.executable
        
        # No match found
        self.logger.warning(
            f"Could not ground intent '{intent}' on screen {current_screen_id}. "
            f"Available actions: {[a.semantic.intent for a in screen.actions]}"
        )
        return None
    
    def ground_by_action_id(
        self,
        action_id: str
    ) -> Optional[ActionExecutable]:
        """
        Ground action by exact action_id.
        
        This is the most reliable method when action_id is known.
        
        Args:
            action_id: Exact action ID from exploration
            
        Returns:
            ActionExecutable if found, None otherwise
        """
        if not self.exploration_result:
            self.logger.error("No exploration result set. Cannot ground action.")
            return None
        
        action = self.exploration_result.get_action_by_id(action_id)
        if action:
            self.logger.info(f"Grounded action {action_id} via exact ID match")
            return action.executable
        
        self.logger.warning(f"Action ID {action_id} not found in exploration result")
        return None
    
    def get_available_intents(self, screen_id: str) -> List[str]:
        """
        Get list of available action intents for a screen.
        
        Useful for debugging and runtime introspection.
        
        Args:
            screen_id: Screen ID
            
        Returns:
            List of available intent strings
        """
        if not self.exploration_result:
            return []
        
        screen = self.exploration_result.screens.get(screen_id)
        if not screen:
            return []
        
        return [action.semantic.intent for action in screen.actions]
    
    def _match_by_intent(
        self,
        intent: str,
        actions: List[Action]
    ) -> Optional[Action]:
        """
        Match action by exact intent.
        
        Primary matching strategy.
        """
        intent_lower = intent.lower().strip()
        
        for action in actions:
            if action.semantic.intent.lower().strip() == intent_lower:
                return action
        
        return None
    
    def _match_by_description(
        self,
        description: str,
        actions: List[Action],
        threshold: float = 0.6
    ) -> Optional[Action]:
        """
        Match action by fuzzy description matching.
        
        Fallback strategy when exact intent doesn't match.
        """
        description_lower = description.lower().strip()
        
        best_match = None
        best_score = 0.0
        
        for action in actions:
            action_desc = safe_get_description(action.semantic).lower().strip()
            score = SequenceMatcher(None, description_lower, action_desc).ratio()
            
            if score > best_score and score >= threshold:
                best_score = score
                best_match = action
        
        if best_match:
            self.logger.debug(f"Description match score: {best_score:.2f}")
        
        return best_match
    
    def _match_by_category_and_keywords(
        self,
        intent: str,
        category: str,
        actions: List[Action]
    ) -> Optional[Action]:
        """
        Match by category and keyword overlap.
        
        Last resort strategy.
        """
        intent_keywords = set(intent.lower().split('_'))
        category_lower = category.lower()
        
        candidates = [
            a for a in actions 
            if a.semantic.category.value.lower() == category_lower
        ]
        
        if not candidates:
            return None
        
        # Find candidate with most keyword overlap
        best_match = None
        best_overlap = 0
        
        for action in candidates:
            intent = getattr(action.semantic, 'intent', None) or ''
            action_keywords = set(intent.lower().split('_'))
            action_keywords.update(safe_get_description(action.semantic).lower().split())
            
            overlap = len(intent_keywords & action_keywords)
            if overlap > best_overlap:
                best_overlap = overlap
                best_match = action
        
        return best_match if best_overlap > 0 else None
    
    def ground_batch(
        self,
        intent_list: List[Dict[str, Any]],
        current_screen_id: str
    ) -> List[Optional[ActionExecutable]]:
        """
        Ground multiple intents in batch.
        
        Args:
            intent_list: List of dicts with {intent, description?, category?}
            current_screen_id: Current screen ID
            
        Returns:
            List of ActionExecutables (None for failed matches)
        """
        results = []
        for item in intent_list:
            executable = self.ground(
                intent=item['intent'],
                current_screen_id=current_screen_id,
                description=item.get('description'),
                category=item.get('category')
            )
            results.append(executable)
        
        success_count = sum(1 for e in results if e is not None)
        self.logger.info(
            f"Batch grounding: {success_count}/{len(intent_list)} successful"
        )
        
        return results
