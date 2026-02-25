# Training Pipeline Documentation

This document explains the **offline SLM training pipeline** - how we train a Small Language Model policy using unified trajectory data.

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Training Data Flow](#training-data-flow)
- [Components](#components)
- [Training a Model](#training-a-model)
- [Evaluating a Model](#evaluating-a-model)
- [Using Checkpoints in Runtime](#using-checkpoints-in-runtime)
- [Design Principles](#design-principles)

## Overview

**Goal**: Train a Small Language Model (SLM) to predict web agent actions from observations.

**Input**: Unified trajectory data from `data/trajectories/online/` and `data/trajectories/offline/`

**Output**: Trained model checkpoint that can be loaded by runtime agents

**Constraints**:
- **Offline only**: No environment interaction during training
- **Pure data transformation**: Only depends on schema.py and trajectory JSON files
- **No cross-contamination**: Never imports explorers, adapters, browser, or runtime agents

## Architecture

```
Trajectory JSON Files
    ↓
TrajectoryDataset (dataset.py)
    ↓ flatten into (state, action) pairs
StateEncoder + ActionEncoder (collate.py)
    ↓ convert to tensors
WebAgentPolicy Model (model.py)
    ↓ predict actions from states
Trainer (trainer.py)
    ↓ optimize with cross-entropy loss
Checkpoint (.pt file)
    ↓ can be loaded by runtime agent
Production Agent
```

## Training Data Flow

### 1. Trajectory Loading

```python
from training.dataset import TrajectoryDataset

dataset = TrajectoryDataset(
    data_dir="data/trajectories",
    sources=["online", "offline"],  # Load from both sources
    filter_failed=False,             # Include failed trajectories
    filter_empty=True                # Exclude empty trajectories
)

# Dataset flattens trajectories into individual steps
# Each step: (state, action, next_state, reward, meta)
print(f"Loaded {len(dataset)} training examples")
```

**What it does**:
- Loads all JSON files from `data/trajectories/online/` and `data/trajectories/offline/`
- Parses them into `Trajectory` objects using `schema.py`
- Flattens each trajectory into individual (state, action) pairs
- Each pair becomes one training example

### 2. Train/Val Split

```python
train_dataset, val_dataset = dataset.split(
    train_ratio=0.8,
    shuffle=True,
    seed=42
)
```

**Important**: Split is at trajectory level (not step level) to avoid data leakage.

### 3. Encoding States and Actions

```python
from training.collate import StateEncoder, ActionEncoder

state_encoder = StateEncoder(
    vocab_size=1000,
    max_text_length=512,      # Max HTML text length
    max_url_length=128,        # Max URL length
    max_elements=50,           # Max interactive elements
    max_element_text_length=32 # Max text per element
)

action_encoder = ActionEncoder(
    max_elements=50,           # Must match state_encoder
    max_value_length=128       # Max length for TYPE values
)
```

**State Encoding**:
- URL → character indices (128 chars)
- HTML text → character indices (512 chars)
- Interactive elements → character indices (50 elements × 32 chars each)

**Action Encoding**:
- Action type → class label (0-5 for CLICK, TYPE, SCROLL, etc.)
- Target element → element index (0-49 for which element to click)
- Value text → character indices (128 chars for TYPE actions)

### 4. Model Architecture

```python
from training.model import WebAgentPolicy

model = WebAgentPolicy(
    vocab_size=1000,
    num_action_types=6,        # CLICK, TYPE, SCROLL, NAVIGATE, WAIT, SELECT
    max_elements=50,
    embedding_dim=128,         # Character embedding dimension
    hidden_dim=256,            # LSTM hidden dimension
    num_layers=2,              # Number of LSTM layers
    dropout=0.1
)
```

**Architecture**:
- Character embeddings (shared across all text)
- 3 LSTM encoders (URL, text, elements)
- State fusion layer
- 3 prediction heads:
  * Action type (classification)
  * Target element (classification)
  * Value text (sequence generation)

### 5. Training Loop

```python
from training.trainer import Trainer

trainer = Trainer(
    model=model,
    train_dataset=train_dataset,
    val_dataset=val_dataset,
    state_encoder=state_encoder,
    action_encoder=action_encoder,
    config={
        "device": "cuda",
        "num_epochs": 10,
        "batch_size": 32,
        "learning_rate": 1e-3,
        "output_dir": "checkpoints"
    }
)

trainer.train()
```

**What it does**:
- Batches training data
- Forward pass through model
- Computes multi-task loss:
  * Action type loss (cross-entropy)
  * Target element loss (cross-entropy)
  * Value text loss (cross-entropy, teacher forcing)
- Backpropagation and optimization
- Validation after each epoch
- Saves checkpoints

## Components

### dataset.py

**TrajectoryDataset**: Loads trajectory JSON files and prepares training data

Key features:
- Loads from multiple sources (online/offline)
- Filters failed/empty trajectories
- Flattens into (state, action) pairs
- Supports train/val split
- Reports dataset statistics

### collate.py

**StateEncoder**: Converts State observations to tensors  
**ActionEncoder**: Converts Actions to label tensors  
**collate_fn**: Batches data for DataLoader

Key features:
- Character-level encoding (simple, no pretrained models needed)
- Fixed-size representations (padding/truncation)
- Separate encoding for URL, text, elements
- Action type + target + value encoding

### model.py

**WebAgentPolicy**: LSTM-based policy model

Architecture:
- 3 LSTM encoders (bidirectional)
- State fusion MLP
- 3 prediction heads
- Auto-regressive value generation

Key features:
- Lightweight (few million parameters)
- No external dependencies
- Forward pass (training with teacher forcing)
- Predict method (inference without teacher forcing)
- Save/load checkpoints

### trainer.py

**Trainer**: Training loop and optimization

Key features:
- Multi-task loss (action type + target + value)
- Learning rate scheduling
- Gradient clipping
- Progress logging
- Checkpoint saving (periodic + best + final)
- Training history tracking

### train.py

**CLI entry point** for training

```bash
python training/train.py \
    --data_dir data/trajectories \
    --sources online offline \
    --epochs 10 \
    --batch_size 32 \
    --lr 1e-3 \
    --output_dir checkpoints
```

### evaluate.py

**CLI entry point** for offline evaluation

```bash
python training/evaluate.py \
    --checkpoint checkpoints/best_model.pt \
    --data_dir data/trajectories \
    --sources offline
```

Reports:
- Overall action accuracy
- Target accuracy
- Per-action breakdown

## Training a Model

### Basic Training

```bash
# Train with default settings
python training/train.py --data_dir data/trajectories

# Train with custom settings
python training/train.py \
    --data_dir data/trajectories \
    --sources online offline \
    --epochs 20 \
    --batch_size 64 \
    --lr 1e-3 \
    --output_dir my_checkpoints
```

### Training Output

```
Loading trajectories from data/trajectories...
  Found 150 files in online/
  Found 300 files in offline/
  Loaded 450 trajectories (0 skipped)

Dataset Statistics:
============================================================
Trajectories: 450
  Successful: 320
  Failed: 130
Training steps: 3890
Avg steps/trajectory: 8.6

Action distribution:
  CLICK     : 2100 (54.0%)
  TYPE      :  890 (22.9%)
  SCROLL    :  450 (11.6%)
  NAVIGATE  :  300 (7.7%)
  WAIT      :  150 (3.9%)
============================================================

Splitting dataset (train: 80%, val: 20%)...
Train: 3112 steps from 360 trajectories
Val:   778 steps from 90 trajectories

Creating model...
Model initialized with 1,234,567 parameters
Device: cuda

============================================================
Starting training for 10 epochs
============================================================

Epoch 1/10
  Epoch 1 [100/98] Loss: 2.4532 (action: 1.8234, target: 0.4123, value: 0.2175)
  ...

Epoch 1/10 Summary:
  Train - Loss: 2.3421, Time: 45.2s
  Val   - Loss: 2.1234, Action Acc: 45.23%, Target Acc: 32.10%
  → Saved best model (val_loss: 2.1234)

...

Epoch 10/10 Summary:
  Train - Loss: 0.8765, Time: 45.5s
  Val   - Loss: 0.9123, Action Acc: 78.90%, Target Acc: 65.43%
  → Saved best model (val_loss: 0.9123)

============================================================
Training complete!
Best validation loss: 0.9123
Models saved to: checkpoints
============================================================

Final model saved to: checkpoints/final_model.pt
Best model saved to: checkpoints/best_model.pt
```

### Resume Training

```bash
python training/train.py \
    --data_dir data/trajectories \
    --resume checkpoints/checkpoint_epoch_5.pt \
    --epochs 15  # Train 10 more epochs (5 already done)
```

## Evaluating a Model

### Offline Evaluation

```bash
# Evaluate on test data
python training/evaluate.py \
    --checkpoint checkpoints/best_model.pt \
    --data_dir data/trajectories \
    --sources offline
```

**Output**:

```
============================================================
Evaluation Results
============================================================
Total samples: 778
Action type accuracy: 78.90%
Target element accuracy: 65.43%

Per-Action Breakdown:
Action Type     Count    Correct  Accuracy  
--------------------------------------------------
CLICK           420      350      83.33%
NAVIGATE        60       48       80.00%
SCROLL          90       72       80.00%
TYPE            178      135      75.84%
WAIT            30       24       80.00%
============================================================

Results saved to: checkpoints/evaluation_results.json
```

### Interpreting Results

**Action Type Accuracy**: How often the model predicts the correct action type
- **Good**: >70% (model understands what action to take)
- **Fair**: 50-70% (model has some understanding)
- **Poor**: <50% (model is guessing)

**Target Element Accuracy**: How often the model selects the correct element
- **Good**: >60% (model can identify interactive elements)
- **Fair**: 40-60% (model has some spatial understanding)
- **Poor**: <40% (model struggles with element selection)

**Per-Action Breakdown**: Shows which actions the model is good/bad at
- CLICK usually has highest accuracy (most common action)
- TYPE might be lower (more complex, requires value generation)

## Using Checkpoints in Runtime

### Checkpoint Structure

A checkpoint contains:
- `model_state_dict`: Model weights
- `vocab_size`: Character vocabulary size
- `num_action_types`: Number of action types (6)
- `max_elements`: Maximum interactive elements (50)
- `embedding_dim`: Embedding dimension
- `hidden_dim`: Hidden dimension
- `epoch`: Training epoch number
- `config`: Full training configuration

### Loading in Runtime Agent

**Option 1: Direct model loading**

```python
from training.model import WebAgentPolicy
import torch

# Load checkpoint
checkpoint = torch.load("checkpoints/best_model.pt", map_location="cpu")

# Create model
model = WebAgentPolicy(
    vocab_size=checkpoint["vocab_size"],
    num_action_types=checkpoint["num_action_types"],
    max_elements=checkpoint["max_elements"],
    embedding_dim=checkpoint["embedding_dim"],
    hidden_dim=checkpoint["hidden_dim"]
)
model.load_state_dict(checkpoint["model_state_dict"])
model.eval()

# Use model for inference
state_encoded = state_encoder.encode_state(current_state)
outputs = model.predict(
    url=state_encoded["url"].unsqueeze(0),
    text=state_encoded["text"].unsqueeze(0),
    elements=state_encoded["elements"].unsqueeze(0),
    element_mask=state_encoded["element_mask"].unsqueeze(0)
)

action_type_idx = outputs["action_type"][0].item()
```

**Option 2: Through agent wrapper** (future work)

```python
from agents.slm_agent import SLMAgent

agent = SLMAgent.from_checkpoint("checkpoints/best_model.pt")
action = await agent.act(observation)
```

### Checkpoint Compatibility

**Important**: Encoders must match training settings
- Use same `vocab_size`, `max_elements`, `max_text_length`, etc.
- Store encoder config in checkpoint or documentation
- Runtime agent should have access to StateEncoder and ActionEncoder

## Design Principles

### 1. Offline-Only

Training operates purely on trajectory data. No environment interaction, no browser automation, no API calls.

**Why**: Clean separation between training (offline) and inference (online). Training is deterministic and reproducible.

### 2. Unified Schema is the Contract

Training only depends on `schema.py` (Trajectory, State, Action). Any data that matches the schema can be used for training.

**Why**: Explorers can change, adapters can be rewritten, but training remains stable as long as schema stays consistent.

### 3. No Hidden Dependencies

Training must NOT import:
- `explorers/` (external black boxes)
- `adapters/` (offline data conversion only)
- `envs/` (runtime environments)
- `browser/` (browser automation)
- `agents/` (runtime agents)

**Why**: Training should work even if those components don't exist. Enables training on different machines, CI/CD, etc.

### 4. Simple and Lightweight

Model is intentionally simple (LSTM, character-level). No pretrained transformers, no vision models.

**Why**: 
- Fast training (minutes to hours, not days)
- On-device inference (no GPU required)
- Educational (easy to understand and modify)
- Baseline for comparison

Can be extended with:
- Pretrained embeddings (e.g., BERT)
- Larger transformers
- Vision encoders (for screenshots)
- Multi-modal models

### 5. Deterministic and Reproducible

Training uses fixed random seeds, deterministic data loading, and saves all hyperparameters.

**Why**: Research requires reproducibility. Same data + same config → same model.

### 6. Checkpoints are Self-Contained

Checkpoints include model weights AND all configuration needed to reconstruct the model.

**Why**: No guessing about hyperparameters. Checkpoint is portable and can be loaded anywhere.

## FAQ

**Q: Why character-level encoding instead of pretrained embeddings?**  
A: Simplicity and no external dependencies. Character-level works reasonably well for web text and is self-contained. Can be upgraded to word-level or pretrained later.

**Q: Why LSTM instead of Transformer?**  
A: LSTMs are simpler, faster to train, and require less data. Good baseline. Can upgrade to Transformer if needed.

**Q: Can I mix online and offline trajectories?**  
A: Yes! Use `--sources online offline` when training. The dataset loads from both and treats them identically.

**Q: Should I filter failed trajectories?**  
A: Depends. Successful trajectories show good behavior, but failed trajectories show mistakes to avoid. Experiment with both.

**Q: How much data do I need?**  
A: Depends on task complexity. Start with 100-500 trajectories. More data → better model, but diminishing returns.

**Q: How long does training take?**  
A: On CPU: ~5-10 min/epoch for 5000 steps  
On GPU: ~1-2 min/epoch for 5000 steps  
10 epochs is usually enough for initial convergence.

**Q: Can I train on a subset of actions?**  
A: Not directly, but you can filter trajectories before training. Or modify the model to predict a subset of action types.

**Q: How do I debug low accuracy?**  
A:
1. Check data quality (trajectories make sense?)
2. Check action distribution (too imbalanced?)
3. Increase model capacity (larger hidden_dim)
4. Add more training data
5. Tune hyperparameters (learning rate, dropout)

**Q: Can I use this checkpoint in a different agent framework?**  
A: Yes, as long as:
1. You can encode States using the same StateEncoder
2. You can decode action predictions to Actions
3. You have PyTorch to load the model

Checkpoint is just PyTorch model weights + config. Portable to any Python environment.

## Summary

The training pipeline:
1. Loads unified trajectories from JSON
2. Encodes states and actions into tensors
3. Trains an LSTM policy model
4. Saves checkpoints for runtime use

**Key constraints**:
- Offline only (no environment interaction)
- Only depends on schema.py and trajectory data
- No cross-contamination with explorers/adapters/runtime

**Key outputs**:
- Trained model checkpoint (`.pt` file)
- Training history (loss, accuracy over time)
- Evaluation metrics (action/target accuracy)

**Next steps**:
- Create a runtime agent that loads the checkpoint
- Integrate with environment for online evaluation
- Iterate on model architecture and hyperparameters
