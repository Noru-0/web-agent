"""
Task Synthesis: Deterministic task inference from semantic actions.

PHASE USAGE: Phase 3 (Task Synthesis)

PURPOSE:
- Aggregate semantic actions across screens
- Infer high-level user tasks (workflows) deterministically
- Group related actions into multi-step user goals
- NO LLM calls - pure algorithmic approach

CRITICAL INPUT:
- Consumes semantic-only exploration data (NO executable info)
- NEVER include selectors, DOM, or coordinates

OUTPUT:
- TaskGraph: Structured representation of user tasks
- Each task is a multi-step workflow with confidence scores

VALIDATION:
- Uses exploration.validation utilities for strict enforcement
- Rejects graphs with executable data

CONTAINS:
1. TaskSynthesizer: Deterministic task aggregation and grouping
2. TaskSynthesisPromptBuilder: LLM prompt builder (legacy/alternative approach)
"""

from typing import List, Dict, Any, Optional, Set, Tuple
from dataclasses import dataclass, field
from collections import defaultdict
from enum import Enum
import logging
import hashlib

from exploration.semantic_projector import SemanticGraph, SemanticScreen
from exploration.validation import validate_semantic_only
from exploration.schema import Screen, ActionSemantic

logger = logging.getLogger(__name__)


class TaskPriority(str, Enum):
    """Task priority levels based on workflow position"""
    INITIAL = "initial"  # Entry point tasks (search, browse)
    INTERMEDIATE = "intermediate"  # Mid-flow tasks (view details, filter)
    TERMINAL = "terminal"  # Goal completion tasks (checkout, add to cart, sign in)


@dataclass
class Task:
    """
    Represents a high-level user task (workflow).
    
    A task is a multi-step user goal inferred from semantic actions.
    Examples: "search products", "view product details", "add to cart"
    """
    task_id: str
    name: str
    description: str
    related_actions: List[str]  # action_ids
    confidence: float  # 0.0-1.0
    entry_screens: List[str]  # screen_ids where task can start
    priority: TaskPriority
    meta: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "name": self.name,
            "description": self.description,
            "related_actions": self.related_actions,
            "confidence": self.confidence,
            "entry_screens": self.entry_screens,
            "priority": self.priority.value,
            "meta": self.meta
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Task':
        data = data.copy()
        data['priority'] = TaskPriority(data['priority'])
        return cls(**data)


@dataclass
class TaskGraph:
    """
    Collection of synthesized user tasks.
    
    Output of task synthesis phase.
    """
    tasks: List[Task]
    meta: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "tasks": [t.to_dict() for t in self.tasks],
            "meta": self.meta
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TaskGraph':
        data = data.copy()
        data['tasks'] = [Task.from_dict(t) for t in data['tasks']]
        return cls(**data)
    
    def get_tasks_by_priority(self, priority: TaskPriority) -> List[Task]:
        """Get all tasks with specified priority"""
        return [t for t in self.tasks if t.priority == priority]
    
    def get_task_by_id(self, task_id: str) -> Optional[Task]:
        """Get task by ID"""
        for task in self.tasks:
            if task.task_id == task_id:
                return task
        return None


