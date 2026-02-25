"""
Training package for SLM-based web agent.

This package contains all components for training the Small Language Model
policy using unified trajectory data. It operates ENTIRELY offline and has
strict architectural boundaries.

ARCHITECTURE RULES:
- ONLY depends on: schema.py, torch, standard library
- NEVER imports: explorers, adapters, envs, browser, runtime agents
- Operates purely on Trajectory data (no environment interaction)

Components:
- dataset.py: Load and prepare trajectory data from JSON files
- collate.py: Encode observations and actions into tensors
- model.py: SLM policy network (LSTM-based)
- trainer.py: Training loop, loss computation, checkpointing
- train.py: CLI entry point for training
- evaluate.py: Offline evaluation script for checkpoints

Data Flow:
1. Trajectory JSON files (data/trajectories/online/, offline/)
   ↓
2. TrajectoryDataset loads and flattens trajectories into steps
   ↓
3. StateEncoder/ActionEncoder convert to tensors
   ↓
4. WebAgentPolicy predicts actions from states
   ↓
5. Trainer optimizes model with cross-entropy loss
   ↓
6. Checkpoint saved (can be loaded by runtime agent)

Usage:
    # Train a model
    python training/train.py --data_dir data/trajectories --epochs 10
    
    # Evaluate a trained model
    python training/evaluate.py --checkpoint checkpoints/best_model.pt

Design Principles:
- Unified trajectory schema is the ONLY data contract
- Training is offline and deterministic (no environment interaction)
- Model is simple and lightweight (suitable for on-device inference)
- Easy to swap model architecture (just implement forward/predict)
- Checkpoints are self-contained (include all model config)
"""

__all__ = [
    # Dataset
    "TrajectoryDataset",
    # Encoding
    "StateEncoder",
    "ActionEncoder",
    "collate_fn",
    "create_collate_fn",
    # Model
    "WebAgentPolicy",
    "count_parameters",
    # Training
    "Trainer",
]

from training.dataset import TrajectoryDataset
from training.collate import StateEncoder, ActionEncoder, collate_fn, create_collate_fn
from training.model import WebAgentPolicy, count_parameters
from training.trainer import Trainer
