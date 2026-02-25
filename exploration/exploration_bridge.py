"""
Exploration bridge - main exploration logic and adapters.

Contains:
1. ExplorationLoop - Core BFS exploration algorithm
2. ExplorationAdapter - Interface for executing semantic actions
3. run_exploration() - Convenience function for running exploration

This is pure domain logic with no CLI/config concerns.
"""

from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from datetime import datetime
from collections import deque
import logging

from exploration.schema import Screen, ActionSemantic, Transition, ExplorationResult, ScreenType
from exploration.action_schema import (
    Action, ActionExecutable, ActionSemantic as ActionSemanticNew,
    ActionCategory, ScreenWithActions
)
from exploration.analyzer import ScreenAnalyzer, extract_visible_text
from exploration.dedup import ScreenDeduplicator
from exploration.storage import ExplorationStorage
from exploration.semantic_normalization import normalize_semantic, safe_get_description
from utils.env import env as env_config

logger = logging.getLogger(__name__)


# ============================================================================
# EXPLORATION LOOP - Core BFS Algorithm
# ============================================================================


class ExplorationLoop:
    """
    BFS-style exploration loop that discovers screens and transitions.
    
    DESIGN PRINCIPLES:
    - Exploration is NOT task solving
    - LLM is used ONLY for screen understanding and action listing
    - Explorer agents execute actions (AgentTrek, WebTactix)
    - Exploration is ONE-STEP ONLY (no multi-step planning, no backtracking)
    - Store ALL semantic transitions
    - System is explorer-agnostic via adapters
    """
    
    def __init__(
        self,
        env,
        explorer_adapter,
        analyzer: Optional[ScreenAnalyzer] = None,
        deduplicator: Optional[ScreenDeduplicator] = None,
        storage: Optional[ExplorationStorage] = None,
        max_screens: int = 50,
        max_transitions: int = 200,
        max_actions_per_screen: int = 10
    ):
        """
        Initialize exploration loop.
        
        Args:
            env: Web environment (implements WebEnv interface)
            explorer_adapter: Adapter for executing actions (AgentTrek, WebTactix, etc.)
            analyzer: Screen analyzer (creates one if None)
            deduplicator: Screen deduplicator (creates one if None)
            storage: Exploration storage (creates one if None)
            max_screens: Maximum unique screens to discover
            max_transitions: Maximum transitions to record
            max_actions_per_screen: Maximum actions to try per screen
        """
        self.env = env
        self.explorer_adapter = explorer_adapter
        self.analyzer = analyzer or ScreenAnalyzer()
        self.deduplicator = deduplicator or ScreenDeduplicator()
        
        # Use explorer_name as folder name (can be URL-based or explorer name)
        explorer_name = getattr(explorer_adapter, 'explorer_name', 'unknown')
        self.storage = storage or ExplorationStorage(explorer_name, auto_clean=False)
        
        self.max_screens = max_screens
        self.max_transitions = max_transitions
        self.max_actions_per_screen = max_actions_per_screen
        
        # Exploration state
        self.result = ExplorationResult(
            screens={},
            actions={},  # Single source of truth for actions
            transitions=[],
            explorer_name=explorer_name,
            start_url="",
            timestamp=datetime.now().isoformat()
        )
        
        # BFS queue: (screen_id, path_to_screen)
        # path_to_screen is List[(from_screen_id, action_semantic)]
        self.exploration_queue: deque = deque()
        self.explored_screens: set = set()
        
        # DOM cache: Prevents duplicate LLM calls for same content
        # Key: DOM hash, Value: (semantic_summary, screen_type, action_semantics)
        self.dom_cache: Dict[str, tuple] = {}
        logger.info("DOM caching enabled to prevent duplicate LLM calls")
    
    async def run_exploration(self, start_url: Optional[str] = None) -> ExplorationResult:
        """
        Run the exploration loop.
        
        Args:
            start_url: Starting URL (if None, uses env.reset())
            
        Returns:
            ExplorationResult with all discovered screens and transitions
        """
        logger.info("=" * 60)
        logger.info("Starting exploration")
        logger.info("=" * 60)
        
        # Initialize environment
        if start_url:
            # Navigate to start URL
            await self.env.reset()
            # TODO: Navigate to start_url
            self.result.start_url = start_url
        else:
            # Use env default
            obs = await self.env.reset()
            self.result.start_url = obs.get('url', 'unknown')
        
        # Capture root screen
        root_screen = await self._capture_screen()
        canonical_id, is_new = self.deduplicator.add_screen(root_screen, previous_screen=None)
        
        if is_new:
            self.result.add_screen(root_screen)
            self.storage.save_screen(root_screen)
        
        # Initialize exploration queue with root
        self.exploration_queue.append((canonical_id, []))
        
        logger.info(f"Root screen captured: {canonical_id}")
        logger.info(f"Starting BFS exploration...")
        
        # BFS exploration
        while self.exploration_queue and not self._should_stop():
            current_screen_id, path_to_screen = self.exploration_queue.popleft()
            
            # Skip if already explored
            if current_screen_id in self.explored_screens:
                continue
            
            logger.info(f"\n--- Exploring screen {current_screen_id} (depth: {len(path_to_screen)}) ---")
            
            # Mark as explored
            self.explored_screens.add(current_screen_id)
            
            # Get screen object
            current_screen = self.result.screens.get(current_screen_id)
            if not current_screen:
                logger.warning(f"Screen {current_screen_id} not found in results, skipping")
                continue
            
            # Explore from this screen
            await self._explore_from_screen(current_screen, path_to_screen)
        
        logger.info("\n" + "=" * 60)
        logger.info("Exploration complete")
        logger.info(f"Unique screens: {self.result.get_unique_screen_count()}")
        logger.info(f"Transitions: {self.result.get_transition_count()}")
        logger.info("=" * 60)
        
        # Save final results
        self.storage.save_exploration_result(self.result)
        
        return self.result
    
    async def _explore_from_screen(self, screen: Screen, path_to_screen: List):
        """
        Explore actions from a given screen.
        
        For each action semantic:
        1. Reset environment
        2. Replay path to this screen
        3. Execute ONE action
        4. Capture resulting screen
        5. Save transition
        
        Args:
            screen: Current screen to explore from
            path_to_screen: List of (from_screen_id, action_semantic) to reach this screen
        """
        logger.info(f"Screen type: {screen.screen_type.value}")
        logger.info(f"Summary: {screen.semantic_summary}")
        
        # Get action semantics for this screen
        action_ids = screen.meta.get('action_ids', [])
        
        if not action_ids:
            logger.info("No actions available from this screen")
            return
        
        # Retrieve actions from result.actions
        actions = [self.result.actions[aid] for aid in action_ids if aid in self.result.actions]
        
        logger.info(f"Found {len(actions)} possible actions")
        
        # Limit actions per screen
        actions = actions[:self.max_actions_per_screen]
        
        for i, action in enumerate(actions):
            if self._should_stop():
                logger.info("Stopping conditions met, ending exploration")
                break
            
            desc = safe_get_description(action.semantic)
            logger.info(f"  Action {i+1}/{len(actions)}: {desc}")
            
            # Execute one-step transition
            try:
                next_screen = await self._execute_transition(
                    screen,
                    action,
                    path_to_screen
                )
                
                if next_screen:
                    # Add screen to deduplicator (pass previous screen for validation detection)
                    canonical_id, is_new = self.deduplicator.add_screen(next_screen, previous_screen=screen)
                    
                    if is_new:
                        self.result.add_screen(next_screen)
                        self.storage.save_screen(next_screen)
                        logger.info(f"    → New screen discovered: {canonical_id}")
                    else:
                        logger.info(f"    → Existing screen: {canonical_id}")
                    
                    # Create and save transition (reference action_id only)
                    transition = Transition(
                        from_screen_id=screen.screen_id,
                        action_id=action.action_id,  # Only reference, not embed
                        to_screen_id=canonical_id,
                        success=True
                    )
                    self.result.add_transition(transition)
                    self.storage.save_transition(transition)
                    
                    # Add to exploration queue if new
                    if is_new and canonical_id not in self.explored_screens:
                        new_path = path_to_screen + [(screen.screen_id, action.action_id)]
                        self.exploration_queue.append((canonical_id, new_path))
                        logger.info(f"    → Added to exploration queue")
            
            except Exception as e:
                logger.error(f"    → Error executing action: {e}")
                # Record failed transition
                transition = Transition(
                    from_screen_id=screen.screen_id,
                    action_id=action.action_id,  # Only reference
                    to_screen_id=screen.screen_id,  # Stay on same screen
                    success=False,
                    meta={"error": str(e)}
                )
                self.result.add_transition(transition)
                self.storage.save_transition(transition)
    
    async def _execute_transition(
        self,
        from_screen: Screen,
        action: 'Action',  # Full action - agent receives ONLY semantic
        path_to_screen: List
    ) -> Optional[Screen]:
        """
        Execute a one-step transition.
        
        CRITICAL: Agent receives ONLY semantic intent.
        Executable details are logged AFTER execution as artifacts.
        
        1. Reset environment
        2. Replay path to from_screen
        3. Execute action (agent receives ONLY semantic)
        4. Capture resulting screen
        5. Log executable as artifact
        
        Args:
            from_screen: Starting screen
            action: Action object (agent uses ONLY .semantic)
            path_to_screen: Path to reach from_screen
            
        Returns:
            Resulting Screen or None if failed
        """
        # Reset environment
        await self.env.reset()
        
        # Replay path to from_screen
        if path_to_screen:
            logger.debug(f"    Replaying path of length {len(path_to_screen)}")
            for step_screen_id, step_action_id in path_to_screen:
                # Resolve action_id to semantic (CRITICAL FIX)
                if step_action_id not in self.result.actions:
                    logger.error(f"    Action {step_action_id} not found in results")
                    return None
                
                step_action = self.result.actions[step_action_id]
                # Execute step action using explorer (semantic only)
                try:
                    success = await self._execute_action_with_explorer(step_action.semantic)
                    if not success:
                        logger.error(f"    Failed to replay step: action returned False")
                        return None
                except Exception as e:
                    logger.error(f"    Failed to replay step: {e}")
                    return None
        
        # Verify we're at the expected screen
        # (optional check - could compare screen state)
        
        # Execute the target action (SEMANTIC ONLY)
        desc = safe_get_description(action.semantic)
        logger.debug(f"    Executing action: {desc}")
        success = await self._execute_action_with_explorer(action.semantic)
        
        # Only capture screen if action succeeded (CRITICAL FIX)
        if not success:
            logger.warning(f"    Action failed: {desc}")
            return None
        
        # Capture resulting screen
        next_screen = await self._capture_screen()
        
        return next_screen
    
    async def _execute_action_with_explorer(self, action_semantic: ActionSemantic) -> bool:
        """
        Execute an action using the explorer adapter.
        
        Args:
            action_semantic: High-level action to execute
            
        Returns:
            bool: True if action succeeded, False otherwise
        """
        # The explorer adapter handles converting semantic action
        # to actual browser actions
        return await self.explorer_adapter.execute_action(action_semantic, self.env)
    
    async def _capture_screen(self) -> Screen:
        """
        Capture current screen state.
        
        SEMANTIC-ONLY CONTROL: 
        - LLM extracts ONLY semantic information (intents, descriptions)
        - NO pre-grounding to executable actions
        - Actions stored with semantic only
        - Executables are filled in AFTER agent execution as artifacts
        
        OPTIMIZATION:
        - DOM hash caching prevents duplicate LLM calls
        - If DOM unchanged, reuse previous analysis
        
        Returns:
            Screen object with semantic-only actions
        """
        import hashlib
        
        # Get current observation from environment
        obs = await self.env.observe()
        
        url = obs.get('url', '')
        html = obs.get('html', '')
        
        # Calculate DOM hash for caching
        dom_hash = hashlib.md5(html.encode('utf-8')).hexdigest()
        
        # Extract visible text
        visible_text = extract_visible_text(html)
        
        # Check DOM cache (OPTIMIZATION: prevent duplicate LLM calls)
        if dom_hash in self.dom_cache:
            logger.info(f"[CACHE HIT] Reusing LLM analysis for DOM hash: {dom_hash[:8]}...")
            semantic_summary, screen_type, action_semantics = self.dom_cache[dom_hash]
        else:
            logger.info(f"[CACHE MISS] Calling LLM for new DOM hash: {dom_hash[:8]}...")
            # Use LLM to analyze screen (semantic only)
            semantic_summary, screen_type, action_semantics = self.analyzer.analyze_screen(
                url=url,
                dom_snapshot=html,
                visible_text=visible_text
            )
            # Cache the result
            self.dom_cache[dom_hash] = (semantic_summary, screen_type, action_semantics)
            logger.debug(f"Cached LLM result for DOM hash: {dom_hash[:8]}...")
        
        # Create actions with semantic ONLY (no executable yet)
        actions = self._create_semantic_only_actions(action_semantics)
        
        # Store actions in result.actions (single source of truth)
        action_ids = []
        for action in actions:
            action.source_screen_id = ""  # Will be set after screen_id generated
            self.result.add_action(action)
            self.storage.save_action(action)
            action_ids.append(action.action_id)
        
        # Create Screen object (NO action data in meta)
        screen = Screen(
            screen_id="",  # Will be generated
            url=url,
            dom_snapshot=html,
            visible_text=visible_text,
            semantic_summary=semantic_summary,
            screen_type=screen_type,
            timestamp=datetime.now().isoformat(),
            screenshot=obs.get('screenshot'),
            meta={
                'action_ids': action_ids  # Only references, not full actions
            }
        )
        
        # Update action source_screen_id after screen_id is generated
        for action_id in action_ids:
            if action_id in self.result.actions:
                self.result.actions[action_id].source_screen_id = screen.screen_id
        
        return screen
    
    def _create_semantic_only_actions(
        self,
        action_semantics: List[ActionSemantic]
    ) -> List['Action']:
        """
        Create Action objects with semantic ONLY.
        
        SEMANTIC-ONLY CONTROL:
        - NO pre-grounding to executable details
        - Executable fields are placeholders (empty)
        - Executables filled AFTER agent execution as artifacts
        
        Args:
            action_semantics: List of semantic action descriptions from LLM
            
        Returns:
            List of Action objects (semantic only, executable as placeholder)
        """
        from exploration.schema import Action
        from exploration.executable_schema import ActionExecutable, ActionType
        
        actions = []
        
        for action_sem in action_semantics:
            # Create placeholder executable (will be filled after execution)
            executable = ActionExecutable(
                action_id=action_sem.action_id,  # Link via same ID
                type=ActionType.CLICK,  # Placeholder
                selector="",  # Empty - filled after execution
                confidence=0.0  # 0 indicates not yet executed
            )
            
            # Create Action with semantic only (executable is placeholder)
            action = Action(
                action_id=action_sem.action_id,
                semantic=action_sem,
                executable=executable,
                source_screen_id="",  # Set later
                confidence=action_sem.confidence,
                meta={'executable_status': 'pending'}  # Mark as not yet executed
            )
            actions.append(action)
        
        return actions
    
    def _infer_category(self, description: str) -> ActionCategory:
        """Infer action category from description."""
        desc_lower = description.lower()
        
        if any(w in desc_lower for w in ['navigate', 'go to', 'visit', 'back', 'forward']):
            return ActionCategory.NAVIGATION
        elif any(w in desc_lower for w in ['search', 'find']):
            return ActionCategory.SEARCH
        elif any(w in desc_lower for w in ['type', 'enter', 'input', 'fill']):
            return ActionCategory.FORM_INPUT
        elif any(w in desc_lower for w in ['select', 'choose', 'pick']):
            return ActionCategory.SELECTION
        elif any(w in desc_lower for w in ['submit', 'checkout', 'purchase', 'buy']):
            return ActionCategory.SUBMISSION
        elif any(w in desc_lower for w in ['filter', 'sort']):
            return ActionCategory.FILTER
        elif any(w in desc_lower for w in ['view', 'see', 'look']):
            return ActionCategory.VIEW
        else:
            return ActionCategory.OTHER
    
    def _extract_intent(self, description: str) -> str:
        """Extract intent keyword from description."""
        import re
        # Remove common words and get key action
        words = re.findall(r'\b\w+\b', description.lower())
        # Filter out stop words
        stop_words = {'to', 'the', 'a', 'an', 'and', 'or', 'for', 'on', 'in', 'at'}
        key_words = [w for w in words if w not in stop_words and len(w) > 2]
        
        # Return first 2-3 key words as intent
        if key_words:
            return '_'.join(key_words[:2])
        return 'action'
    
    async def _log_executable_artifact(
        self,
        action_id: str,
        executed_selector: Optional[str],
        executed_type: str,
        success: bool
    ):
        """
        Log executable details AFTER action execution as artifacts.
        
        WRITE-ONLY ARTIFACT:
        - Executables are logged AFTER agent execution
        - These are historical records, not used for future decisions
        - Agent decisions are based ONLY on semantic data
        
        Args:
            action_id: Action identifier
            executed_selector: Actual selector used (if available)
            executed_type: Actual action type executed
            success: Whether execution succeeded
        """
        from exploration.executable_schema import ActionExecutable, ActionType
        
        # Update action's executable with actual execution details
        if action_id in self.result.actions:
            action = self.result.actions[action_id]
            
            # Create executable artifact from actual execution
            try:
                action_type = ActionType(executed_type) if executed_type else ActionType.CLICK
            except ValueError:
                action_type = ActionType.CLICK
            
            action.executable = ActionExecutable(
                action_id=action_id,
                type=action_type,
                selector=executed_selector or "unknown",
                confidence=1.0 if success else 0.0
            )
            action.meta['executable_status'] = 'executed'
            action.meta['execution_success'] = success
            
            # NOTE: Do NOT save here to avoid duplicates
            # Actions are already saved incrementally during screen capture
            # This function only updates in-memory state for future use
            # self.storage.save_action(action)  # DISABLED: Causes duplicates
            
            logger.debug(f"Logged executable artifact for action {action_id}: "
                        f"{executed_type} on {executed_selector} (success={success})")
    
    def _should_stop(self) -> bool:
        """
        Check if exploration should stop based on budget limits.
        
        Note: Queue emptiness is checked in the main BFS loop condition,
        not here, to allow completing action exploration from current screen.
        
        Returns:
            True if stopping conditions met
        """
        # Check screen limit
        if self.result.get_unique_screen_count() >= self.max_screens:
            logger.info(f"Reached max screens: {self.max_screens}")
            return True
        
        # Check transition limit
        if self.result.get_transition_count() >= self.max_transitions:
            logger.info(f"Reached max transitions: {self.max_transitions}")
            return True
        
        return False


