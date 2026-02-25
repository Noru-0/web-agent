"""
Trajectory dataset loader.

This module loads unified trajectory data from JSON files and prepares
it for training. It operates purely on the unified schema and has no
dependencies on explorers, adapters, or runtime components.

ARCHITECTURAL BOUNDARIES:
- Imports: schema.py, torch, standard library ONLY
- No imports from: explorers, adapters, envs, browser, agents
- Operates on Trajectory JSON files in data/trajectories/
"""

import json
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional, Literal, Tuple
from dataclasses import dataclass

# Import unified schema (ONLY allowed external dependency)
sys.path.insert(0, str(Path(__file__).parent.parent))
from schema import Trajectory, TrajectoryStep, State, Action, ActionType

try:
    import torch
    from torch.utils.data import Dataset
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    

@dataclass
class DatasetStats:
    """Statistics about the loaded dataset"""
    num_trajectories: int
    num_steps: int
    num_successful: int
    num_failed: int
    avg_steps_per_trajectory: float
    action_distribution: Dict[str, int]
    sources: Dict[str, int]  # online vs offline


class TrajectoryDataset(Dataset if TORCH_AVAILABLE else object):
    """
    Dataset for loading and preparing unified trajectory data.
    
    This dataset:
    1. Loads Trajectory JSON files from online/offline directories
    2. Flattens trajectories into (state, action) pairs
    3. Supports filtering (failed episodes, empty steps, etc.)
    4. Returns individual steps for training
    
    Usage:
        dataset = TrajectoryDataset(
            data_dir="data/trajectories",
            sources=["online", "offline"],
            filter_failed=True
        )
        
        state, action, meta = dataset[0]
    """
    
    def __init__(
        self,
        data_dir: str,
        sources: List[Literal["online", "offline"]] = ["online", "offline"],
        filter_failed: bool = False,
        filter_empty: bool = True,
        max_trajectories: Optional[int] = None,
        verbose: bool = True
    ):
        """
        Initialize trajectory dataset.
        
        Args:
            data_dir: Root directory containing trajectories (e.g., "data/trajectories")
            sources: Which sources to load from (["online"], ["offline"], or both)
            filter_failed: If True, exclude trajectories where success=False
            filter_empty: If True, exclude trajectories with no steps
            max_trajectories: Maximum number of trajectories to load (for debugging)
            verbose: Print loading progress
        """
        self.data_dir = Path(data_dir)
        self.sources = sources
        self.filter_failed = filter_failed
        self.filter_empty = filter_empty
        self.max_trajectories = max_trajectories
        self.verbose = verbose
        
        # Storage
        self.trajectories: List[Trajectory] = []
        self.steps: List[Tuple[TrajectoryStep, int]] = []  # (step, trajectory_idx)
        
        # Load data
        self._load_trajectories()
        self._flatten_trajectories()
        
        if self.verbose:
            stats = self.get_stats()
            self._print_stats(stats)
    
    def _load_trajectories(self):
        """Load trajectory JSON files from specified sources"""
        if self.verbose:
            print(f"Loading trajectories from {self.data_dir}...")
        
        trajectory_files = []
        
        # Collect files from each source
        for source in self.sources:
            source_dir = self.data_dir / source
            if not source_dir.exists():
                if self.verbose:
                    print(f"  Warning: {source_dir} does not exist, skipping")
                continue
            
            files = list(source_dir.glob("*.json"))
            trajectory_files.extend([(f, source) for f in files])
            
            if self.verbose:
                print(f"  Found {len(files)} files in {source}/")
        
        if not trajectory_files:
            raise ValueError(f"No trajectory files found in {self.data_dir}")
        
        # Sort for deterministic loading
        trajectory_files.sort(key=lambda x: str(x[0]))
        
        # Apply max limit
        if self.max_trajectories:
            trajectory_files = trajectory_files[:self.max_trajectories]
        
        # Load each file
        loaded_count = 0
        skipped_count = 0
        
        for traj_file, source in trajectory_files:
            try:
                with open(traj_file) as f:
                    data = json.load(f)
                
                trajectory = Trajectory.from_dict(data)
                
                # Apply filters
                if self.filter_failed and not trajectory.success:
                    skipped_count += 1
                    continue
                
                if self.filter_empty and len(trajectory.steps) == 0:
                    skipped_count += 1
                    continue
                
                # Add source to metadata
                if "source" not in trajectory.meta:
                    trajectory.meta["source"] = source
                
                self.trajectories.append(trajectory)
                loaded_count += 1
                
            except Exception as e:
                if self.verbose:
                    print(f"  Error loading {traj_file.name}: {e}")
                skipped_count += 1
        
        if self.verbose:
            print(f"  Loaded {loaded_count} trajectories ({skipped_count} skipped)")
    
    def _flatten_trajectories(self):
        """Flatten trajectories into individual (state, action) step pairs"""
        for traj_idx, trajectory in enumerate(self.trajectories):
            for step in trajectory.steps:
                self.steps.append((step, traj_idx))
    
    def __len__(self) -> int:
        """Number of training examples (individual steps)"""
        return len(self.steps)
    
    def __getitem__(self, idx: int) -> Tuple[State, Action, Dict[str, Any]]:
        """
        Get a single training example.
        
        Returns:
            state: State observation
            action: Ground truth action
            meta: Metadata (trajectory_idx, step_meta, trajectory_meta)
        """
        step, traj_idx = self.steps[idx]
        trajectory = self.trajectories[traj_idx]
        
        meta = {
            "trajectory_idx": traj_idx,
            "trajectory_task": trajectory.task,
            "trajectory_success": trajectory.success,
            "step_meta": step.meta,
            "trajectory_meta": trajectory.meta,
            "reward": step.reward,
        }
        
        return step.state, step.action, meta
    
    def get_trajectory(self, idx: int) -> Trajectory:
        """Get full trajectory by index"""
        return self.trajectories[idx]
    
    def get_stats(self) -> DatasetStats:
        """Compute dataset statistics"""
        num_successful = sum(1 for t in self.trajectories if t.success)
        num_failed = len(self.trajectories) - num_successful
        
        avg_steps = (
            sum(len(t) for t in self.trajectories) / len(self.trajectories)
            if self.trajectories else 0
        )
        
        # Action distribution
        action_dist: Dict[str, int] = {}
        for step, _ in self.steps:
            action_type = step.action.type.value
            action_dist[action_type] = action_dist.get(action_type, 0) + 1
        
        # Source distribution
        sources: Dict[str, int] = {}
        for traj in self.trajectories:
            source = traj.meta.get("source", "unknown")
            sources[source] = sources.get(source, 0) + 1
        
        return DatasetStats(
            num_trajectories=len(self.trajectories),
            num_steps=len(self.steps),
            num_successful=num_successful,
            num_failed=num_failed,
            avg_steps_per_trajectory=avg_steps,
            action_distribution=action_dist,
            sources=sources
        )
    
    def _print_stats(self, stats: DatasetStats):
        """Print dataset statistics"""
        print(f"\nDataset Statistics:")
        print(f"{'='*60}")
        print(f"Trajectories: {stats.num_trajectories}")
        print(f"  Successful: {stats.num_successful}")
        print(f"  Failed: {stats.num_failed}")
        print(f"Training steps: {stats.num_steps}")
        print(f"Avg steps/trajectory: {stats.avg_steps_per_trajectory:.1f}")
        print(f"\nAction distribution:")
        for action, count in sorted(stats.action_distribution.items()):
            pct = 100 * count / stats.num_steps
            print(f"  {action:10s}: {count:5d} ({pct:5.1f}%)")
        print(f"\nSources:")
        for source, count in sorted(stats.sources.items()):
            pct = 100 * count / stats.num_trajectories
            print(f"  {source:10s}: {count:5d} ({pct:5.1f}%)")
        print(f"{'='*60}\n")
    
    def split(
        self,
        train_ratio: float = 0.8,
        shuffle: bool = True,
        seed: int = 42
    ) -> Tuple['TrajectoryDataset', 'TrajectoryDataset']:
        """
        Split dataset into train/val sets (trajectory-level split).
        
        Args:
            train_ratio: Fraction of trajectories for training
            shuffle: Whether to shuffle before splitting
            seed: Random seed for reproducibility
            
        Returns:
            (train_dataset, val_dataset)
        """
        import random
        
        # Get trajectory indices
        indices = list(range(len(self.trajectories)))
        
        if shuffle:
            random.seed(seed)
            random.shuffle(indices)
        
        # Split indices
        split_idx = int(len(indices) * train_ratio)
        train_indices = set(indices[:split_idx])
        val_indices = set(indices[split_idx:])
        
        # Create new datasets with split data
        train_dataset = TrajectoryDataset.__new__(TrajectoryDataset)
        val_dataset = TrajectoryDataset.__new__(TrajectoryDataset)
        
        # Copy attributes
        for ds in [train_dataset, val_dataset]:
            ds.data_dir = self.data_dir
            ds.sources = self.sources
            ds.filter_failed = self.filter_failed
            ds.filter_empty = self.filter_empty
            ds.max_trajectories = None
            ds.verbose = False
        
        # Split trajectories and steps
        train_dataset.trajectories = [
            self.trajectories[i] for i in train_indices
        ]
        val_dataset.trajectories = [
            self.trajectories[i] for i in val_indices
        ]
        
        train_dataset.steps = [
            (step, idx) for step, idx in self.steps if idx in train_indices
        ]
        val_dataset.steps = [
            (step, idx) for step, idx in self.steps if idx in val_indices
        ]
        
        if self.verbose:
            print(f"\nSplit dataset:")
            print(f"  Train: {len(train_dataset)} steps from {len(train_dataset.trajectories)} trajectories")
            print(f"  Val:   {len(val_dataset)} steps from {len(val_dataset.trajectories)} trajectories")
        
        return train_dataset, val_dataset
