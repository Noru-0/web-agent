"""
WebTactix explorer adapter.

This adapter converts WebTactix exploration logs into the unified
trajectory format. WebTactix is an LLM-based web agent that explores
websites and generates interaction traces.

EXPECTED INPUT FORMAT (example):
{
  "task": "Book a flight",
  "url": "https://example.com",
  "steps": [
    {
      "observation": {
        "url": "https://example.com",
        "html": "<html>...</html>",
        "text": "Welcome...",
        "elements": [...]
      },
      "action": {
        "type": "click",
        "element": "button#search",
        "reasoning": "..."
      },
      "reward": 0.0
    },
    ...
  ],
  "success": true,
  "metadata": {...}
}

NOTE: This is a REFERENCE IMPLEMENTATION. Actual WebTactix format
may differ. Adapt as needed based on real explorer output.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from adapters.base_adapter import ExplorerAdapter, InvalidExplorerOutputError, ConversionError
from schema import Trajectory, TrajectoryStep, Action, ActionType, State


class WebTactiXAdapter(ExplorerAdapter):
    """
    Adapter for WebTactix LLM explorer.
    
    Converts WebTactix exploration logs to unified trajectories.
    """
    
    def __init__(self):
        super().__init__("WebTactix")
        
        # Action mapping: WebTactix -> schema.ActionType
        self.action_map = {
            "click": ActionType.CLICK,
            "type": ActionType.TYPE,
            "scroll": ActionType.SCROLL,
            "navigate": ActionType.NAVIGATE,
            "wait": ActionType.WAIT,
            "select": ActionType.SELECT,
        }
    
    def load_raw(self, path: Path) -> Dict[str, Any]:
        """
        Load WebTactix JSON log file.
        
        Args:
            path: Path to JSON file
            
        Returns:
            Parsed JSON data
        """
        if not path.exists():
            raise FileNotFoundError(f"WebTactix output not found: {path}")
        
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return data
        except json.JSONDecodeError as e:
            raise InvalidExplorerOutputError(f"Invalid JSON in {path}: {e}")
        except Exception as e:
            raise InvalidExplorerOutputError(f"Failed to load {path}: {e}")
    
    def to_trajectory(self, raw: Dict[str, Any]) -> Trajectory:
        """
        Convert WebTactix log to Trajectory.
        
        Args:
            raw: Raw WebTactix log data
            
        Returns:
            Unified Trajectory
        """
        # Extract task
        task = raw.get("task", "unknown_task")
        
        # Extract steps
        raw_steps = raw.get("steps", [])
        if not raw_steps:
            raise ConversionError("WebTactix log has no steps")
        
        # Convert each step
        trajectory_steps = []
        for i, raw_step in enumerate(raw_steps):
            try:
                # Extract observation
                obs = raw_step.get("observation", {})
                state = self._obs_to_state(obs)
                
                # Extract action
                raw_action = raw_step.get("action", {})
                action = self._convert_action(raw_action)
                
                # Get next observation (from next step or current if last)
                if i + 1 < len(raw_steps):
                    next_obs = raw_steps[i + 1].get("observation", obs)
                else:
                    next_obs = obs  # Last step uses same state
                next_state = self._obs_to_state(next_obs)
                
                # Extract reward
                reward = raw_step.get("reward", 0.0)
                
                # Create step
                step = TrajectoryStep(
                    state=state,
                    action=action,
                    next_state=next_state,
                    reward=reward,
                    meta={
                        "step_num": i + 1,
                        "explorer": "webtactix",
                        "reasoning": raw_action.get("reasoning", "")
                    }
                )
                trajectory_steps.append(step)
                
            except Exception as e:
                raise ConversionError(f"Failed to convert step {i}: {e}")
        
        # Extract success and metadata
        success = raw.get("success", False)
        metadata = raw.get("metadata", {})
        metadata["explorer"] = "webtactix"
        metadata["url"] = raw.get("url", "unknown")
        
        # Create trajectory
        trajectory = Trajectory(
            steps=trajectory_steps,
            task=task,
            success=success,
            meta=metadata
        )
        
        return trajectory
    
    def _obs_to_state(self, obs: Dict[str, Any]) -> State:
        """Convert WebTactix observation to State"""
        url = obs.get("url", "")
        html = obs.get("html", "")
        text = obs.get("text", "")
        
        # Extract interactive elements if available
        elements = obs.get("elements", [])
        interactive_elements = None
        if elements:
            interactive_elements = [
                {
                    "selector": elem.get("selector", ""),
                    "type": elem.get("type", "unknown"),
                    "text": elem.get("text", "")
                }
                for elem in elements
            ]
        
        # If no HTML but we have text, wrap text in HTML
        if not html and text:
            html = f"<!-- WebTactix Text Content -->\n{text}"
        
        return State(
            url=url,
            html=html,
            interactive_elements=interactive_elements,
            dom_tree=None,
            screenshot=None,
            viewport=None
        )
    
    def _convert_action(self, raw_action: Dict[str, Any]) -> Action:
        """Convert WebTactix action to schema.Action"""
        # Get action type
        action_type_str = raw_action.get("type", "").lower()
        action_type = self.action_map.get(action_type_str)
        
        if action_type is None:
            # Unknown action type, default to CLICK
            action_type = ActionType.CLICK
        
        # Extract target element
        target = raw_action.get("element", "")
        if not target:
            target = raw_action.get("selector", "")
        
        # Extract value (for TYPE actions)
        value = raw_action.get("value")
        if value is None:
            value = raw_action.get("text")
        
        return Action(
            type=action_type,
            target=target,
            value=value
        )