async def run_exploration(
    env,
    explorer_adapter,
    start_url: Optional[str] = None,
    max_screens: int = 50,
    max_transitions: int = 200,
    max_actions_per_screen: int = 10,
    analyzer: Optional[ScreenAnalyzer] = None,
    deduplicator: Optional[ScreenDeduplicator] = None,
    storage: Optional[ExplorationStorage] = None
) -> ExplorationResult:
    """
    Convenience function to run exploration.
    
    This is the main entry point for exploration domain logic.
    
    Args:
        env: Web environment
        explorer_adapter: Explorer adapter for executing actions
        start_url: Starting URL (optional)
        max_screens: Maximum unique screens to discover
        max_transitions: Maximum transitions to record
        max_actions_per_screen: Maximum actions to try per screen
        analyzer: Custom screen analyzer (optional)
        deduplicator: Custom deduplicator (optional)
        storage: Custom storage (optional)
        
    Returns:
        ExplorationResult with all discovered screens and transitions
    """
    loop = ExplorationLoop(
        env=env,
        explorer_adapter=explorer_adapter,
        analyzer=analyzer,
        deduplicator=deduplicator,
        storage=storage,
        max_screens=max_screens,
        max_transitions=max_transitions,
        max_actions_per_screen=max_actions_per_screen
    )
    
    result = await loop.run_exploration(start_url)
    return result


