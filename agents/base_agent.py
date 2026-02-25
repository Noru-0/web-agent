"""
Base agent interface for production inference.

This defines the minimal interface that all agents must implement.
The interface is designed to be stable so that simple rule-based agents
can be replaced with SLM-backed agents without changing other code.

DESIGN PRINCIPLES:
- Minimal interface (reset, act)
- Stateless from external perspective
- Production-focused (no training, no trajectories)
- No dependencies on explorers or training code
"""

from abc import ABC, abstractmethod
from typing import Dict, Any
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from schema import Action


class BaseAgent(ABC):
    """
    Abstract base class for all agents.
    
    Agents are responsible for deciding what action to take given
    an observation. They run in production mode and must be fast.
    
    The interface is minimal to allow easy replacement:
    - SimpleAgent (rule-based) can be swapped for SLMAgent (model-based)
    - Environment code doesn't need to change
    - Runner code doesn't need to change
    """
    
    def __init__(self, name: str):
        """
        Initialize agent.
        
        Args:
            name: Agent name for logging/debugging
        """
        self.name = name
    
    @abstractmethod
    def reset(self):
        """
        Reset agent state at the beginning of an episode.
        
        Called before the first act() in each episode.
        Agents can use this to clear internal state.
        """
        pass
    
    @abstractmethod
    def act(self, observation: Dict[str, Any]) -> Action:
        """
        Select action given observation.
        
        This is the core inference method. Given the current state
        of the environment (observation), decide what action to take.
        
        Args:
            observation: Current observation from environment
            
        Returns:
            Action to execute
            
        Note:
            This method should be fast and deterministic (or use
            controlled randomness). It runs in the critical path
            of the production agent loop.
        """
        pass
    
    def get_name(self) -> str:
        """Get agent name"""
        return self.name
