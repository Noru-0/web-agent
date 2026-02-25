"""
Agent package for production inference.

This package contains agent implementations that run in production mode.
Agents take observations and output actions.

ARCHITECTURAL RULES:
- Agents depend ONLY on: envs/, schema.py
- Agents must NOT import: explorers/, adapters/, training/
- Agent interface must remain stable for SLM replacement
"""

from agents.base_agent import BaseAgent
from agents.simple_agent import SimpleAgent
from agents.runner import AgentRunner

# SLMAgent requires PyTorch - import conditionally
try:
    from agents.slm_agent import SLMAgent
    __all__ = ["BaseAgent", "SimpleAgent", "SLMAgent", "AgentRunner"]
except ImportError:
    # PyTorch not available - SLMAgent not usable
    __all__ = ["BaseAgent", "SimpleAgent", "AgentRunner"]