# ============================================================================
# EXPLORATION ADAPTERS - Action Execution Interface
# ============================================================================


class ExplorationAdapter(ABC):
    """
    Base class for exploration-time adapters.
    
    Adapters convert high-level ActionSemantics into
    actual browser actions that the explorer can execute.
    """
    
    def __init__(self, explorer_name: str):
        """
        Initialize adapter.
        
        Args:
            explorer_name: Name of the explorer (e.g., "agenttrek", "webtactix")
        """
        self.explorer_name = explorer_name
    
    @abstractmethod
    async def execute_action(self, action_semantic: ActionSemantic, env) -> bool:
        """
        Execute a semantic action in the environment.
        
        The adapter is responsible for:
        1. Understanding the high-level action intent
        2. Using optional hints as SOFT GUIDANCE (not hard constraints)
        3. Converting intent to concrete browser actions
        4. Executing those actions via the environment
        
        HINTS USAGE (if action_semantic.hints is not None):
        - Hints are NON-BINDING attention biases
        - Use to prioritize/score elements, not as hard filters
        - Executor policy remains responsible for final decisions
        - Example: Boost score for elements matching hint keywords
        
        Args:
            action_semantic: High-level action description with optional hints
            env: Web environment to execute in
            
        Returns:
            True if action executed successfully, False otherwise
        """
        pass
    
    async def reset(self):
        """
        Reset adapter state (if needed).
        
        Called before each new exploration path.
        """
        pass


