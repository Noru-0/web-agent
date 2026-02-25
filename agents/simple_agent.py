"""
Simple rule-based agent for baseline testing.

This agent uses deterministic heuristics to select actions.
It serves as:
- A baseline for comparison with trained SLM agents
- A sanity check that the environment works
- A placeholder until the SLM agent is trained

POLICY:
1. If there are clickable elements -> CLICK the first one
2. Else if URL can be navigated -> stay on page (no action)
3. Else -> no action

This is intentionally simple. The goal is to have a working
end-to-end system, not to have intelligent behavior.
"""

import sys
from pathlib import Path
from typing import Dict, Any, Optional, List

sys.path.insert(0, str(Path(__file__).parent.parent))
from agents.base_agent import BaseAgent
from schema import Action, ActionType


class SimpleAgent(BaseAgent):
    """
    Simple rule-based agent using fixed heuristics.
    
    This agent doesn't learn and has no state. It applies
    simple rules to decide what to do given an observation.
    
    The rules are intentionally naive - this is just a placeholder
    to validate the architecture before the SLM is trained.
    """
    
    def __init__(self, name: str = "SimpleAgent", click_first: bool = True):
        """
        Initialize simple agent.
        
        Args:
            name: Agent name
            click_first: If True, always click first clickable element.
                        If False, cycle through clickables.
        """
        super().__init__(name)
        self.click_first = click_first
        self.step_count = 0
    
    def reset(self):
        """Reset agent state"""
        self.step_count = 0
    
    def act(self, observation: Dict[str, Any]) -> Action:
        """
        Select action using simple heuristics.
        
        Decision logic:
        1. Extract clickable elements from observation
        2. If clickables exist, click the first one (or cycle through them)
        3. Otherwise, return a null action
        
        Args:
            observation: Dict with keys like 'url', 'text', 'clickables'
            
        Returns:
            Action to execute
        """
        self.step_count += 1
        
        # Extract clickables from observation
        clickables = observation.get('clickables', [])
        
        if not clickables:
            # No actionable elements - return null action
            return Action(
                type=ActionType.CLICK,
                target="",
                value=""
            )
        
        # Choose which clickable to interact with
        if self.click_first:
            # Always click the first one
            target_selector = clickables[0]
        else:
            # Cycle through clickables
            idx = (self.step_count - 1) % len(clickables)
            target_selector = clickables[idx]
        
        # Return click action
        return Action(
            type=ActionType.CLICK,
            target=target_selector,
            value=""
        )
    
    def get_step_count(self) -> int:
        """Get number of steps taken in current episode"""
        return self.step_count


class RandomAgent(BaseAgent):
    """
    Agent that takes random valid actions.
    
    This is useful for:
    - Testing environment robustness
    - Generating diverse trajectories
    - Comparison baseline for learned policies
    """
    
    def __init__(self, name: str = "RandomAgent", seed: Optional[int] = None):
        """
        Initialize random agent.
        
        Args:
            name: Agent name
            seed: Random seed for reproducibility
        """
        super().__init__(name)
        self.seed = seed
        if seed is not None:
            import random
            random.seed(seed)
    
    def reset(self):
        """Reset agent state"""
        if self.seed is not None:
            import random
            random.seed(self.seed)
    
    def act(self, observation: Dict[str, Any]) -> Action:
        """
        Select random action from available actions.
        
        Args:
            observation: Current observation
            
        Returns:
            Random valid action
        """
        import random
        
        clickables = observation.get('clickables', [])
        
        if not clickables:
            # No actions available
            return Action(
                type=ActionType.CLICK,
                target="",
                value=""
            )
        
        # Pick random clickable
        target_selector = random.choice(clickables)
        
        return Action(
            type=ActionType.CLICK,
            target=target_selector,
            value=""
        )


def create_simple_agent(strategy: str = "click_first") -> BaseAgent:
    """
    Factory function to create simple agents.
    
    Args:
        strategy: Agent strategy - "click_first", "cycle", or "random"
        
    Returns:
        Configured agent instance
    """
    if strategy == "click_first":
        return SimpleAgent(name="SimpleAgent-ClickFirst", click_first=True)
    elif strategy == "cycle":
        return SimpleAgent(name="SimpleAgent-Cycle", click_first=False)
    elif strategy == "random":
        return RandomAgent(name="RandomAgent")
    else:
        raise ValueError(f"Unknown strategy: {strategy}")
