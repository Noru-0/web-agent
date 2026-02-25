"""
Online trajectory recorder for production agent runs.

This recorder observes agent-environment interactions and saves
trajectories in the unified schema format. It does NOT affect
agent behavior and is completely optional.

DESIGN:
- Observer pattern (agent unaware of recorder)
- Non-intrusive (can be turned on/off)
- Uses unified schema as single source of truth
- No dependencies on explorers or training

Usage:
    recorder = TrajectoryRecorder(
        save_dir="data/trajectories/online",
        env_name="demo",
        agent_name="simple"
    )
    
    # In runner lifecycle
    recorder.on_reset(initial_obs)
    recorder.on_step(action, obs, reward, done)
    recorder.on_episode_end(success=True)
"""

import json
import sys
from pathlib import Path
from typing import Any, Dict, Optional, List
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from schema import Trajectory, TrajectoryStep, Action, State


class TrajectoryRecorder:
    """
    Records agent-environment interactions as trajectories.
    
    This recorder observes the agent loop and saves trajectories
    in the unified format. It is production-safe and can be
    enabled/disabled without affecting agent behavior.
    """
    
    def __init__(
        self,
        save_dir: str = "data/trajectories/online",
        env_name: str = "unknown",
        agent_name: str = "unknown",
        task: str = "online_run",
        auto_save: bool = True
    ):
        """
        Initialize trajectory recorder.
        
        Args:
            save_dir: Directory to save trajectories
            env_name: Name of environment
            agent_name: Name of agent
            task: Task description
            auto_save: If True, save automatically on episode end
        """
        self.save_dir = Path(save_dir)
        self.save_dir.mkdir(parents=True, exist_ok=True)
        
        self.env_name = env_name
        self.agent_name = agent_name
        self.task = task
        self.auto_save = auto_save
        
        # Current trajectory being recorded
        self.current_trajectory: Optional[Trajectory] = None
        self.current_steps: List[TrajectoryStep] = []
        self.initial_state: Optional[State] = None
        self.episode_start_time: Optional[datetime] = None
    
    def on_reset(self, observation: Dict[str, Any]):
        """
        Called when episode starts.
        
        Args:
            observation: Initial observation from environment
        """
        self.episode_start_time = datetime.now()
        self.current_steps = []
        self.initial_state = self._obs_to_state(observation)
        
        # Initialize trajectory
        self.current_trajectory = Trajectory(
            steps=[],
            task=self.task,
            success=False,  # Updated at episode end
            meta={
                "env": self.env_name,
                "agent": self.agent_name,
                "start_time": self.episode_start_time.isoformat(),
                "source": "online_recording"
            }
        )
    
    def on_step(
        self,
        action: Action,
        observation: Dict[str, Any],
        reward: float = 0.0,
        done: bool = False
    ):
        """
        Called after each agent-environment step.
        
        Args:
            action: Action taken by agent
            observation: Observation after action
            reward: Reward received (if available)
            done: Whether episode is done
        """
        if self.current_trajectory is None:
            raise RuntimeError("on_reset() must be called before on_step()")
        
        # Get previous state (last step's next_state, or initial state)
        if self.current_steps:
            state = self.current_steps[-1].next_state
        else:
            state = self.initial_state
        
        # Create next state from observation
        next_state = self._obs_to_state(observation)
        
        # Create trajectory step (without 'done' field - store in meta)
        step = TrajectoryStep(
            state=state,
            action=action,
            next_state=next_state,
            reward=reward,
            meta={
                "step_num": len(self.current_steps) + 1,
                "timestamp": datetime.now().isoformat(),
                "done": done  # Store done flag in meta
            }
        )
        
        self.current_steps.append(step)
    
    def on_episode_end(self, success: bool = False, error: Optional[str] = None):
        """
        Called when episode ends.
        
        Args:
            success: Whether episode completed successfully
            error: Error message if episode failed
        """
        if self.current_trajectory is None:
            raise RuntimeError("on_reset() must be called before on_episode_end()")
        
        # Update trajectory
        self.current_trajectory.steps = self.current_steps
        self.current_trajectory.success = success
        
        # Add end time to metadata
        end_time = datetime.now()
        self.current_trajectory.meta["end_time"] = end_time.isoformat()
        
        if self.episode_start_time:
            duration = (end_time - self.episode_start_time).total_seconds()
            self.current_trajectory.meta["duration_seconds"] = duration
        
        if error:
            self.current_trajectory.meta["error"] = error
        
        # Auto-save if enabled
        if self.auto_save:
            filename = self.save()
            return filename
        
        return None
    
    def save(self, filename: Optional[str] = None) -> str:
        """
        Save current trajectory to disk.
        
        Args:
            filename: Optional custom filename
            
        Returns:
            Path to saved file
        """
        if self.current_trajectory is None:
            raise RuntimeError("No trajectory to save")
        
        # Generate filename if not provided
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{timestamp}_{self.env_name}_{self.agent_name}.json"
        
        filepath = self.save_dir / filename
        
        # Convert trajectory to dict and save
        traj_dict = self.current_trajectory.to_dict()
        
        with open(filepath, 'w') as f:
            json.dump(traj_dict, f, indent=2)
        
        return str(filepath)
    
    def get_current_trajectory(self) -> Optional[Trajectory]:
        """Get current trajectory being recorded"""
        return self.current_trajectory
    
    def _obs_to_state(self, observation: Dict[str, Any]) -> State:
        """
        Convert observation dict to State object.
        
        Args:
            observation: Observation from environment
            
        Returns:
            State object
        """
        url = observation.get('url', '')
        text = observation.get('text', '')
        clickables = observation.get('clickables', [])
        
        # State expects html field (not text)
        # For now, wrap text content in simple HTML
        # In production, the environment should provide actual HTML
        html = f"<!-- Text Content -->\n{text}" if text else ""
        
        # Store clickables as interactive elements in State schema format
        interactive_elements = None
        if clickables:
            interactive_elements = [
                {"selector": selector, "type": "clickable"}
                for selector in clickables
            ]
        
        state = State(
            url=url,
            html=html,
            interactive_elements=interactive_elements,
            dom_tree=None,
            screenshot=None,
            viewport=None
        )
        
        return state


class NullRecorder:
    """
    Null object pattern for recorder.
    
    This recorder does nothing and is used when recording is disabled.
    Allows runner to call recorder methods without checking if None.
    """
    
    def on_reset(self, observation: Dict[str, Any]):
        """No-op"""
        pass
    
    def on_step(
        self,
        action: Action,
        observation: Dict[str, Any],
        reward: float = 0.0,
        done: bool = False
    ):
        """No-op"""
        pass
    
    def on_episode_end(self, success: bool = False, error: Optional[str] = None):
        """No-op"""
        pass
    
    def get_current_trajectory(self) -> None:
        """Returns None"""
        return None


def create_recorder(
    enabled: bool = True,
    save_dir: str = "data/trajectories/online",
    env_name: str = "unknown",
    agent_name: str = "unknown",
    task: str = "online_run"
) -> TrajectoryRecorder:
    """
    Factory function to create recorder.
    
    Args:
        enabled: If False, returns NullRecorder
        save_dir: Directory to save trajectories
        env_name: Name of environment
        agent_name: Name of agent
        task: Task description
        
    Returns:
        TrajectoryRecorder or NullRecorder
    """
    if not enabled:
        return NullRecorder()
    
    return TrajectoryRecorder(
        save_dir=save_dir,
        env_name=env_name,
        agent_name=agent_name,
        task=task
    )
