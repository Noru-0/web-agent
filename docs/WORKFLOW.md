# Complete Workflow Guide

This guide walks through the entire web agent system workflow, from data collection to production deployment.

## Overview

The system follows a clear pipeline:

```
Explorer (LLM) → Adapter → Data → Training → SLM Agent (Production)
   OFFLINE                      OFFLINE        ONLINE
```

## Detailed Workflow

### Phase 1: Offline Data Collection

**Goal**: Generate training data using LLM-based explorers

#### Step 1.1: Choose/Setup Explorer

Options:
- WebTactiX (example)
- AgentTrek (example)
- Your custom LLM-based agent

Place explorer code in:
```
explorers/
└── <explorer_name>/
    ├── ... (explorer code - treated as black box)
```

#### Step 1.2: Run Explorer

```bash
python scripts/run_explorer.py \
  --explorer webtactix \
  --task "book a flight from NYC to LA"
```

**Output**: Raw logs in explorer's format
```
data/raw/webtactix/book_a_flight_from_NYC_to_LA.json
```

**Example log format** (explorer-specific):
```json
{
  "task": "book a flight from NYC to LA",
  "steps": [
    {
      "observation": {
        "url": "https://airline.com",
        "html": "...",
        "screenshot": "..."
      },
      "action": {
        "type": "click",
        "element": "input[name='from']"
      },
      "next_observation": {...},
      "success": true
    }
  ]
}
```

---

### Phase 2: Data Conversion

**Goal**: Convert explorer logs to unified trajectory format

#### Step 2.1: Create/Verify Adapter

Ensure adapter exists for your explorer:
```python
# adapters/webtactix_adapter.py (root level)
class WebTactiXAdapter(ExplorerAdapter):
    def parse_action(self, raw_action):
        # Convert explorer action → unified Action
        return Action(
            type=ActionType.CLICK,
            target=raw_action["element"],
            value=raw_action.get("text")
        )
    
    def parse_state(self, raw_state):
        # Convert explorer state → unified State
        return State(
            url=raw_state["url"],
            html=raw_state["html"]
        )
```

#### Step 2.2: Run Conversion

```bash
python scripts/convert_data.py \
  --explorer webtactix \
  --input data/raw/webtactix \
  --output data/trajectories/webtactix
```

**Output**: Unified trajectories
```
data/trajectories/webtactix/book_a_flight_from_NYC_to_LA_traj_0.json
```

**Unified format**:
```json
{
  "steps": [
    {
      "state": {
        "url": "https://airline.com",
        "html": "...",
        "interactive_elements": [...]
      },
      "action": {
        "type": "CLICK",
        "target": "input[name='from']",
        "value": null
      },
      "next_state": {...},
      "reward": 0.5,
      "meta": {
        "url": "https://airline.com",
        "success": true,
        "explorer": "webtactix"
      }
    }
  ],
  "task": "book a flight from NYC to LA",
  "success": true,
  "total_reward": 5.0
}
```

---

### Phase 3: Data Cleaning

**Goal**: Validate and clean trajectories

#### Step 3.1: Run Cleaning

```bash
python scripts/clean_data.py \
  --input data/trajectories \
  --output data/cleaned \
  --min-steps 1
```

**What it does**:
- Removes invalid trajectories
- Validates state/action format
- Filters by minimum steps
- Checks required fields

**Output**: Clean trajectories
```
data/cleaned/book_a_flight_from_NYC_to_LA_traj_0.json
```

#### Step 3.2: Verify Data

```python
from training.dataset import TrajectoryDataset

dataset = TrajectoryDataset("data/cleaned")
stats = dataset.get_statistics()

print(f"Total examples: {stats['num_examples']}")
print(f"Action distribution: {stats['action_distribution']}")
print(f"Success rate: {stats['success_rate']:.2%}")
```

---

### Phase 4: Model Training

**Goal**: Train SLM on cleaned trajectories

#### Step 4.1: Configure Training

Edit `config/training.yaml`:
```yaml
data:
  train_dir: "data/cleaned"
  val_split: 0.1

model:
  name: "gpt2"  # or "distilgpt2", "microsoft/phi-2"
  device: "cpu"

training:
  num_epochs: 10
  batch_size: 32
  learning_rate: 1e-4
```

#### Step 4.2: Train Model

```bash
python training/train.py \
  --data-dir data/cleaned \
  --epochs 10 \
  --batch-size 32 \
  --lr 1e-4 \
  --model gpt2 \
  --device cpu
```

**Output**: Model checkpoints
```
checkpoints/
├── model_epoch_1.pt
├── model_epoch_2.pt
...
└── model_epoch_10.pt
```

**Training logs**:
```
Epoch 1/10
  Train loss: 2.3451
  Val loss: 2.1234
✓ Saved checkpoint: checkpoints/model_epoch_1.pt

Epoch 2/10
  Train loss: 1.8765
  Val loss: 1.7543
...
```

---

### Phase 5: Evaluation

**Goal**: Test trained agent on benchmarks

#### Step 5.1: Configure Evaluation

Create `config/eval.json`:
```json
{
  "environments": [
    {
      "name": "booking-form",
      "type": "form",
      "url": "https://airline.com/book",
      "form_data": {
        "from": "NYC",
        "to": "LA",
        "date": "2026-03-15"
      },
      "submit_selector": "button[type='submit']"
    }
  ],
  "num_episodes": 10
}
```

#### Step 5.2: Run Evaluation

