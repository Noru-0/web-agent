"""
Exploration module - Domain logic for web exploration.

This module contains all exploration domain logic:
- schema: Data models (Screen, Transition, ActionSemantic)
- action_schema: Dual-representation action models (semantic + executable)
- analyzer: LLM-based screen understanding
- dedup: Screen deduplication logic
- storage: Screen graph and transition persistence
- exploration_bridge: Main exploration loop and adapters
- semantic_projector: Strip executable info for LLM consumption
- action_grounder: Map semantic intents to executables
- task_synthesis: Build LLM prompts for task synthesis

Separation of concerns:
- exploration/ = ALL domain logic (BFS algorithm, data models, adapters)
- workflows/ = ONLY orchestration (config, initialization, CLI)
- adapters/ = foreign data translation (for training data)
"""

from .schema import (
    Screen,
    ActionSemantic,
    Transition,
    ExplorationResult,
    ScreenType
)

from .action_schema import (
    Action,
    ActionExecutable,
    ActionSemantic as ActionSemanticNew,
    ActionCategory,
    ScreenWithActions,
    Transition as TransitionNew,
    ExplorationResult as ExplorationResultNew
)

from .exploration_bridge import (
    run_exploration,
    ExplorationLoop,
    ExplorationAdapter,
    SimpleExplorationAdapter
)

from .semantic_projector import (
    SemanticProjector,
    SemanticGraph,
    SemanticScreen,
    SemanticTransition
)

from .action_grounder import (
    ActionGrounder
)

from .task_synthesis import (
    TaskSynthesisPromptBuilder,
    TaskSynthesizer,
    Task,
    TaskGraph,
    TaskPriority
)

__all__ = [
    # Data models
    "Screen",
    "ActionSemantic",
    "Transition",
    "ExplorationResult",
    "ScreenType",
    # Task synthesis
    "Task",
    "TaskGraph",
    "TaskPriority",
    "TaskSynthesizer",
    "TaskSynthesisPromptBuilder",
    # Exploration logic
    "run_exploration",
    "ExplorationLoop",
    # Adapters
    "ExplorationAdapter",
    "SimpleExplorationAdapter"
]

