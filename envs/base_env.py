"""
Base environment interface for web tasks.

This defines the abstract interface that all web environments must implement.

RULES:
- Environment must NOT know about explorers
- Environment must NOT know about training or models
- Keep interface minimal and explicit
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Tuple
import sys
from pathlib import Path

# Add project root for schema imports
sys.path.insert(0, str(Path(__file__).parent.parent))
from schema import Action


class WebEnv(ABC):
    """
    Abstract base class for web environments.
    
    Each environment represents a specific website or task.
    Environments are responsible for:
    - Managing browser state
    - Executing actions
    - Returning observations
    - Determining when episodes are done
    """
    
    def __init__(self, name: str):
        """
        Initialize environment.
        
        Args:
            name: Environment name
        """
        self.name = name
        self._step_count = 0
    
    @abstractmethod
    async def reset(self) -> Dict[str, Any]:
        """
        Reset environment to initial state.
        
        Returns:
            observation: Initial observation dict
        """
        pass
    
    @abstractmethod
    async def step(self, action: Action) -> Tuple[Dict[str, Any], bool]:
        """
        Execute action and return result.
        
        Args:
            action: Action to execute
            
        Returns:
            observation: Updated observation dict
            done: Whether episode is complete
        """
        pass
    
    @abstractmethod
    async def observe(self) -> Dict[str, Any]:
        """
        Get current observation without executing action.
        
        Returns:
            observation: Current observation dict
        """
        pass
    
    @abstractmethod
    async def close(self):
        """Clean up environment resources"""
        pass
    
    def _increment_step(self):
        """Increment step counter"""
        self._step_count += 1
    
    def get_step_count(self) -> int:
        """Get current step count"""
        return self._step_count
