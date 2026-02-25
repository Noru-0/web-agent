"""
Main package initialization.
"""

__version__ = "0.1.0"
__author__ = "Your Name"

# Export key components
from schema import (
    Action,
    ActionType,
    State,
    Trajectory,
    TrajectoryStep
)

__all__ = [
    "Action",
    "ActionType", 
    "State",
    "Trajectory",
    "TrajectoryStep"
]
