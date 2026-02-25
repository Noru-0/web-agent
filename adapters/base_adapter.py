"""
Base adapter interface for explorer output conversion.

This defines the contract that all explorer adapters must implement.
The adapter pattern isolates the core system from the chaos of
external LLM explorers.

DESIGN PRINCIPLES:
- Explorers are untrusted inputs
- Unified schema is the single source of truth
- Fail loudly on schema violations
- Adapters are disposable, schema is permanent
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from schema import Trajectory, TrajectoryStep, Action, State


class ExplorerAdapter(ABC):
    """
    Abstract base class for explorer adapters.
    
    An adapter converts external explorer outputs (logs, traces, etc.)
    into the unified Trajectory format that the training pipeline expects.
    
    Each explorer (WebTactix, AgentTrek, etc.) has its own adapter
    that understands its specific output format.
    """
    
    def __init__(self, name: str):
        """
        Initialize adapter.
        
        Args:
            name: Human-readable name of the explorer
        """
        self.name = name
    
    @abstractmethod
    def load_raw(self, path: Path) -> Any:
        """
        Load raw explorer output from disk.
        
        This method is responsible for loading the explorer's output
        in whatever format it uses (JSON, pickle, plain text, etc.).
        
        Args:
            path: Path to explorer output file or directory
            
        Returns:
            Raw explorer output (format depends on explorer)
            
        Raises:
            FileNotFoundError: If path doesn't exist
            ValueError: If file format is invalid
        """
        pass
    
    @abstractmethod
    def to_trajectory(self, raw: Any) -> Trajectory:
        """
        Convert raw explorer output to unified Trajectory.
        
        This is the core conversion logic. It must:
        1. Extract observations from raw data
        2. Convert explorer actions to schema.Action
        3. Build TrajectoryStep objects
        4. Create a valid Trajectory
        
        Args:
            raw: Raw explorer output (from load_raw)
            
        Returns:
            Unified Trajectory object
            
        Raises:
            ValueError: If conversion fails (invalid data, missing fields, etc.)
        """
        pass
    
    def validate(self, trajectory: Trajectory):
        """
        Validate trajectory against schema requirements.
        
        This method checks that the trajectory is valid and complete.
        Override if you need explorer-specific validation.
        
        Args:
            trajectory: Trajectory to validate
            
        Raises:
            ValueError: If trajectory is invalid
        """
        if not trajectory.steps:
            raise ValueError(f"{self.name}: Trajectory has no steps")
        
        if trajectory.task is None or trajectory.task == "":
            raise ValueError(f"{self.name}: Trajectory missing task description")
        
        # Check each step
        for i, step in enumerate(trajectory.steps):
            if step.state is None:
                raise ValueError(f"{self.name}: Step {i} missing state")
            if step.action is None:
                raise ValueError(f"{self.name}: Step {i} missing action")
            if step.next_state is None:
                raise ValueError(f"{self.name}: Step {i} missing next_state")
    
    def convert(self, input_path: Path, output_path: Optional[Path] = None) -> Trajectory:
        """
        Complete conversion pipeline: load -> convert -> validate -> save.
        
        This is a convenience method that runs the full conversion.
        
        Args:
            input_path: Path to raw explorer output
            output_path: Optional path to save trajectory JSON
            
        Returns:
            Converted and validated Trajectory
        """
        # Load raw data
        raw = self.load_raw(input_path)
        
        # Convert to trajectory
        trajectory = self.to_trajectory(raw)
        
        # Validate
        self.validate(trajectory)
        
        # Save if output path provided
        if output_path is not None:
            import json
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w') as f:
                json.dump(trajectory.to_dict(), f, indent=2)
        
        return trajectory
    
    def get_name(self) -> str:
        """Get adapter name"""
        return self.name


class AdapterError(Exception):
    """Base exception for adapter errors"""
    pass


class InvalidExplorerOutputError(AdapterError):
    """Raised when explorer output is invalid or corrupted"""
    pass


class ConversionError(AdapterError):
    """Raised when conversion fails"""
    pass
