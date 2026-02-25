"""
Agent runner for episode execution.

The runner is responsible for connecting an agent with an environment
and orchestrating the episode lifecycle:

1. Reset environment
2. Get initial observation
3. Loop:
   - Agent selects action
   - Environment executes action
   - Environment returns observation
   - Check if episode is done
4. Return episode summary

The runner has NO agent logic and NO environment logic.
It ONLY coordinates the interaction between agent and environment.

DESIGN:
- Stateless (each run is independent)
- Minimal interface
- Clear separation of concerns
- Easy to extend for logging/metrics
"""

import sys
from pathlib import Path
from typing import Dict, Any, List, Optional
import asyncio

sys.path.insert(0, str(Path(__file__).parent.parent))
from agents.base_agent import BaseAgent
from envs.base_env import WebEnv
from schema import Action


class EpisodeSummary:
    """
    Summary of a completed episode.
    
    Contains:
    - Number of steps taken
    - Final observation
    - Whether episode completed successfully
    - List of actions taken
    """
    
    def __init__(self):
        self.steps: int = 0
        self.actions: List[Action] = []
        self.observations: List[Dict[str, Any]] = []
        self.completed: bool = False
        self.error: Optional[str] = None
    
    def add_step(self, action: Action, observation: Dict[str, Any]):
        """Record a step"""
        self.actions.append(action)
        self.observations.append(observation)
        self.steps += 1
    
    def set_completed(self, completed: bool):
        """Mark episode as completed or terminated"""
        self.completed = completed
    
    def set_error(self, error: str):
        """Record error that terminated episode"""
        self.error = error
    
    def __str__(self) -> str:
        """String representation of episode summary"""
        status = "COMPLETED" if self.completed else "TERMINATED"
        if self.error:
            status = f"ERROR: {self.error}"
        
        return f"""
Episode Summary:
  Status: {status}
  Steps: {self.steps}
  Actions: {len(self.actions)}
  Observations: {len(self.observations)}
""".strip()


class AgentRunner:
    """
    Orchestrates agent-environment interaction.
    
    This class is the production runtime loop. It connects
    an agent with an environment and runs episodes.
    
    Usage:
        runner = AgentRunner(agent, env, max_steps=10)
        summary = await runner.run_episode(verbose=True)
        print(summary)
    """
    
    def __init__(
        self,
        agent: BaseAgent,
        env: WebEnv,
        max_steps: int = 10,
        verbose: bool = False,
        recorder = None
    ):
        """
        Initialize runner.
        
        Args:
            agent: Agent to run
            env: Environment to run in
            max_steps: Maximum steps per episode
            verbose: If True, print progress during episode
            recorder: Optional trajectory recorder (for online recording)
        """
        self.agent = agent
        self.env = env
        self.max_steps = max_steps
        self.verbose = verbose
        self.recorder = recorder
    
    async def run_episode(self) -> EpisodeSummary:
        """
        Run a single episode.
        
        Episode lifecycle:
        1. Reset agent and environment
        2. Get initial observation
        3. Loop until done or max_steps:
           - Agent selects action
           - Environment executes action
           - Record step
        4. Return summary
        
        Returns:
            EpisodeSummary with episode statistics
        """
        summary = EpisodeSummary()
        
        try:
            # Reset agent and environment
            self.agent.reset()
            initial_obs = await self.env.reset()
            
            # Notify recorder of episode start
            if self.recorder is not None:
                self.recorder.on_reset(initial_obs)
            
            if self.verbose:
                print(f"\n{'='*60}")
                print(f"Starting episode with {self.agent.get_name()}")
                print(f"Max steps: {self.max_steps}")
                print(f"{'='*60}\n")
                print(f"Initial observation:")
                self._print_observation(initial_obs)
            
            # Episode loop
            observation = initial_obs
            done = False
            step = 0
            
            while not done and step < self.max_steps:
                step += 1
                
                # Agent selects action
                action = self.agent.act(observation)
                
                if self.verbose:
                    print(f"\n--- Step {step} ---")
                    print(f"Action: {action.type.value}")
                    if action.target:
                        print(f"  Target: {action.target}")
                    if action.value:
                        print(f"  Value: {action.value}")
                
                # Environment executes action
                observation, done = await self.env.step(action)
                
                # Record step in summary
                summary.add_step(action, observation)
                
                # Notify recorder of step
                if self.recorder is not None:
                    self.recorder.on_step(action, observation, reward=0.0, done=done)
                
                if self.verbose:
                    print(f"\nObservation after action:")
                    self._print_observation(observation)
                    print(f"Done: {done}")
            
            # Mark completion status
            summary.set_completed(done)
            
            # Notify recorder of episode end
            if self.recorder is not None:
                self.recorder.on_episode_end(success=done, error=None)
            
            if self.verbose:
                print(f"\n{'='*60}")
                print(f"Episode finished")
                print(f"{'='*60}")
                print(summary)
        
        except Exception as e:
            summary.set_error(str(e))
            
            # Notify recorder of error
            if self.recorder is not None:
                self.recorder.on_episode_end(success=False, error=str(e))
            
            if self.verbose:
                print(f"\nError during episode: {e}")
        
        return summary
    
    def _print_observation(self, obs: Dict[str, Any]):
        """Pretty-print observation"""
        print(f"  URL: {obs.get('url', 'N/A')}")
        
        text = obs.get('text', '')
        if text:
            # Truncate long text
            text_preview = text[:100] + "..." if len(text) > 100 else text
            print(f"  Text: {text_preview}")
        
        clickables = obs.get('clickables', [])
        if clickables:
            print(f"  Clickables ({len(clickables)}):")
            for i, clickable in enumerate(clickables[:5]):  # Show first 5
                print(f"    {i+1}. {clickable}")
            if len(clickables) > 5:
                print(f"    ... and {len(clickables) - 5} more")
        else:
            print(f"  Clickables: None")


async def run_single_episode(
    agent: BaseAgent,
    env: WebEnv,
    max_steps: int = 10,
    verbose: bool = True,
    recorder = None
) -> EpisodeSummary:
    """
    Convenience function to run a single episode.
    
    Args:
        agent: Agent to run
        env: Environment to run in
        max_steps: Maximum steps per episode
        verbose: Print progress
        recorder: Optional trajectory recorder
        
    Returns:
        Episode summary
    """
    runner = AgentRunner(agent, env, max_steps=max_steps, verbose=verbose, recorder=recorder)
    return await runner.run_episode()


if __name__ == "__main__":
    # Quick test of runner (requires demo env)
    print("AgentRunner module loaded successfully")
    print("Use run_single_episode() to run an episode")
