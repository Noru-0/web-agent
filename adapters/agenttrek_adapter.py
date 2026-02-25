"""
AgentTrek explorer adapter.

This adapter converts AgentTrek exploration traces into the unified
trajectory format. AgentTrek is an LLM-based agent that uses tool
calls to interact with web environments.

EXPECTED INPUT FORMAT (example):
{
  "goal": "Find product information",
  "starting_url": "https://example.com",
  "trace": [
    {
      "state": {
        "url": "https://example.com",
        "page_content": "...",
        "interactive": [...]
      },
      "thought": "I need to click the search button",
      "tool": "click_element",
      "tool_input": {"selector": "#search"},
      "tool_output": "Success"
    },
    ...
  ],
  "outcome": "success",
  "metrics": {...}
}

NOTE: This is a REFERENCE IMPLEMENTATION. Actual AgentTrek format
may differ. Adapt as needed based on real explorer output.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from adapters.base_adapter import ExplorerAdapter, InvalidExplorerOutputError, ConversionError
from schema import Trajectory, TrajectoryStep, Action, ActionType, State


class AgentTrekAdapter(ExplorerAdapter):
    """
    Adapter for AgentTrek LLM explorer.
    
    Converts AgentTrek tool-based traces to unified trajectories.
    """
    
    def __init__(self):
        super().__init__("AgentTrek")
        
        # Tool call mapping: AgentTrek tool -> schema.ActionType
        self.tool_map = {
            "click_element": ActionType.CLICK,
            "click": ActionType.CLICK,
            "type_text": ActionType.TYPE,
            "input_text": ActionType.TYPE,
            "scroll_page": ActionType.SCROLL,
            "scroll": ActionType.SCROLL,
            "navigate_to": ActionType.NAVIGATE,
            "goto": ActionType.NAVIGATE,
            "wait": ActionType.WAIT,
            "select_option": ActionType.SELECT,
        }
    
    def load_raw(self, path: Path) -> Dict[str, Any]:
        """
        Load AgentTrek JSON trace file.
        
        Args:
            path: Path to JSON file
            
        Returns:
            Parsed JSON data
        """
        if not path.exists():
            raise FileNotFoundError(f"AgentTrek output not found: {path}")
        
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
        Convert AgentTrek trace to Trajectory.
        
        Args:
            raw: Raw AgentTrek trace data
            
        Returns:
            Unified Trajectory
        """
        # Extract task/goal
        task = raw.get("goal", raw.get("task", "unknown_task"))
        
        # Extract trace
        raw_trace = raw.get("trace", [])
        if not raw_trace:
            raise ConversionError("AgentTrek trace has no steps")
        
        # Convert each trace entry
        trajectory_steps = []
        for i, trace_entry in enumerate(raw_trace):
            try:
                # Extract state
                state_data = trace_entry.get("state", {})
                state = self._state_to_state(state_data)
                
                # Extract tool call (action)
                tool_name = trace_entry.get("tool", "")
                tool_input = trace_entry.get("tool_input", {})
                action = self._tool_to_action(tool_name, tool_input)
                
                # Get next state (from next entry or current if last)
                if i + 1 < len(raw_trace):
                    next_state_data = raw_trace[i + 1].get("state", state_data)
                else:
                    next_state_data = state_data
                next_state = self._state_to_state(next_state_data)
                
                # Create step
                step = TrajectoryStep(
                    state=state,
                    action=action,
                    next_state=next_state,
                    reward=0.0,  # AgentTrek doesn't provide rewards
                    meta={
                        "step_num": i + 1,
                        "explorer": "agenttrek",
                        "thought": trace_entry.get("thought", ""),
                        "tool_output": trace_entry.get("tool_output", "")
                    }
                )
                trajectory_steps.append(step)
                
            except Exception as e:
                raise ConversionError(f"Failed to convert trace entry {i}: {e}")
        
        # Extract outcome and metadata
        outcome = raw.get("outcome", "unknown")
        success = outcome.lower() in ["success", "succeeded", "completed"]
        
        metadata = raw.get("metrics", {})
        metadata["explorer"] = "agenttrek"
        metadata["starting_url"] = raw.get("starting_url", "unknown")
        metadata["outcome"] = outcome
        
        # Create trajectory
        trajectory = Trajectory(
            steps=trajectory_steps,
            task=task,
            success=success,
            meta=metadata
        )
        
        return trajectory
    
    def _state_to_state(self, state_data: Dict[str, Any]) -> State:
        """Convert AgentTrek state to State"""
        url = state_data.get("url", "")
        page_content = state_data.get("page_content", "")
        
        # AgentTrek stores content as text, wrap in HTML
        html = f"<!-- AgentTrek Page Content -->\n{page_content}" if page_content else ""
        
        # Extract interactive elements if available
        interactive = state_data.get("interactive", [])
        interactive_elements = None
        if interactive:
            interactive_elements = [
                {
                    "selector": elem.get("selector", elem.get("id", "")),
                    "type": elem.get("tag", "unknown"),
                    "text": elem.get("text", "")
                }
                for elem in interactive
            ]
        
        return State(
            url=url,
            html=html,
            interactive_elements=interactive_elements,
            dom_tree=None,
            screenshot=None,
            viewport=None
        )
    
    def _tool_to_action(self, tool_name: str, tool_input: Dict[str, Any]) -> Action:
        """Convert AgentTrek tool call to schema.Action"""
        # Map tool name to action type
        action_type = self.tool_map.get(tool_name)
        
        if action_type is None:
            # Unknown tool, default to CLICK
            action_type = ActionType.CLICK
        
        # Extract target from tool input
        target = tool_input.get("selector", "")
        if not target:
            target = tool_input.get("element", "")
        if not target:
            target = tool_input.get("url", "")  # For navigate
        
        # Extract value (for TYPE/SELECT actions)
        value = tool_input.get("text")
        if value is None:
            value = tool_input.get("value")
        
        return Action(
            type=action_type,
            target=target,
            value=value
        )