class SimpleExplorationAdapter(ExplorationAdapter):
    """
    Simple exploration adapter that uses heuristics
    to execute semantic actions.
    
    This is a fallback when no specific explorer is available.
    Uses basic pattern matching and element discovery.
    """
    
    def __init__(self):
        super().__init__("simple")
    
    async def execute_action(self, action_semantic: ActionSemantic, env) -> bool:
        """
        Execute action using simple heuristics with optional hint-based guidance.
        
        Attempts to:
        1. Parse the semantic description
        2. Use hints (if available) to guide element selection
        3. Find relevant elements via text/type matching
        4. Execute appropriate action
        
        Uses INTENT-LEVEL MAPPING (not just verb matching):
        - "search X" → TYPE action (search input)
        - "view/see X" → CLICK action (view details)
        - "sign in/login" → CLICK action (auth button)
        - "add to cart/checkout" → CLICK action (purchase flow)
        
        HINT USAGE (if action_semantic.hints is not None):
        - Keywords: Prioritize elements containing these words
        - Exclude keywords: Avoid elements containing these words
        - Element role: Prefer elements with matching role
        - Interaction type: Use hint to determine action type
        
        Args:
            action_semantic: High-level action with optional hints
            env: Environment
            
        Returns:
            True if successful
        """
        description = safe_get_description(action_semantic).lower()
        hints = action_semantic.hints
        
        logger.debug(f"Executing semantic action: {description}")
        if hints and not hints.is_empty():
            logger.debug(f"Using hints: keywords={hints.keywords}, exclude={hints.exclude_keywords}, "
                        f"role={hints.element_role}, interaction={hints.interaction_type}")
        
        # Import here to avoid circular dependency
        from schema import Action, ActionType
        
        try:
            # Determine action type (hints can override intent-level mapping)
            interaction_type = hints.interaction_type if hints else None
            
            if interaction_type == "type" or (not interaction_type and 
                any(word in description for word in ["search", "find", "query", "lookup", "type", "enter", "input", "fill"])):
                # TYPE action
                action = await self._find_and_create_type_action(description, env, hints)
            
            elif interaction_type == "navigate" or (not interaction_type and 
                any(word in description for word in ["navigate", "go to", "visit", "back", "forward"])):
                # NAVIGATION action
                action = await self._find_and_create_navigate_action(description, env, hints)
            
            elif interaction_type == "select" or (not interaction_type and
                any(word in description for word in ["select dropdown", "choose option"])):
                # SELECT action
                action = await self._find_and_create_select_action(description, env, hints)
            
            elif interaction_type == "click" or (not interaction_type and
                any(word in description for word in ["view", "see", "show", "details", "more", "sign in", 
                     "login", "register", "sign up", "add to cart", "checkout", "purchase", "buy", "cart",
                     "select", "choose", "pick", "click", "press", "tap", "button"])):
                # CLICK action (most common)
                action = await self._find_and_create_click_action(description, env, hints)
            
            elif "scroll" in description:
                # SCROLL action
                action = Action(type=ActionType.SCROLL, target="body", value="down")
            
            # FALLBACK: Try CLICK on any interactive element
            else:
                logger.info(f"No explicit verb match, attempting generic click: {description}")
                action = await self._find_and_create_click_action(description, env, hints)
            
            if action:
                # Execute action via environment
                _, done = await env.step(action)
                return True
            else:
                logger.warning(f"Could not create action for semantic: {description}")
                return False
        
        except Exception as e:
            logger.error(f"Error executing action: {e}")
            return False
    
    async def _find_and_create_click_action(self, description: str, env, hints=None):
        """
        Find clickable element matching description, using hints as guidance.
        
        Args:
            description: Action description
            env: Environment
            hints: Optional ActionHints for prioritization
            
        Returns:
            Action or None
        """
        from schema import Action, ActionType
        
        # Get current observation
        obs = await env.observe()
        
        # Try to find element by text content
        interactive_elements = obs.get('interactive_elements', [])
        
        if interactive_elements:
            # Score elements based on description and hints
            best_element = None
            best_score = 0.0
            
            for elem in interactive_elements:
                elem_text = elem.get('text', '').lower()
                score = 0.0
                
                # Base: keyword matching from description
                keywords = [
                    word for word in description.split()
                    if len(word) > 3 and word not in ['click', 'select', 'choose', 'press', 'button', 'link']
                ]
                if any(keyword in elem_text for keyword in keywords):
                    score += 1.0
                
                # HINT-BASED MODIFIERS (soft guidance)
                if hints:
                    # Boost elements matching hint keywords
                    if hints.keywords:
                        for kw in hints.keywords:
                            if kw.lower() in elem_text:
                                score += 0.5
                                logger.debug(f"Hint keyword match: '{kw}' in '{elem_text[:50]}'")
                    
                    # Penalize elements matching exclude keywords
                    if hints.exclude_keywords:
                        for ex_kw in hints.exclude_keywords:
                            if ex_kw.lower() in elem_text:
                                score -= 1.0
                                logger.debug(f"Hint exclusion match: '{ex_kw}' in '{elem_text[:50]}'")
                    
                    # Prefer elements with matching role
                    if hints.element_role:
                        elem_role = elem.get('role', elem.get('tag', '')).lower()
                        if hints.element_role.lower() in elem_role:
                            score += 0.3
                
                if score > best_score:
                    best_score = score
                    best_element = elem
            
            # Use best scoring element
            if best_element and best_score > 0:
                selector = best_element.get('selector', best_element.get('tag', 'button'))
                logger.debug(f"Selected element with score {best_score:.2f}: {selector}")
                return Action(type=ActionType.CLICK, target=selector)
            
            # Fallback: click first interactive element
            if interactive_elements:
                selector = interactive_elements[0].get('selector', 'button')
                return Action(type=ActionType.CLICK, target=selector)
        
        # Fallback: generic selector
        return Action(type=ActionType.CLICK, target="button, a, input[type='submit']")
    
    async def _find_and_create_type_action(self, description: str, env, hints=None):
        """
        Find input element and create type action, using hints as guidance.
        
        Args:
            description: Action description
            env: Environment
            hints: Optional ActionHints for prioritization
            
        Returns:
            Action or None
        """
        from schema import Action, ActionType
        
        # Extract what to type (very basic)
        value = ""
        if "search" in description:
            value = "search query"
        elif "email" in description:
            value = "test@example.com"
        elif "password" in description:
            value = "password123"
        else:
            value = "test input"
        
        # Use hints to refine selector if available
        target = "input, textarea"
        if hints and hints.element_role:
            if "input" in hints.element_role.lower():
                target = "input[type='text'], input[type='search'], textarea"
        
        return Action(type=ActionType.TYPE, target=target, value=value)
    
    async def _find_and_create_navigate_action(self, description: str, env, hints=None):
        """
        Create navigate action (hints not used for navigation).
        
        Args:
            description: Action description
            env: Environment
            hints: Optional ActionHints (not used)
            
        Returns:
            Action or None
        """
        from schema import Action, ActionType
        
        # In real implementation, would extract URL from description
        # For now, return None as we can't determine target URL
        logger.warning("Navigate action semantic requires URL, cannot execute")
        return None
    
    async def _find_and_create_select_action(self, description: str, env, hints=None):
        """
        Create select action for dropdown elements.
        
        Args:
            description: Action description
            env: Environment
            hints: Optional ActionHints for prioritization
            
        Returns:
            Action or None
        """
        from schema import Action, ActionType
        
        # Find select element
        target = "select"
        value = ""  # Would parse from description in real implementation
        
        return Action(type=ActionType.SELECT, target=target, value=value)


