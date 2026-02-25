# Training Pipeline

Offline SLM training pipeline for web agent policy learning.

## Quick Start

### Train a Model

```bash
python training/train.py --data_dir data/trajectories --epochs 10
```

### Evaluate a Model

```bash
python training/evaluate.py \
    --checkpoint checkpoints/best_model.pt \
    --data_dir data/trajectories
```

## Files

- **dataset.py**: Load trajectory JSON files, flatten into training examples
- **collate.py**: Encode states and actions into tensors
- **model.py**: LSTM-based policy model
- **trainer.py**: Training loop, loss, checkpointing
- **train.py**: CLI entry point for training
- **evaluate.py**: Offline evaluation on test data
- **TRAINING.md**: Comprehensive training guide

## Architecture

```
Trajectory JSON → TrajectoryDataset → Encoder → Model → Checkpoint
```

## Key Constraints

- **Offline only**: No environment interaction
- **Imports**: schema.py, torch, stdlib ONLY
- **No imports from**: explorers, adapters, envs, browser, agents

## Documentation

See [TRAINING.md](TRAINING.md) for comprehensive guide.
