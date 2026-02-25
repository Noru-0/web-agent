"""
Unified trajectory schema and type definitions.

This is the SINGLE SOURCE OF TRUTH for RUNTIME data types.

SCOPE: Training, Agent Runtime, Trajectory Recording
- Used by: training/, agents/, data/recorders/
- Purpose: Define what agents see/do and how trajectories are stored

DISTINCTION FROM exploration/schema.py:
- This file (schema.py): Runtime actions and trajectory steps
  * Action, ActionType: What agents execute
  * State: What agents observe
  * TrajectoryStep, Trajectory: Training data format

- exploration/schema.py: Discovery phase models
  * Screen, ScreenType: Semantic screen classification
  * ActionSemantic: High-level action descriptions from LLM
  * Transition: Screen-to-screen navigation
  
These serve DIFFERENT phases and should NOT be merged:
- Exploration discovers possibilities (semantic)
- Runtime executes actions (concrete)
"""

from typing import Any, Dict, List, Literal, Optional, Union
from dataclasses import dataclass, asdict
from enum import Enum


class ActionType(str, Enum):
    """Project-owned action space"""
    CLICK = "CLICK"
    TYPE = "TYPE"
    SCROLL = "SCROLL"
    NAVIGATE = "NAVIGATE"
    WAIT = "WAIT"
    SELECT = "SELECT"


@dataclass
class Action:
    """Unified action representation"""
    type: ActionType
    target: str  # Element selector/identifier
    value: Optional[str] = None  # For TYPE, SELECT actions
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type.value,
            "target": self.target,
            "value": self.value
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Action':
        return cls(
            type=ActionType(data["type"]),
            target=data["target"],
            value=data.get("value")
        )


@dataclass
class State:
    """
    Project-owned state representation.
    This is what the SLM agent sees and operates on.
    """
    url: str
    html: str  # Simplified/cleaned HTML
    dom_tree: Optional[Dict[str, Any]] = None
    screenshot: Optional[str] = None  # Base64 encoded or path
    interactive_elements: Optional[List[Dict[str, str]]] = None
    viewport: Optional[Dict[str, int]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'State':
        return cls(**data)


@dataclass
class TrajectoryStep:
    """
    Unified trajectory step - MANDATORY format for all training data.
    All explorer outputs MUST be converted to this format via adapters.
    """
    state: State
    action: Action
    next_state: State
    reward: float = 0.0  # Optional reward signal
    meta: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.meta is None:
            self.meta = {}
        # Ensure required meta fields
        if "url" not in self.meta:
            self.meta["url"] = self.state.url
        if "success" not in self.meta:
            self.meta["success"] = False
        if "explorer" not in self.meta:
            self.meta["explorer"] = "unknown"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "state": self.state.to_dict(),
            "action": self.action.to_dict(),
            "next_state": self.next_state.to_dict(),
            "reward": self.reward,
            "meta": self.meta
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TrajectoryStep':
        return cls(
            state=State.from_dict(data["state"]),
            action=Action.from_dict(data["action"]),
            next_state=State.from_dict(data["next_state"]),
            reward=data.get("reward", 0.0),
            meta=data.get("meta", {})
        )


@dataclass
class Trajectory:
    """
    Complete episode trajectory.
    """
    steps: List[TrajectoryStep]
    task: str
    success: bool
    total_reward: float = 0.0
    meta: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.meta is None:
            self.meta = {}
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "steps": [step.to_dict() for step in self.steps],
            "task": self.task,
            "success": self.success,
            "total_reward": self.total_reward,
            "meta": self.meta
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Trajectory':
        return cls(
            steps=[TrajectoryStep.from_dict(step) for step in data["steps"]],
            task=data["task"],
            success=data["success"],
            total_reward=data.get("total_reward", 0.0),
            meta=data.get("meta", {})
        )
    
    def __len__(self) -> int:
        return len(self.steps)


# Type aliases for clarity
EncodedState = Dict[str, Any]  # Output of observation encoder
RawExplorerLog = Dict[str, Any]  # Explorer-specific format (black box)