```bash
python training/evaluate.py \
  --checkpoint checkpoints/model_epoch_10.pt \
  --config config/eval.json \
  --episodes 10 \
  --output results/eval_results.json
```

**Output**:
```
Evaluating on: booking-form
  Episode 1: ✓ (12 steps, reward=5.50)
  Episode 2: ✗ (50 steps, reward=2.30)
  ...
  Episode 10: ✓ (15 steps, reward=5.20)

  Success rate: 70.00%
  Avg reward: 4.25
  Avg steps: 22.5

Results saved to results/eval_results.json
```

---

### Phase 6: Production Deployment

**Goal**: Use trained agent in production

#### Step 6.1: Load Agent

```python
from agents.slm_agent import SLMAgent
from training.model import TransformerSLM
from observation.encoder import StateEncoder

# Load trained model
model = TransformerSLM(device="cpu")
model.load("checkpoints/model_epoch_10.pt")

# Create agent
encoder = StateEncoder()
agent = SLMAgent(model, encoder)
```

#### Step 6.2: Create Environment

```python
from browser.controller import PlaywrightController, BrowserConfig
from envs.base import FormFillingEnv

# Setup browser
browser_config = BrowserConfig(headless=True)
browser = PlaywrightController(browser_config)
await browser.start()

# Create task environment
env = FormFillingEnv(
    browser=browser,
    start_url="https://airline.com/book",
    form_data={
        "from": "NYC",
        "to": "LA",
        "date": "2026-03-15"
    },
    submit_selector="button[type='submit']"
)
```

#### Step 6.3: Run Agent

```python
# Execute task
result = await agent.run_episode(env)

print(f"Success: {result['success']}")
print(f"Steps taken: {result['steps']}")
print(f"Total reward: {result['total_reward']}")

# Save episode for analysis
agent.save_episode("results/episode_log.json")

await browser.close()
```

---

## Data Flow Diagram

```
┌──────────────────────────────────────────────────────────────┐
│ PHASE 1: OFFLINE DATA COLLECTION                             │
└──────────────────────────────────────────────────────────────┘

Explorer (LLM)
    │
    │ Generates raw logs
    ▼
data/raw/<explorer>/
    └── task_log.json (explorer format)


┌──────────────────────────────────────────────────────────────┐
│ PHASE 2: DATA CONVERSION                                     │
└──────────────────────────────────────────────────────────────┘

Adapter
    │
    │ Converts to unified format
    ▼
data/trajectories/<explorer>/
    └── task_traj_0.json (unified format)


┌──────────────────────────────────────────────────────────────┐
│ PHASE 3: DATA CLEANING                                       │
└──────────────────────────────────────────────────────────────┘

Cleaner
    │
    │ Validates and cleans
    ▼
data/cleaned/
    └── task_traj_0.json (validated)


┌──────────────────────────────────────────────────────────────┐
│ PHASE 4: TRAINING                                            │
└──────────────────────────────────────────────────────────────┘

Trainer
    │
    │ Trains SLM
    ▼
checkpoints/
    └── model_epoch_N.pt


┌──────────────────────────────────────────────────────────────┐
│ PHASE 5: EVALUATION                                          │
└──────────────────────────────────────────────────────────────┘

Evaluator
    │
    │ Tests agent
    ▼
results/
    └── eval_results.json


┌──────────────────────────────────────────────────────────────┐
│ PHASE 6: PRODUCTION                                          │
└──────────────────────────────────────────────────────────────┘

Agent (SLM)
    │
    │ Performs tasks
    ▼
Real-world actions
```

## Key Principles Reinforced

### ✅ DO

1. **Convert all explorer data through adapters**
2. **Use unified trajectory format for training**
3. **Keep explorers as black boxes**
4. **Train only on cleaned trajectories**
5. **Use SLM for production (fast, efficient)**

### ❌ DON'T

1. **Import explorer code in core agent**
2. **Import explorer code in training**
3. **Train on raw explorer logs**
4. **Use LLMs in production**
5. **Leak explorer-specific concepts into core system**

## Iteration and Improvement

### Continuous Improvement Loop

```
1. Collect more data with explorers
2. Convert → Clean → Add to training set
3. Retrain model
4. Evaluate performance
5. Deploy improved model
6. Repeat
```

### Active Learning

```
1. Agent encounters difficult situation
2. Log the state/task
3. Send to explorer for demonstration
4. Convert demonstration to trajectory
5. Add to training data
6. Retrain
```

## Troubleshooting

### No training data?

Check each step:
```bash
# 1. Raw logs exist?
ls data/raw/webtactix/

# 2. Converted trajectories?
ls data/trajectories/webtactix/

# 3. Cleaned trajectories?
ls data/cleaned/
```

### Training slow?

- Use smaller model: `--model distilgpt2`
- Reduce batch size: `--batch-size 16`
- Use GPU: `--device cuda`

### Agent fails tasks?

- Collect more training data
- Train for more epochs
- Check if task is in training distribution
- Use exploration policy for debugging

## Next Steps

1. **Scale up**: Collect more diverse training data
2. **Multi-task**: Train on multiple task types
3. **Fine-tune**: Specialize for specific domains
4. **Monitor**: Track production performance
5. **Iterate**: Continuously improve with new data

## Summary

The workflow ensures:
- ✅ Clean separation between explorers and core agent
- ✅ Consistent data format via adapters
- ✅ Project-owned action space and state representation
- ✅ Efficient production inference with SLM
- ✅ Scalable data collection and training pipeline