class TaskSynthesizer:
    """
    Deterministic task synthesis from semantic actions.
    
    ALGORITHM:
    1. Collect all semantic actions across screens
    2. Normalize actions by (intent, object) to deduplicate
    3. Group related actions into higher-level tasks
    4. Compute task confidence from action confidences + screen frequency
    5. Prioritize tasks (initial, intermediate, terminal)
    6. Sort by priority and confidence
    
    NO LLM CALLS - pure deterministic logic.
    
    USAGE:
        # Generic (domain-agnostic)
        synthesizer = TaskSynthesizer()
        
        # Domain-specific
        synthesizer = TaskSynthesizer(domain="ecommerce")
        
        # Custom patterns
        synthesizer = TaskSynthesizer(custom_patterns=[...])
    """
    
    # Intent keywords that indicate different task priorities (domain-agnostic)
    INITIAL_INTENTS = {'search', 'browse', 'view', 'navigate', 'explore', 'discover', 'find', 'list'}
    TERMINAL_INTENTS = {
        'checkout', 'purchase', 'buy', 'add_to_cart', 'cart', 
        'sign_in', 'login', 'register', 'submit', 'complete',
        'download', 'save', 'subscribe', 'follow', 'join',
        'post', 'publish', 'send', 'share', 'upload'
    }
    
    # Domain-specific pattern libraries
    DOMAIN_PATTERNS = {
        'ecommerce': [
            (['search', 'filter'], "search products", "Search and filter products"),
            (['view', 'open', 'details'], "view product details", "Browse product details"),
            (['add', 'cart'], "add to cart", "Add items to shopping cart"),
            (['checkout', 'purchase', 'buy'], "checkout", "Complete purchase checkout"),
            (['view_cart', 'cart'], "view cart", "View shopping cart"),
        ],
        'news': [
            (['search', 'find'], "search content", "Search for articles or news"),
            (['read', 'view', 'open'], "read article", "Read article or content"),
            (['browse', 'explore'], "browse topics", "Browse news categories or topics"),
            (['subscribe', 'follow'], "subscribe", "Subscribe to newsletter or topics"),
            (['share', 'post'], "share content", "Share articles or content"),
        ],
        'social': [
            (['post', 'create', 'publish'], "create content", "Create and publish content"),
            (['view', 'open', 'read'], "view content", "View posts or content"),
            (['like', 'react'], "react to content", "Like or react to posts"),
            (['comment', 'reply'], "comment", "Comment on posts"),
            (['follow', 'subscribe'], "follow users", "Follow users or pages"),
            (['share', 'repost'], "share content", "Share or repost content"),
        ],
        'banking': [
            (['view', 'check'], "check balance", "Check account balance"),
            (['transfer', 'send'], "transfer money", "Transfer funds"),
            (['pay', 'payment'], "make payment", "Pay bills or make payments"),
            (['search', 'find'], "search transactions", "Search transaction history"),
        ],
        'streaming': [
            (['search', 'find'], "search content", "Search for movies or shows"),
            (['play', 'watch'], "watch content", "Play video or audio content"),
            (['add', 'save'], "add to watchlist", "Add to favorites or watchlist"),
            (['browse', 'explore'], "browse catalog", "Browse content catalog"),
        ],
        'generic': [
            # Fallback generic patterns
            (['search', 'find', 'filter'], "search", "Search and filter content"),
            (['view', 'open', 'read', 'details'], "view details", "View detailed information"),
            (['create', 'add', 'new'], "create item", "Create or add new item"),
            (['edit', 'update', 'modify'], "edit item", "Edit or update item"),
            (['delete', 'remove'], "delete item", "Delete or remove item"),
            (['navigate', 'browse'], "navigate", "Navigate through site"),
        ]
    }
    
    # Common authentication patterns (added to all domains)
    AUTH_PATTERNS = [
        (['sign_in', 'login', 'authenticate'], "sign in", "Sign in to account"),
        (['register', 'sign_up', 'create_account'], "create account", "Create new account"),
        (['logout', 'sign_out'], "sign out", "Sign out of account"),
    ]
    
    def __init__(self, domain: Optional[str] = None, custom_patterns: Optional[List] = None):
        """
        Initialize task synthesizer.
        
        Args:
            domain: Domain type for predefined patterns. Options:
                    'ecommerce', 'news', 'social', 'banking', 'streaming', 'generic'
                    If None, uses generic patterns + auto-detection
            custom_patterns: Custom task patterns to use instead of domain patterns.
                           Format: [(intent_keywords, task_name, description), ...]
        
        Examples:
            # Auto-detect domain
            TaskSynthesizer()
            
            # E-commerce site
            TaskSynthesizer(domain="ecommerce")
            
            # Custom patterns
            TaskSynthesizer(custom_patterns=[
                (['book', 'reserve'], "book appointment", "Book service appointment"),
                (['cancel'], "cancel booking", "Cancel reservation")
            ])
        """
        self.logger = logging.getLogger(__name__)
        
        # Select patterns
        if custom_patterns:
            self.task_patterns = custom_patterns
            self.logger.info(f"Using {len(custom_patterns)} custom task patterns")
        elif domain and domain in self.DOMAIN_PATTERNS:
            self.task_patterns = self.DOMAIN_PATTERNS[domain]
            self.logger.info(f"Using {len(self.task_patterns)} {domain} domain patterns")
        else:
            # Use generic patterns as fallback
            self.task_patterns = self.DOMAIN_PATTERNS['generic']
            self.logger.info("Using generic domain patterns (no specific domain selected)")
        
        # Always append common authentication patterns (unless using fully custom patterns)
        if not custom_patterns:
            self.task_patterns = self.task_patterns + self.AUTH_PATTERNS
        
        # Store domain for auto-detection flag
        self._domain_specified = domain is not None
        self._domain = domain
    
    def auto_detect_domain(self, screens: List[Screen]) -> str:
        """
        Auto-detect web domain type from screens and actions.
        
        Args:
            screens: List of Screen objects
            
        Returns:
            Detected domain name ('ecommerce', 'news', 'social', etc.)
        """
        # Count domain-specific keywords in screen types and action intents
        domain_scores = defaultdict(float)
        
        # E-commerce indicators
        ecommerce_keywords = ['product', 'cart', 'checkout', 'shop', 'purchase', 'buy', 'price', 'order']
        news_keywords = ['article', 'news', 'blog', 'post', 'read', 'author', 'publish']
        social_keywords = ['post', 'comment', 'like', 'follow', 'share', 'friend', 'profile']
        banking_keywords = ['account', 'balance', 'transfer', 'payment', 'transaction', 'bank']
        streaming_keywords = ['video', 'watch', 'play', 'episode', 'movie', 'series', 'stream']
        
        # Analyze screens
        for screen in screens:
            screen_text = (
                screen.semantic_summary.lower() + " " +
                screen.visible_text.lower() + " " +
                screen.url.lower()
            )
            
            # Score each domain
            domain_scores['ecommerce'] += sum(1 for kw in ecommerce_keywords if kw in screen_text)
            domain_scores['news'] += sum(1 for kw in news_keywords if kw in screen_text)
            domain_scores['social'] += sum(1 for kw in social_keywords if kw in screen_text)
            domain_scores['banking'] += sum(1 for kw in banking_keywords if kw in screen_text)
            domain_scores['streaming'] += sum(1 for kw in streaming_keywords if kw in screen_text)
            
            # Analyze actions
            screen_actions = getattr(screen, 'available_actions', []) or getattr(screen, 'actions', [])
            for action in screen_actions:
                intent = ""
                obj = ""
                
                if isinstance(action, dict):
                    intent = action.get('intent', '').lower()
                    obj = action.get('object', '').lower()
                elif hasattr(action, 'intent'):
                    intent = (action.intent or '').lower()
                    obj = (getattr(action, 'object', None) or '').lower()
                
                action_text = f"{intent} {obj}"
                domain_scores['ecommerce'] += sum(0.5 for kw in ecommerce_keywords if kw in action_text)
                domain_scores['news'] += sum(0.5 for kw in news_keywords if kw in action_text)
                domain_scores['social'] += sum(0.5 for kw in social_keywords if kw in action_text)
                domain_scores['banking'] += sum(0.5 for kw in banking_keywords if kw in action_text)
                domain_scores['streaming'] += sum(0.5 for kw in streaming_keywords if kw in action_text)
        
        # Find highest scoring domain
        if domain_scores:
            detected_domain = max(domain_scores.items(), key=lambda x: x[1])
            if detected_domain[1] > 0:
                self.logger.info(f"Auto-detected domain: {detected_domain[0]} (score: {detected_domain[1]:.1f})")
                return detected_domain[0]
        
        self.logger.info("Could not detect specific domain, using generic patterns")
        return 'generic'
    
    def synthesize(self, screens: List[Screen]) -> TaskGraph:
        """
        Synthesize high-level tasks from screens and their semantic actions.
        
        Args:
            screens: List of Screen objects with semantic actions
            
        Returns:
            TaskGraph with inferred user tasks
        """
        self.logger.info(f"Starting task synthesis for {len(screens)} screens")
        
        # Auto-detect domain if not specified
        if not self._domain_specified and len(screens) > 0:
            detected_domain = self.auto_detect_domain(screens)
            if detected_domain != 'generic' and detected_domain in self.DOMAIN_PATTERNS:
                self.logger.info(f"Switching to {detected_domain} patterns based on auto-detection")
                self.task_patterns = self.DOMAIN_PATTERNS[detected_domain] + self.AUTH_PATTERNS
        
        # Step 1: Collect all semantic actions
        all_actions = self._collect_actions(screens)
        self.logger.debug(f"Collected {len(all_actions)} total actions")
        
        # Step 2: Normalize and deduplicate actions
        normalized_actions = self._normalize_actions(all_actions)
        self.logger.debug(f"Normalized to {len(normalized_actions)} unique actions")
        
        # Step 3: Group actions into tasks
        tasks = self._group_into_tasks(normalized_actions, screens)
        self.logger.debug(f"Grouped into {len(tasks)} tasks")
        
        # Step 4: Compute task priorities
        tasks = self._prioritize_tasks(tasks)
        
        # Step 5: Sort by priority and confidence
        tasks = self._sort_tasks(tasks)
        
        self.logger.info(f"Task synthesis complete: {len(tasks)} tasks generated")
        
        return TaskGraph(
            tasks=tasks,
            meta={
                "total_screens": len(screens),
                "total_actions": len(all_actions),
                "unique_actions": len(normalized_actions)
            }
        )
    
    def _collect_actions(self, screens: List[Screen]) -> List[Tuple[ActionSemantic, str]]:
        """
        Collect all semantic actions from screens.
        
        Returns:
            List of (action, screen_id) tuples
        """
        actions = []
        for screen in screens:
            # Handle different screen structures
            screen_actions = getattr(screen, 'available_actions', [])
            if not screen_actions:
                screen_actions = getattr(screen, 'actions', [])
            
            for action in screen_actions:
                # Convert to ActionSemantic if needed
                if isinstance(action, dict):
                    action_sem = ActionSemantic.from_dict(action)
                elif hasattr(action, 'semantic'):
                    action_sem = action.semantic
                elif isinstance(action, ActionSemantic):
                    action_sem = action
                else:
                    # Try to extract semantic fields
                    action_sem = ActionSemantic(
                        intent=getattr(action, 'intent', None),
                        object=getattr(action, 'object', None),
                        context=getattr(action, 'context', None),
                        description=getattr(action, 'description', 'unknown action'),
                        confidence=getattr(action, 'confidence', 0.5)
                    )
                
                actions.append((action_sem, screen.screen_id))
        
        return actions
    
    def _normalize_actions(self, actions: List[Tuple[ActionSemantic, str]]) -> Dict[str, Dict[str, Any]]:
        """
        Normalize and deduplicate actions by (intent, object).
        
        Args:
            actions: List of (action, screen_id) tuples
            
        Returns:
            Dict mapping normalized_key -> {action, screen_ids, confidence}
        """
        normalized = {}
        
        for action, screen_id in actions:
            # Create normalization key from intent and object
            intent = (action.intent or "").lower().strip()
            obj = (action.object or "").lower().strip()
            
            # Generate key - use intent+object if available, else use description
            if intent or obj:
                key = f"{intent}::{obj}"
            else:
                # Use description as fallback
                desc = (action.description or "").lower().strip()
                key = f"desc::{desc[:50]}"  # Limit description length
            
            if key not in normalized:
                normalized[key] = {
                    'action': action,
                    'screen_ids': set(),
                    'confidences': []
                }
            
            normalized[key]['screen_ids'].add(screen_id)
            normalized[key]['confidences'].append(action.confidence)
        
        # Compute average confidence for each normalized action
        for key, data in normalized.items():
            data['avg_confidence'] = sum(data['confidences']) / len(data['confidences'])
            data['screen_count'] = len(data['screen_ids'])
        
        return normalized
    
    def _group_into_tasks(
        self,
        normalized_actions: Dict[str, Dict[str, Any]],
        screens: List[Screen]
    ) -> List[Task]:
        """
        Group related actions into higher-level tasks.
        
        Uses pattern matching to identify task categories.
        
        Args:
            normalized_actions: Normalized action dictionary
            screens: Original screens list
            
        Returns:
            List of Task objects
        """
        tasks = []
        used_actions = set()
        
        # Try to match each pattern
        for pattern_intents, task_name, task_desc in self.task_patterns:
            matching_actions = []
            
            for norm_key, action_data in normalized_actions.items():
                if norm_key in used_actions:
                    continue
                
                action = action_data['action']
                intent = (action.intent or "").lower()
                
                # Check if intent matches any pattern keyword
                if any(pattern in intent for pattern in pattern_intents):
                    matching_actions.append((norm_key, action_data))
                    used_actions.add(norm_key)
            
            # Create task if we found matching actions
            if matching_actions:
                task = self._create_task(
                    task_name,
                    task_desc,
                    matching_actions,
                    screens
                )
                tasks.append(task)
        
        # Handle remaining actions that didn't match patterns
        remaining_actions = [
            (key, data) for key, data in normalized_actions.items()
            if key not in used_actions
        ]
        
        if remaining_actions:
            # Group by intent prefix (first word)
            intent_groups = defaultdict(list)
            for norm_key, action_data in remaining_actions:
                action = action_data['action']
                intent = (action.intent or "").lower().split()[0] if action.intent else "other"
                intent_groups[intent].append((norm_key, action_data))
            
            # Create a task for each intent group
            for intent, actions in intent_groups.items():
                if len(actions) >= 1:  # Create task even for single actions
                    task_name = f"{intent} actions"
                    task_desc = f"Perform {intent}-related actions"
                    task = self._create_task(task_name, task_desc, actions, screens)
                    tasks.append(task)
        
        return tasks
    
    def _create_task(
        self,
        name: str,
        description: str,
        matching_actions: List[Tuple[str, Dict[str, Any]]],
        screens: List[Screen]
    ) -> Task:
        """
        Create a Task from grouped actions.
        
        Args:
            name: Task name
            description: Task description
            matching_actions: List of (norm_key, action_data) tuples
            screens: All screens
            
        Returns:
            Task object
        """
        # Extract action IDs and screen IDs
        action_ids = []
        all_screen_ids = set()
        confidences = []
        
        for norm_key, action_data in matching_actions:
            action = action_data['action']
            action_ids.append(action.action_id)
            all_screen_ids.update(action_data['screen_ids'])
            confidences.append(action_data['avg_confidence'])
        
        # Compute task confidence
        # Average action confidence boosted by screen frequency
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.5
        screen_boost = min(len(all_screen_ids) / 5.0, 0.2)  # Up to +0.2 for appearing on many screens
        task_confidence = min(avg_confidence + screen_boost, 1.0)
        
        # Generate deterministic task_id
        task_id = self._generate_task_id(name, action_ids)
        
        # Will be set by _prioritize_tasks
        priority = TaskPriority.INTERMEDIATE
        
        return Task(
            task_id=task_id,
            name=name,
            description=description,
            related_actions=action_ids,
            confidence=task_confidence,
            entry_screens=list(all_screen_ids),
            priority=priority,
            meta={
                "action_count": len(action_ids),
                "screen_count": len(all_screen_ids)
            }
        )
    
    def _generate_task_id(self, name: str, action_ids: List[str]) -> str:
        """
        Generate deterministic task ID.
        
        Args:
            name: Task name
            action_ids: Related action IDs
            
        Returns:
            Deterministic task ID string
        """
        # Sort action IDs for determinism
        sorted_actions = sorted(action_ids)
        content = f"{name}::{','.join(sorted_actions)}"
        hash_val = hashlib.sha256(content.encode()).hexdigest()[:12]
        return f"task_{hash_val}"
    
    def _prioritize_tasks(self, tasks: List[Task]) -> List[Task]:
        """
        Assign priority levels to tasks based on intent patterns.
        
        Args:
            tasks: List of tasks
            
        Returns:
            Tasks with priorities assigned
        """
        for task in tasks:
            task_name_lower = task.name.lower()
            
            # Check if task name contains initial intent keywords
            if any(intent in task_name_lower for intent in self.INITIAL_INTENTS):
                task.priority = TaskPriority.INITIAL
            # Check if task name contains terminal intent keywords
            elif any(intent in task_name_lower for intent in self.TERMINAL_INTENTS):
                task.priority = TaskPriority.TERMINAL
            else:
                task.priority = TaskPriority.INTERMEDIATE
        
        return tasks
    
    def _sort_tasks(self, tasks: List[Task]) -> List[Task]:
        """
        Sort tasks by priority and confidence.
        
        Initial tasks first, then intermediate, then terminal.
        Within each priority, sort by confidence (descending).
        
        Args:
            tasks: List of tasks
            
        Returns:
            Sorted list of tasks
        """
        priority_order = {
            TaskPriority.INITIAL: 0,
            TaskPriority.INTERMEDIATE: 1,
            TaskPriority.TERMINAL: 2
        }
        
        return sorted(
            tasks,
            key=lambda t: (priority_order[t.priority], -t.confidence)
        )


