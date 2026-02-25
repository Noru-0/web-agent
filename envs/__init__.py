"""
Environment interfaces for website-specific tasks.
"""

from .base_env import WebEnv
from .generic_env import GenericWebEnv

__all__ = [
    "WebEnv",
    "GenericWebEnv",
]