# Registry of available exploration adapters
_exploration_adapters = {
    "simple": SimpleExplorationAdapter,
}


def get_exploration_adapter(name: str = None) -> ExplorationAdapter:
    """
    Get an exploration adapter by name or from .env config.
    
    Args:
        name: Adapter name (if None, loads from EXPLORER_PROVIDER env var)
        
    Returns:
        Adapter instance
        
    Raises:
        ValueError: If adapter not found
    """
    if name is None:
        name = env_config.get("EXPLORER_PROVIDER", "simple")
    
    name = name.lower()
    
    # Special handling for AgentTrek (needs factory with config)
    if name == "agenttrek":
        try:
            from adapters.agenttrek_exploration_adapter import create_agenttrek_adapter
            logger.info("Creating AgentTrek exploration adapter from .env config")
            return create_agenttrek_adapter()
        except ImportError as e:
            logger.error(f"Failed to import AgentTrek adapter: {e}")
            logger.warning("Falling back to simple adapter")
            name = "simple"
    
    adapter_class = _exploration_adapters.get(name)
    if not adapter_class:
        available = ", ".join(_exploration_adapters.keys()) + ", agenttrek"
        raise ValueError(
            f"Unknown exploration adapter: {name}. "
            f"Available adapters: {available}"
        )
    
    return adapter_class()


def register_exploration_adapter(name: str, adapter_class: type):
    """
    Register a new exploration adapter.
    
    Args:
        name: Adapter name
        adapter_class: Adapter class
    """
    _exploration_adapters[name] = adapter_class


def list_exploration_adapters() -> List[str]:
    """
    List all available exploration adapter names.
    
    Returns:
        List of adapter names
    """
    adapters = list(_exploration_adapters.keys())
    adapters.append("agenttrek")  # Add special case
    return sorted(adapters)