# ============================================================================
# Legacy LLM-based Task Synthesis (Alternative Approach)
# ============================================================================


class TaskSynthesisPromptBuilder:
    """
    Builds LLM prompts for task synthesis from semantic graphs.
    
    USAGE:
        builder = TaskSynthesisPromptBuilder()
        prompt = builder.build_prompt(semantic_graph)
        
        # Send to LLM
        tasks = llm.generate(prompt)
    
    DESIGN PRINCIPLES:
    - Prompts describe ONLY semantic information
    - Focus on user goals and intents
    - No technical details (selectors, DOM, etc.)
    - Tasks should be realistic user workflows
    """
    
    def __init__(
        self,
        max_screens_in_prompt: int = 20,
        max_actions_per_screen: int = 10
    ):
        """
        Initialize prompt builder.
        
        Args:
            max_screens_in_prompt: Limit screens to avoid token overflow
            max_actions_per_screen: Limit actions per screen in prompt
        """
        self.max_screens_in_prompt = max_screens_in_prompt
        self.max_actions_per_screen = max_actions_per_screen
        self.logger = logging.getLogger(__name__)
    
    def build_prompt(
        self,
        semantic_graph: SemanticGraph,
        style: str = "comprehensive"
    ) -> str:
        """
        Build task synthesis prompt from semantic graph.
        
        CRITICAL VALIDATION:
        - Asserts semantic_graph contains NO executable fields
        - Rejects graphs with selectors, DOM, or coordinates
        - Enforces semantic-only control for LLM
        
        Args:
            semantic_graph: Semantic-only exploration graph
            style: Prompt style - "comprehensive", "concise", "examples"
            
        Returns:
            Formatted prompt string for LLM
            
        Raises:
            ValueError: If semantic_graph contains executable data
        """
        self.logger.info(f"Building task synthesis prompt ({style} style)")
        self.logger.info(f"Input: {semantic_graph.get_screen_count()} screens, "
                        f"{semantic_graph.get_transition_count()} transitions")
        
        # CRITICAL: Validate semantic graph has NO executable data
        self._validate_semantic_only(semantic_graph)
        
        if style == "comprehensive":
            return self._build_comprehensive_prompt(semantic_graph)
        elif style == "concise":
            return self._build_concise_prompt(semantic_graph)
        elif style == "examples":
            return self._build_examples_prompt(semantic_graph)
        else:
            raise ValueError(f"Unknown prompt style: {style}")
    
    def _build_comprehensive_prompt(self, semantic_graph: SemanticGraph) -> str:
        """
        Build comprehensive prompt with full graph details.
        
        Best for complex websites with many screens/actions.
        """
        prompt_parts = []
        
        # Header
        prompt_parts.append(self._build_header())
        prompt_parts.append("")
        
        # Website overview
        prompt_parts.append(self._build_website_overview(semantic_graph))
        prompt_parts.append("")
        
        # Screen details
        prompt_parts.append(self._build_screen_catalog(semantic_graph))
        prompt_parts.append("")
        
        # Transition graph
        prompt_parts.append(self._build_transition_summary(semantic_graph))
        prompt_parts.append("")
        
        # Task requirements
        prompt_parts.append(self._build_task_requirements())
        prompt_parts.append("")
        
        # Output format
        prompt_parts.append(self._build_output_format())
        
        return "\n".join(prompt_parts)
    
    def _build_concise_prompt(self, semantic_graph: SemanticGraph) -> str:
        """
        Build concise prompt with key information only.
        
        Best for simpler websites or token-limited models.
        """
        prompt_parts = []
        
        prompt_parts.append("# Task Synthesis Request")
        prompt_parts.append("")
        prompt_parts.append(f"Website: {semantic_graph.start_url}")
        prompt_parts.append(f"Screens discovered: {semantic_graph.get_screen_count()}")
        prompt_parts.append(f"Transitions: {semantic_graph.get_transition_count()}")
        prompt_parts.append("")
        
        # Key screens only
        prompt_parts.append("## Key Screens:")
        for screen_id, screen in list(semantic_graph.screens.items())[:10]:
            prompt_parts.append(f"- {screen.screen_type}: {screen.semantic_summary}")
        prompt_parts.append("")
        
        # Task request
        prompt_parts.append("## Request:")
        prompt_parts.append("Synthesize 5-10 realistic user tasks that can be completed "
                          "using the available screens and actions.")
        prompt_parts.append("")
        prompt_parts.append("Each task should be:")
        prompt_parts.append("- A high-level user goal (e.g., 'buy a product', 'check order status')")
        prompt_parts.append("- Achievable using discovered transitions")
        prompt_parts.append("- 2-5 steps long")
        
        return "\n".join(prompt_parts)
    
    def _build_examples_prompt(self, semantic_graph: SemanticGraph) -> str:
        """
        Build prompt with example task structure.
        
        Guides LLM with concrete examples.
        """
        prompt = self._build_comprehensive_prompt(semantic_graph)
        
        examples = """

## Example Tasks:

Example 1 - E-commerce:
{
  "task_id": "task_001",
  "goal": "Purchase a product",
  "steps": [
    {"intent": "search_product", "description": "Search for desired product"},
    {"intent": "view_product", "description": "View product details"},
    {"intent": "add_to_cart", "description": "Add product to cart"},
    {"intent": "checkout", "description": "Proceed to checkout"}
  ]
}

Example 2 - Account Management:
{
  "task_id": "task_002",
  "goal": "View order history",
  "steps": [
    {"intent": "login", "description": "Log into account"},
    {"intent": "navigate_orders", "description": "Navigate to order history"},
    {"intent": "view_order_details", "description": "View specific order details"}
  ]
}

Generate similar tasks based on the exploration graph above.
"""
        return prompt + examples
    
    def _validate_semantic_only(self, semantic_graph: SemanticGraph):
        """
        Validate that semantic graph contains NO executable information.
        
        STRICT ENFORCEMENT:
        - Checks for forbidden fields: selector, xpath, dom, coordinates, etc.
        - Raises exception if violations found
        - Prevents executable data from reaching LLM
        
        Args:
            semantic_graph: Graph to validate
            
        Raises:
            ValueError: If executable fields found
        """
        graph_dict = semantic_graph.to_dict()
        
        # Forbidden fields that indicate executable data
        forbidden_fields = [
            'selector', 'xpath', 'dom_snapshot', 'coordinates',
            'element_text', 'element_type', 'element_id'
        ]
        
        violations = []
        
        # Check screens
        for screen_id, screen_data in graph_dict.get('screens', {}).items():
            for field in forbidden_fields:
                if field in screen_data:
                    violations.append(f"Screen {screen_id} contains '{field}'")
            
            # Check actions
            for action_data in screen_data.get('available_actions', []):
                for field in forbidden_fields:
                    if field in action_data:
                        violations.append(f"Action in screen {screen_id} contains '{field}'")
        
        # Check transitions
        for transition_data in graph_dict.get('transitions', []):
            for field in forbidden_fields:
                if field in transition_data:
                    tid = transition_data.get('transition_id', 'unknown')
                    violations.append(f"Transition {tid} contains '{field}'")
        
        if violations:
            error_msg = (
                "SEMANTIC-ONLY VALIDATION FAILED: Executable data found in semantic graph.\n"
                "This violates the semantic-only control principle.\n"
                "Violations:\n"
            )
            for violation in violations:
                error_msg += f"  - {violation}\n"
            
            self.logger.error(error_msg)
            raise ValueError(error_msg)
        
        self.logger.debug("Semantic-only validation passed: No executable fields found")
    
    def _validate_semantic_only(self, semantic_graph: SemanticGraph):
        """
        Validate that semantic graph contains NO executable information.
        
        Uses centralized validation utilities for consistency.
        
        Args:
            semantic_graph: Graph to validate
            
        Raises:
            ValueError: If executable fields found
        """
        graph_dict = semantic_graph.to_dict()
        
        # Use centralized validation
        validate_semantic_only(
            graph_dict,
            context="TaskSynthesis input (SemanticGraph)",
            raise_on_violation=True
        )
        
        self.logger.debug("Semantic-only validation passed: No executable fields found")
    
    def _build_header(self) -> str:
        """Build prompt header explaining the task."""
        return """# Web Task Synthesis

You are a task synthesis agent. Your job is to analyze a website's semantic structure
and generate realistic user tasks that can be performed on the website.

IMPORTANT:
- Focus on HIGH-LEVEL user goals
- Tasks should be realistic workflows users would perform
- Each task is a sequence of semantic action intents
- Tasks should use available actions discovered during exploration"""
    
    def _build_website_overview(self, semantic_graph: SemanticGraph) -> str:
        """Build website overview section."""
        lines = ["## Website Overview", ""]
        lines.append(f"Start URL: {semantic_graph.start_url}")
        lines.append(f"Total screens: {semantic_graph.get_screen_count()}")
        lines.append(f"Total transitions: {semantic_graph.get_transition_count()}")
        
        # Screen type distribution
        screen_types = {}
        for screen in semantic_graph.screens.values():
            screen_types[screen.screen_type] = screen_types.get(screen.screen_type, 0) + 1
        
        lines.append("")
        lines.append("Screen types:")
        for screen_type, count in sorted(screen_types.items(), key=lambda x: -x[1]):
            lines.append(f"  - {screen_type}: {count}")
        
        return "\n".join(lines)
    
    def _build_screen_catalog(self, semantic_graph: SemanticGraph) -> str:
        """Build detailed screen catalog."""
        lines = ["## Available Screens", ""]
        
        # Limit screens to avoid token overflow
        screens_to_show = list(semantic_graph.screens.items())[:self.max_screens_in_prompt]
        
        for screen_id, screen in screens_to_show:
            lines.append(f"### Screen: {screen_id}")
            lines.append(f"Type: {screen.screen_type}")
            lines.append(f"Summary: {screen.semantic_summary}")
            lines.append("")
            
            # Available actions
            if screen.available_actions:
                lines.append("Available actions:")
                actions_to_show = screen.available_actions[:self.max_actions_per_screen]
                for action in actions_to_show:
                    lines.append(f"  - [{action['intent']}] {action['description']}")
                
                if len(screen.available_actions) > self.max_actions_per_screen:
                    remaining = len(screen.available_actions) - self.max_actions_per_screen
                    lines.append(f"  ... and {remaining} more actions")
            else:
                lines.append("No actions available")
            
            lines.append("")
        
        if len(semantic_graph.screens) > self.max_screens_in_prompt:
            remaining = len(semantic_graph.screens) - self.max_screens_in_prompt
            lines.append(f"... and {remaining} more screens")
        
        return "\n".join(lines)
    
    def _build_transition_summary(self, semantic_graph: SemanticGraph) -> str:
        """Build transition graph summary."""
        lines = ["## Transition Graph", ""]
        lines.append("Key transitions discovered:")
        lines.append("")
        
        # Group transitions by from_screen
        transitions_by_screen: Dict[str, List] = {}
        for transition in semantic_graph.transitions:
            if transition.from_screen_id not in transitions_by_screen:
                transitions_by_screen[transition.from_screen_id] = []
            transitions_by_screen[transition.from_screen_id].append(transition)
        
        # Show top screens by transition count
        sorted_screens = sorted(
            transitions_by_screen.items(),
            key=lambda x: len(x[1]),
            reverse=True
        )[:10]
        
        for screen_id, transitions in sorted_screens:
            screen = semantic_graph.screens.get(screen_id)
            if screen:
                lines.append(f"From {screen.screen_type} ({screen_id}):")
                for t in transitions[:5]:  # Limit transitions per screen
                    lines.append(f"  --[{t.action_intent}]--> {t.to_screen_id}")
                if len(transitions) > 5:
                    lines.append(f"  ... and {len(transitions) - 5} more")
                lines.append("")
        
        return "\n".join(lines)
    
    def _build_task_requirements(self) -> str:
        """Build task synthesis requirements."""
        return """## Task Synthesis Requirements

Generate 5-10 realistic user tasks based on the exploration graph above.

Each task should:
1. Have a clear HIGH-LEVEL goal (e.g., "Purchase a product", "View order history")
2. Consist of 2-5 sequential steps
3. Use action intents that exist in the graph
4. Represent realistic user workflows

Task characteristics:
- Focus on user intent, not implementation
- Tasks should be achievable using discovered transitions
- Vary complexity (some simple, some multi-step)
- Cover different areas of the website"""
    
    def _build_output_format(self) -> str:
        """Build expected output format specification."""
        return """## Output Format

Return tasks as a JSON array:

[
  {
    "task_id": "task_001",
    "goal": "Brief description of user goal",
    "category": "e.g., shopping, account_management, search",
    "complexity": "simple|medium|complex",
    "steps": [
      {
        "step_number": 1,
        "intent": "action_intent_from_graph",
        "description": "Human-readable step description",
        "expected_outcome": "What happens after this step"
      },
      ...
    ]
  },
  ...
]

CRITICAL: Use ONLY action intents that appear in the exploration graph above."""
    
    def build_task_validation_prompt(
        self,
        task: Dict[str, Any],
        semantic_graph: SemanticGraph
    ) -> str:
        """
        Build prompt to validate if a task is achievable.
        
        Args:
            task: Synthesized task to validate
            semantic_graph: Semantic graph
            
        Returns:
            Validation prompt string
        """
        lines = ["# Task Validation", ""]
        lines.append("Validate if the following task is achievable given the exploration graph:")
        lines.append("")
        lines.append(f"Task: {task.get('goal', 'Unknown')}")
        lines.append("Steps:")
        for step in task.get('steps', []):
            lines.append(f"  {step.get('step_number', '?')}. {step.get('intent', 'unknown')}: "
                        f"{step.get('description', '')}")
        lines.append("")
        lines.append("Questions:")
        lines.append("1. Do all action intents exist in the graph?")
        lines.append("2. Are transitions between steps valid?")
        lines.append("3. Is the task realistic for a user?")
        lines.append("")
        lines.append("Respond with: VALID or INVALID, with brief reasoning.")
        
        return "\n".join(lines)
