"""
Exploration workflow orchestration.

This module handles:
- Configuration loading
- Environment and adapter initialization
- Calling the exploration domain logic
- CLI and logging setup

All exploration domain logic lives in exploration/exploration_bridge.py
"""

import asyncio
import logging
from typing import Optional
from pathlib import Path

from exploration.exploration_bridge import (
    run_exploration,
    ExplorationAdapter,
    get_exploration_adapter
)
from exploration.schema import ExplorationResult

logger = logging.getLogger(__name__)


async def explore_website(
    env,
    explorer_adapter: Optional[ExplorationAdapter] = None,
    start_url: Optional[str] = None,
    max_screens: int = None,
    max_transitions: int = None,
    max_actions_per_screen: int = None,
    storage = None
) -> ExplorationResult:
    """
    Orchestration wrapper for website exploration.
    
    This is a thin wrapper that delegates to the domain logic.
    Kept for backwards compatibility and convenient imports.
    
    Args:
        env: Web environment
        explorer_adapter: Explorer adapter for executing actions (if None, loads from .env)
        start_url: Starting URL (optional)
        max_screens: Maximum unique screens to discover (defaults from .env: EXPLORER_MAX_STEPS)
        max_transitions: Maximum transitions to record (defaults from .env)
        max_actions_per_screen: Maximum actions to try per screen (defaults from .env)
        storage: ExplorationStorage instance (optional)
        
    Returns:
        ExplorationResult from domain logic
    """
    logger.info("Orchestrating exploration workflow...")
    
    # Load defaults from .env if not provided
    from utils.env import env as env_config
    
    # Get explorer adapter if not provided
    if explorer_adapter is None:
        provider = env_config.get("EXPLORER_PROVIDER", "simple")
        logger.info(f"Loading explorer adapter from .env: {provider}")
        explorer_adapter = get_exploration_adapter(provider)
    
    if max_screens is None:
        max_screens = env_config.get_int("EXPLORER_MAX_STEPS", 50)
    if max_transitions is None:
        max_transitions = env_config.get_int("EXPLORER_MAX_STEPS", 50) * 4  # 4x screens
    if max_actions_per_screen is None:
        max_actions_per_screen = 10
    
    # Delegate to domain logic
    result = await run_exploration(
        env=env,
        explorer_adapter=explorer_adapter,
        start_url=start_url,
        max_screens=max_screens,
        max_transitions=max_transitions,
        max_actions_per_screen=max_actions_per_screen,
        storage=storage
    )
    
    return result


if __name__ == "__main__":
    # CLI entry point
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("Exploration workflow module")
    print("\nFor exploration orchestration:")
    print("  from workflows.explore import explore_website")
    print("  result = await explore_website(env, adapter)")
    print("\nFor direct domain logic:")
    print("  from exploration.exploration_bridge import run_exploration")
    print("  result = await run_exploration(env, adapter)")
