# Web Agent System

A production web agent system powered by a Small Language Model (SLM), with LLM-based exploration for offline training data generation.

> **🎯 New here?** Read [docs/OVERVIEW.md](docs/OVERVIEW.md) for a quick introduction (Vietnamese)
> **📍 Project Status**: See [docs/PROJECT_CONTEXT.md](docs/PROJECT_CONTEXT.md) for current development status, recent changes, and known issues.

## 🔥 Recent Updates (Feb 2026)

**URL-Based Storage & Automatic Task Synthesis:**
- ✅ **URL-based folders**: Each website gets unique folder (e.g., `localhost_9999`, `shop.example.com`)
- ✅ **No auto-cleanup**: Previous explorations preserved by default
- ✅ **Automatic task synthesis**: Phase 3 runs automatically after exploration
- ✅ **Domain-aware patterns**: Task synthesis supports ecommerce, news, social, banking, streaming
- ✅ **Consolidated docs**: Reduced from 18 to 6 core documentation files

**Production-Ready System:**
- ✅ **Production CLI**: `run_exploration.py` with automatic Phase 2+3 pipeline
- ✅ **Generic Environment**: `envs/generic_env.py` works with any website
- ✅ **Semantic/Executable Separation**: Strict architectural boundary
- ✅ **Structured Actions**: ActionSemantic uses `intent`/`object`/`context`/`confidence`

**Key Design Principles:**
- URL-based storage for multi-website exploration
- Automatic task synthesis pipeline (Phase 2 → Phase 3)
- Strict semantic/executable separation (NON-NEGOTIABLE)
- No data loss - all explorations preserved
- Modular, testable components

## �🚀 Quick Start

## 🚀 Quick Start

**→ [docs/QUICKSTART.md](docs/QUICKSTART.md) - Complete setup and usage guide**

```bash
# 1. Setup
pip install -r requirements.txt
playwright install chromium

# 2. Configure
cp .env.example .env
# Add HUGGINGFACE_API_KEY or OPENAI_API_KEY to .env

# 3. Verify
python scripts/verify_system.py

# 4. Run exploration (Phase 2 + Phase 3 automatic)
python run_exploration.py --url http://localhost:9999

# Output:
# → data/raw/localhost_9999/        (screens, actions, transitions)
# → data/tasks/localhost_9999/      (tasks.json, tasks_summary.txt)

# 5. Explore another website (keeps all data)
python run_exploration.py --url https://shop.example.com
# → data/raw/shop.example.com/      (new folder, no data loss!)
```

See details: **[docs/QUICKSTART.md](docs/QUICKSTART.md)**

---

## Architecture

```
External Explorer (LLM-based)
    ↓
Adapter Layer
    ↓
data/raw/ → data/cleaned/ → data/trajectories/
    ↓
SLM Training
    ↓
Core SLM Agent (Production)
```

## Core Principles

1. **Explorers are black boxes**: External exploration frameworks (webtactix, agenttrek, etc.) are NOT part of the core agent
2. **Strict separation**: Explorer code must never be imported into core agent or training code
3. **Unified trajectory format**: All explorer outputs are converted via adapters into standardized trajectories
4. **Minimal dependencies**: SLM agent only depends on: `envs/`, `browser/`, `observation/`, `data/trajectories`
5. **Project-owned abstractions**: Action space and state representation are defined by THIS project

## Directory Structure

```
web-agent/
├── .env                   # ⭐ Environment configuration (NEW - copy from .env.example)
├── .env.example           # ⭐ Example configuration template (NEW)
├── utils/                 # ⭐ Utility modules (NEW)
│   ├── __init__.py
│   └── env.py             #    - Environment config loader
├── adapters/              # ⭐ Explorer adapters (NEW - offline only)
│   ├── __init__.py        #    - Package documentation
│   ├── base_adapter.py    #    - Abstract adapter interface
│   ├── webtactix_adapter.py #  - WebTactix converter
│   ├── agenttrek_adapter.py #  - AgentTrek converter
│   └── registry.py        #    - Adapter factory
├── data/
│   ├── raw/               # Explorer-specific logs (explorer-owned format)
│   ├── cleaned/           # Cleaned but still raw data
│   ├── trajectories/      # Final training data (unified format)
│   │   ├── offline/       # ⭐ Offline: Converted explorer trajectories (NEW)
│   │   └── online/        # ⭐ Online: Production agent trajectories (NEW)
│   └── recorders/         # ⭐ Trajectory recorders (NEW)
│       └── trajectory_recorder.py  # Online trajectory recorder
├── scripts/               # ⭐ CLI tools (NEW)
│   └── convert_explorer_output.py  # Convert explorer outputs via adapters
├── agents/                # ⭐ Production runtime agents (NEW)
│   ├── base_agent.py      #    - Abstract agent interface
│   ├── simple_agent.py    #    - Rule-based baseline agent
│   ├── runner.py          #    - Episode controller
│   └── README.md          #    - Agent documentation
├── envs/                  # Website-specific environments
│   ├── base.py            # Base environment interface (legacy)
│   ├── base_env.py        # ⭐ Abstract WebEnv interface (NEW)
│   ├── demo_site/         # ⭐ Demo environment (NEW)
│   │   ├── env.py         #    - Environment implementation
│   │   ├── action_space.py #   - Fixed action definitions
│   │   └── selectors.py   #    - CSS selector mappings
│   └── examples/          # Example environments (e.g., shopping, forms)
├── browser/               # Browser interaction layer
│   ├── controller.py      # Browser automation (legacy)
│   ├── state.py           # Browser state extraction
│   └── session.py         # ⭐ Minimal browser session (NEW)
├── observation/           # State encoding and representation
│   ├── encoder.py         # State → feature encoding
│   └── preprocessor.py    # HTML/DOM preprocessing
├── training/              # SLM training pipeline
│   ├── train.py           # Training script
│   ├── dataset.py         # Trajectory dataset loader
│   └── evaluate.py        # Evaluation script
├── config/                # Configuration files
│   ├── agent.yaml         # Agent configuration
├── examples/              # ⭐ Usage examples (NEW)
│   ├── run_agent.py       #    - Run agent in production mode
│   └── __init__.py
├── workflows/             # ⭐ Validation workflows (NEW)
    ├── test_env.py        #    - Test browser & environment layer
    └── README.md          #    - Workflow documentation

    ├── run_explorer.py    # Run external explorer (offline)
    ├── convert_data.py    # Run adapters to convert data
    └── clean_data.py      # Data cleaning pipeline├── workflows/             # ⭐ Validation workflows (NEW)
    ├── test_env.py        #    - Test browser & environment layer
    └── README.md          #    - Workflow documentation```

## Trajectory Schema

All explorer outputs are converted to this unified format:

```python
{
    "state": <encoded_state>,      # State representation (project-defined)
    "action": {
        "type": "CLICK | TYPE | SCROLL | NAVIGATE",
        "target": <string>,         # Element selector/identifier
        "value": <optional string>  # For TYPE actions

```

---

## Configuration (.env)

The system uses a `.env` file for runtime configuration. This separates secrets and environment-specific settings from code.

### Setup

```bash
# Copy example configuration
cp .env.example .env

# Edit .env and add your API keys
# (See .env.example for all available options)
```

### Configuration Categories

**LLM / Explorer Configuration**:
- `OPENAI_API_KEY` - Required for OpenAI-based exploration
- `HUGGINGFACE_API_KEY` - Required for HuggingFace LLaMA models (AgentTrek)
- `EXPLORER_PROVIDER` - Explorer to use: `agenttrek`, `simple` (default: agenttrek)
- `EXPLORER_MODEL` - Model to use (default: meta-llama/Llama-3.1-8B-Instruct)
- `EXPLORER_BASE_URL` - API endpoint (default: https://api-inference.huggingface.co/v1)
- `EXPLORER_TEMPERATURE` - Model temperature (default: 0.2)
- `EXPLORER_MAX_STEPS` - Maximum exploration steps (default: 50)

**Browser / Playwright**:
- `BROWSER_HEADLESS` - Run headless (default: true)
- `BROWSER_TIMEOUT_MS` - Browser timeout (default: 30000)
- `BROWSER_VIEWPORT_WIDTH` / `HEIGHT` - Viewport size

**Training / SLM**:
- `SLM_DEVICE` - Device for training (default: cpu)
- `SLM_DTYPE` - Data type (default: float32)
- `SLM_MAX_SEQ_LEN` - Maximum sequence length (default: 2048)

**Paths**:
- `DATA_DIR`, `RAW_DATA_DIR`, `TRAJECTORY_DIR`, `CHECKPOINT_DIR`

### AgentTrek Integration

The exploration pipeline supports AgentTrek-style reasoning with HuggingFace LLaMA models:

1. Set `EXPLORER_PROVIDER=agenttrek` in `.env`
2. Configure `HUGGINGFACE_API_KEY` with your HuggingFace token
3. Choose model: `EXPLORER_MODEL=meta-llama/Llama-3.1-8B-Instruct`
4. Run exploration - adapter is automatically loaded

See **[docs/AGENTTREK_INTEGRATION.md](docs/AGENTTREK_INTEGRATION.md)** for complete guide.

### Why .env?

- **Security**: Secrets not committed to version control
- **Flexibility**: Different settings per environment (dev/staging/prod)
- **Convenience**: Override defaults without code changes
- **Optional**: System still works with sensible defaults

**Note**: `.env` is for runtime config only. Dataset schemas, adapters, and core architecture are NOT affected by `.env`.

---

## Trajectory Schema

All explorer outputs are converted to this unified format:

```python
{
    "state": <encoded_state>,      # State representation (project-defined)
    "action": {
        "type": "CLICK | TYPE | SCROLL | NAVIGATE",
        "target": <string>,         # Element selector/identifier
        "value": <optional string>  # For TYPE actions
    },
    "next_state": <encoded_state>,
    "meta": {
        "url": <string>,
        "success": <boolean>,
        "explorer": <string>        # Which explorer generated this
    }
}
```

## Quick Test

### System Verification (Static Checks - Safe & Fast)
```bash
# Verify system structure and dependencies (no side effects)
python -u scripts/verify_system.py

# Expected output: "✓ SYSTEM VERIFICATION PASSED"
# Time: ~2-5 seconds
```

**What verification does:**
- ✓ Checks if dependencies are installed
- ✓ Verifies file structure
- ✓ Validates architectural boundaries
- ✓ Tests imports

**What verification does NOT do:**
- ❌ Launch browsers
- ❌ Initialize models
- ❌ Load checkpoints
- ❌ Run agents

For actual runtime execution, see [SYSTEM_EXECUTION_GUIDE.md](SYSTEM_EXECUTION_GUIDE.md).

This verifies: dependencies, imports, boundaries, schema, and components.

### Run Simple Agent (No Training Required)
```bash
# Run rule-based agent with demo environment
python examples/run_agent.py

# With options
python examples/run_agent.py --headless --steps 10
```

This runs a complete episode: agent observes, decides, acts, repeats until done.

### Run SLM Agent (After Training)
```bash
# Run trained agent (requires checkpoint)
python examples/run_slm_agent.py --checkpoint checkpoints/best_model.pt --verbose
```

This demonstrates end-to-end trained agent inference.

## Workflow

### 1. Offline Exploration (LLM-based)
```bash
# Run external explorer (generates raw logs)
python scripts/run_explorer.py --explorer webtactix --task booking
```

### 5. Production Runtime (Simple Agent)
```bash
# Run simple rule-based agent (no training needed)
python examples/run_agent.py

# With options
python examples/run_agent.py --steps 5 --agent click_first
```

### 6. Production Inference (SLM Agent)
```bash
# Run trained SLM agent
python examples/run_slm_agent.py --checkpoint checkpoints/best_model.pt

# With GPU acceleration
python examples/run_slm_agent.py --checkpoint checkpoints/best_model.pt --device cuda

# With trajectory recording
python examples/run_slm_agent.py \
    --checkpoint checkpoints/best_model.pt \
    --record data/trajectories/online/slm_episode.json \
    --verbose

# With temperature sampling (stochastic)
python examples/run_slm_agent.py --checkpoint checkpoints/best_model.pt --temperature 0.5
```

This completes the full loop: **Trajectory → Train → Checkpoint → SLMAgent → Environment**

## Agent System

The agent system implements the **production runtime** that runs in inference mode:

### Components

- **BaseAgent**: Abstract interface (`agents/base_agent.py`)
  - `reset()`: Initialize for new episode
  - `act(observation) -> Action`: Select action given observation

- **SimpleAgent**: Rule-based baseline (`agents/simple_agent.py`)
  - Uses fixed heuristics (e.g., click first element)
  - No learning, no model required
  - Serves as baseline for comparison

- **AgentRunner**: Episode controller (`agents/runner.py`)
  - Connects agent with environment
  - Runs episode loop: observe → act → step
  - Returns episode summary with statistics

### Usage

```python
from agents.simple_agent import create_simple_agent
from agents.runner import run_single_episode
from envs.demo_site.env import DemoWebEnv

# Create components
env = DemoWebEnv(headless=False)
agent = create_simple_agent(strategy="click_first")

# Run episode
summary = await run_single_episode(agent, env, max_steps=5, verbose=True)
print(f"Steps: {summary.steps}, Completed: {summary.completed}")

await env.close()
```

### Design Principles

1. **Stable Interface**: `BaseAgent` interface allows swapping SimpleAgent for future SLMAgent
2. **Strict Dependencies**: Agents depend ONLY on `envs/` and `schema.py`
3. **No Exploration Code**: Agents never import explorers, adapters, or training
4. **Production Focus**: Fast, minimal, stateless inference

See **[agents/README.md](agents/README.md)** for detailed documentation.

## SLM Runtime Agent

The **SLMAgent** is the production runtime agent that uses trained checkpoints for inference.

### Overview

- **Input**: Trained checkpoint (`.pt` file from training pipeline)
- **Output**: Actions selected via model inference
- **Mode**: Inference only (no training, no gradients)
- **Performance**: Fast, lightweight, deterministic

### Key Features

1. **Checkpoint Loading**: Automatically loads model and configuration from `.pt` file
2. **Encoder Initialization**: Sets up encoders matching training configuration
3. **Production Inference**: `model.eval()`, `torch.no_grad()`, deterministic sampling
4. **Safe Decoding**: Fallback to WAIT action for invalid predictions
5. **BaseAgent Interface**: Drop-in replacement for SimpleAgent

### Creating an SLM Agent

```python
from agents.slm_agent import SLMAgent

# Load from checkpoint
agent = SLMAgent.from_checkpoint(
    checkpoint_path="checkpoints/best_model.pt",
    device="cpu",           # or "cuda" for GPU
    temperature=0.0         # 0.0 = greedy (deterministic)
)

# Use like any BaseAgent
observation = env.reset()
action = agent.act(observation)
```

### Running End-to-End

```bash
# 1. Train a model
python training/train.py --data_dir data/trajectories --epochs 10

# 2. Run the trained agent
python examples/run_slm_agent.py --checkpoint checkpoints/best_model.pt --verbose

# 3. (Optional) Record new trajectories
python examples/run_slm_agent.py \
    --checkpoint checkpoints/best_model.pt \
    --record data/trajectories/online/slm_run_001.json
```

### Complete System Flow

```
┌────────────────────────────────────────────────────────────────┐
│  OFFLINE PHASE                                                  │
├────────────────────────────────────────────────────────────────┤
│  1. Explorers (LLM) → Raw Logs                                 │
│  2. Adapters → Unified Trajectories (data/trajectories/offline) │
│  3. Training Pipeline → Checkpoint (checkpoints/model.pt)       │
└────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────┐
│  ONLINE PHASE (PRODUCTION)                                      │
├────────────────────────────────────────────────────────────────┤
│  4. SLMAgent loads checkpoint                                   │
│  5. AgentRunner: observation → agent.act() → environment.step() │
│  6. (Optional) TrajectoryRecorder → New trajectories            │
└────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────┐
│  FEEDBACK LOOP                                                  │
├────────────────────────────────────────────────────────────────┤
│  7. Online trajectories → Re-training → Improved checkpoint     │
└────────────────────────────────────────────────────────────────┘
```

### Design Principles

1. **Inference Only**: No training logic in runtime agent
2. **Minimal Dependencies**: Only imports: schema.py, agents.base_agent, training.model, training.collate, torch
3. **No Environment Dependencies**: Never imports: explorers, adapters, training.dataset/trainer/eval
4. **Deterministic by Default**: temperature=0.0 for reproducible behavior
5. **Safe Fallbacks**: Invalid predictions → WAIT action (never crash)

### Sampling Modes

**Greedy (Deterministic)**:
```python
agent = SLMAgent.from_checkpoint(checkpoint_path, temperature=0.0)
```
- Uses `argmax` for all predictions
- Same input → same output (reproducible)
- Recommended for production

**Stochastic (With Temperature)**:
```python
agent = SLMAgent.from_checkpoint(checkpoint_path, temperature=0.5)
```
- Samples from probability distribution
- Higher temperature = more exploration
- Useful for data augmentation

### Implementation Details

**State Encoding** (matching training):
- Character-level text encoding (vocab_size=1000)
- URL: max 128 chars
- Text: max 512 chars
- Elements: max 50 elements, 32 chars each

**Action Decoding**:
- Action type: `argmax(logits)` → ActionType enum
- Target element: Match predicted index to interactive_elements list
- Value text: Decode character sequence (for TYPE actions)

**Model Architecture** (loaded from checkpoint):
- Character embeddings
- 3 LSTM encoders (URL, text, elements)
- State fusion layer
- 3 prediction heads (action type, target, value)

See **[agents/slm_agent.py](agents/slm_agent.py)** for full implementation.

## Online Trajectory Recording

The system can record production agent runs in the unified trajectory format:

### Purpose

- **Debugging**: Understand what agents actually do
- **Analysis**: Study behavior patterns
- **Training data**: Augment offline exploration data
- **Validation**: Verify agent behaves correctly

### Usage

```python
from data.recorders.trajectory_recorder import TrajectoryRecorder
from agents.runner import run_single_episode

# Create recorder
recorder = TrajectoryRecorder(
    save_dir="data/trajectories/online",
    env_name="demo",
    agent_name="simple"
)

# Run with recording
summary = await run_single_episode(agent, env, recorder=recorder)
```

Or via command line:

```bash
# Run agent with recording
python examples/run_agent_with_recording.py

# Disable recording
python examples/run_agent_with_recording.py --no-record
```

### Online vs Offline Trajectories

**Offline** (`data/trajectories/explorers/`):
- Generated by LLM explorers (expensive, high-quality)
- Used for training the SLM
- Requires LLM API access

**Online** (`data/trajectories/online/`):
- Generated by production agents (free, real behavior)
- Used for debugging and analysis
- No LLM needed

Both use the **same unified trajectory format** from `schema.py`.

SeeExplorer Adapter Layer

The adapter layer converts external LLM explorer outputs into the unified trajectory format.

### Key Concepts

- **Explorers are black boxes**: We never modify their code
- **Adapters are the bridge**: One adapter per explorer format
- **Offline only**: Adapters have no production runtime dependencies
- **Schema compliance**: All conversions must match `schema.py`

### Available Adapters

- **WebTactix** (`webtactix`): Converts WebTactix JSON logs
- **AgentTrek** (`agenttrek`): Converts AgentTrek tool-based traces

### Converting Explorer Outputs

```bash
# Convert single file
python scripts/convert_explorer_output.py \
    --adapter webtactix \
    --input data/raw/explorer_log.json \
    --output data/trajectories/offline/traj.json

# ConADAPTERS.md](ADAPTERS.md)** - Explorer adapter layer guide (NEW)
- **[vert directory
python scripts/convert_explorer_output.py \
    --adapter agenttrek \
    --input data/raw/agenttrek/ \
    --output data/trajectories/offline/

# List available adapters
python scripts/convert_explorer_output.py --list-adapters
```

### Python API

```python
from adapters.registry import create_adapter

# Create adapter by name
adapter = create_adapter("webtactix")

# Convert file
trajectory = adapter.convert(
    input_path="data/raw/log.json",
    output_path="data/trajectories/offline/traj.json"
)

print(f"Converted {len(trajectory.steps)} steps")
```

### Creating New Adapters

1. Create `adapters/my_explorer_adapter.py`
2. Subclass `ExplorerAdapter` from `base_adapter.py`
3. Implement `load_raw()`, `to_trajectory()` methods
4. Register in `adapters/registry.py`
5. Test with sample explorer outputs

See **[ADAPTERS.md](ADAPTERS.md)** for detailed guide and examples.

## SLM Training Pipeline

The training pipeline trains a Small Language Model policy using unified trajectory data.

### Overview

- **Input**: Trajectory JSON files from `data/trajectories/online/` and `data/trajectories/offline/`
- **Output**: Trained model checkpoint (`.pt` file)
- **Constraint**: Completely offline, no environment interaction

### Training a Model

```bash
# Basic training
python training/train.py --data_dir data/trajectories --epochs 10

# Advanced training
python training/train.py \
    --data_dir data/trajectories \
    --sources online offline \
    --epochs 20 \
    --batch_size 64 \
    --lr 1e-3 \
    --output_dir my_checkpoints
```

### Evaluating a Model

```bash
# Evaluate on test data
python training/evaluate.py \
    --checkpoint checkpoints/best_model.pt \
    --data_dir data/trajectories \
    --sources offline
```

Reports action prediction accuracy, target accuracy, and per-action breakdown.

### Training Components

- **dataset.py**: Loads trajectory JSON files, flattens into (state, action) pairs
- **collate.py**: Encodes states and actions into tensors (character-level)
- **model.py**: LSTM-based policy model (action type + target + value prediction)
- **trainer.py**: Training loop, loss computation, checkpointing
- **train.py**: CLI entry point for training
- **evaluate.py**: Offline evaluation script

### Model Architecture

- Character-level embeddings (simple, no pretrained models)
- 3 LSTM encoders (URL, text, elements)
- State fusion layer
- 3 prediction heads:
  * Action type (CLICK, TYPE, SCROLL, etc.)
  * Target element (which element to interact with)
  * Value text (for TYPE actions)

### Design Principles

1. **Offline only**: No environment interaction during training
2. **Pure data transformation**: Only depends on schema.py and trajectory JSON
3. **No cross-contamination**: Never imports explorers, adapters, browser, or runtime agents
4. **Lightweight model**: Few million parameters, fast training, on-device inference
5. **Deterministic**: Fixed seeds, reproducible results
6. **Self-contained checkpoints**: Include all config needed to reconstruct model

### Using Checkpoints in Runtime

Trained checkpoints can be loaded by runtime agents for inference:

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

# Use for inference
outputs = model.predict(...)
```

See **[training/TRAINING.md](training/TRAINING.md)** for comprehensive training guide.

## Key Design Decisions

- **No leakage**: Explorers never imported into agents/training (production code)
- **Adapters as interface**: Single point of integration per explorer
- **Project-owned types**: ActionSpace and StateRepresentation defined here
- **Simple, explicit**: Prefer clarity over clever abstractions

## System Verification

**Static verification** (zero side effects, fast):

```bash
# Verify system structure and dependencies
python -u scripts/verify_system.py
```

**What this does:**
- Checks dependency installation (without importing heavy libraries)
- Verifies file structure and required components
- Validates architectural boundaries (no forbidden imports)
- Tests lightweight module imports

**What this does NOT do:**
- Launch browsers (Playwright)
- Initialize PyTorch models
- Load checkpoints
- Start environments or agents

**Time:** ~2-5 seconds (safe, no side effects)

For **runtime execution** (actually running agents), see [SYSTEM_EXECUTION_GUIDE.md](SYSTEM_EXECUTION_GUIDE.md).

**What this verifies**:
- ✓ Python version (>=3.9)
- ✓ All dependencies installed (torch, playwright, etc.)
- ✓ Core module imports work
- ✓ Architectural boundaries enforced (no forbidden imports)
- ✓ Schema definitions consistent
- ✓ Required files and directories present
- ✓ Components can be instantiated
- ✓ SLMAgent can load checkpoints (if provided)

**With checkpoint testing**:
```bash
python scripts/verify_system.py --checkpoint checkpoints/best_model.pt --verbose
```

**Exit codes**:
- `0` = All checks passed (system healthy)
- `1` = One or more checks failed (needs attention)

**When to run**:
- After initial setup
- Before training
- After making changes
- Before deployment
- As part of CI/CD pipeline

**Full execution guide**: See **[SYSTEM_EXECUTION_GUIDE.md](SYSTEM_EXECUTION_GUIDE.md)** for complete setup, testing, and troubleshooting instructions.

## Requirements

- Python 3.9+
- PyTorch (for SLM training/inference)
- Playwright/Selenium (for browser automation)
- See `requirements.txt` for full list

## Documentation

**→ See [docs/README.md](docs/README.md) for complete documentation index**

### Core Documentation

- **[docs/OVERVIEW.md](docs/OVERVIEW.md)** - 🎯 **Quick introduction for newcomers** (Vietnamese, start here!)
- **[docs/PROJECT_CONTEXT.md](docs/PROJECT_CONTEXT.md)** - 📍 **Current project status, recent changes, and active development**
- **[docs/QUICKSTART.md](docs/QUICKSTART.md)** - Complete quickstart guide (installation, exploration, training)
- **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** - System architecture and design principles
- **[docs/WORKFLOW.md](docs/WORKFLOW.md)** - Complete development workflow
- **[docs/PHASE3_WORKFLOW.md](docs/PHASE3_WORKFLOW.md)** - Task synthesis detailed guide
- **[docs/REFERENCE.md](docs/REFERENCE.md)** - API and command reference
- **[.agents/RULES.md](.agents/RULES.md)** - Agent development rules and guidelines

### Component Documentation

- **[agents/README.md](agents/README.md)** - Agent implementations
- **[training/README.md](training/README.md)** - Training pipeline reference
- **[explorers/README.md](explorers/README.md)** - Optional external exploration tools

### Quick Links

- **Setup**: [docs/QUICKSTART.md → Setup](docs/QUICKSTART.md#cấu-hình-ban-đầu)
- **Exploration**: [docs/QUICKSTART.md → Exploration](docs/QUICKSTART.md#khám-phá-website-exploration)
- **Training**: [docs/QUICKSTART.md → Training](docs/QUICKSTART.md#huấn-luyện-model)
- **Architecture**: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- **Task Synthesis**: [docs/PHASE3_WORKFLOW.md](docs/PHASE3_WORKFLOW.md)

```
web-agent
├─ adapters
│  ├─ agenttrek_adapter.py
│  ├─ base_adapter.py
│  ├─ registry.py
│  ├─ webtactix_adapter.py
│  └─ __init__.py
├─ agents
│  ├─ base_agent.py
│  ├─ README.md
│  ├─ runner.py
│  ├─ simple_agent.py
│  ├─ slm_agent.py
│  └─ __init__.py
├─ browser
│  ├─ controller.py
│  ├─ session.py
│  ├─ state.py
│  └─ __init__.py
├─ config
│  ├─ agent.yaml
│  ├─ eval.json
│  └─ training.yaml
├─ data
│  └─ recorders
│     ├─ trajectory_recorder.py
│     └─ __init__.py
├─ envs
│  ├─ base.py
│  ├─ base_env.py
│  ├─ demo_site
│  │  ├─ action_space.py
│  │  ├─ env.py
│  │  ├─ selectors.py
│  │  └─ __init__.py
│  └─ __init__.py
├─ examples
│  ├─ run_agent.py
│  ├─ run_agent_with_recording.py
│  ├─ run_exploration.py
│  ├─ run_slm_agent.py
│  └─ __init__.py
├─ exploration
│  ├─ analyzer.py
│  ├─ dedup.py
│  ├─ exploration_bridge.py
│  ├─ schema.py
│  ├─ storage.py
│  └─ __init__.py
├─ explorers
│  ├─ README.md
│  └─ __init__.py
├─ main.py
├─ observation
│  ├─ encoder.py
│  ├─ preprocessor.py
│  └─ __init__.py
├─ QUICKSTART_SLM.md
├─ README.md
├─ requirements.txt
├─ schema.py
├─ scripts
│  ├─ clean_data.py
│  ├─ convert_data.py
│  ├─ convert_explorer_output.py
│  ├─ run_explorer.py
│  └─ verify_system.py
├─ SYSTEM_EXECUTION_GUIDE.md
├─ training
│  ├─ collate.py
│  ├─ dataset.py
│  ├─ evaluate.py
│  ├─ model.py
│  ├─ prompts
│  │  └─ web_explore.txt
│  ├─ README.md
│  ├─ train.py
│  ├─ trainer.py
│  ├─ TRAINING.md
│  └─ __init__.py
├─ utils
│  ├─ env.py
│  └─ __init__.py
├─ verify_slm.py
├─ workflows
│  ├─ examples.py
│  ├─ explore.py
│  ├─ README.md
│  ├─ test_env.py
│  └─ verify_explore.py
└─ __init__.py

```
```
web-agent
├─ adapters
│  ├─ agenttrek_adapter.py
│  ├─ agenttrek_exploration_adapter.py
│  ├─ base_adapter.py
│  ├─ registry.py
│  ├─ webtactix_adapter.py
│  └─ __init__.py
├─ agents
│  ├─ base_agent.py
│  ├─ README.md
│  ├─ runner.py
│  ├─ simple_agent.py
│  ├─ slm_agent.py
│  └─ __init__.py
├─ browser
│  ├─ controller.py
│  ├─ session.py
│  ├─ state.py
│  └─ __init__.py
├─ COMMANDS.md
├─ config
│  ├─ agent.yaml
│  ├─ eval.json
│  └─ training.yaml
├─ data
│  └─ recorders
│     ├─ trajectory_recorder.py
│     └─ __init__.py
├─ docs/
│  ├─ *.md                # Comprehensive documentation
│  └─ diagrams/
├─ envs
│  ├─ base.py
│  ├─ base_env.py
│  ├─ generic_env.py      # ⭐ Production environment (NEW)
│  └─ __init__.py
├─ exploration            # ⭐ Exploration subsystem
│  ├─ analyzer/           # ⭐ Refactored to submodule (NEW)
│  │  ├─ screen_analyzer.py
│  │  └─ __init__.py
│  ├─ action_grounder.py
│  ├─ action_schema.py
│  ├─ dedup.py
│  ├─ exploration_bridge.py
│  ├─ schema.py           # ⭐ Exploration-specific models (see notes)
│  ├─ semantic_projector.py
│  ├─ storage.py
│  ├─ task_synthesis.py
│  └─ __init__.py
├─ explorers              # ⭐ External tools (OPTIONAL)
│  ├─ AgentTrek/          #    - External exploration framework
│  ├─ webtactix/          #    - External exploration framework
│  ├─ README.md
│  └─ __init__.py
├─ observation
│  ├─ encoder.py
│  ├─ preprocessor.py
│  └─ __init__.py
├─ QUICKSTART.md
├─ README.md
├─ requirements.txt
├─ run_exploration.py     # ⭐ Production CLI (NEW)
├─ schema.py              # ⭐ Runtime schema (see notes)
├─ scripts
│  ├─ clean_data.py
│  ├─ convert_data.py
│  ├─ convert_explorer_output.py
│  ├─ run_explorer.py
│  └─ verify_system.py
├─ SETUP_CHECKLIST.md
├─ training
│  ├─ collate.py
│  ├─ dataset.py
│  ├─ evaluate.py
│  ├─ model.py
│  ├─ prompts
│  │  └─ web_explore.txt
│  ├─ README.md
│  ├─ train.py
│  ├─ trainer.py
│  ├─ TRAINING.md
│  └─ __init__.py
├─ utils
│  ├─ env.py
│  └─ __init__.py
├─ verify_slm.py
├─ workflows
│  ├─ explore.py
│  ├─ README.md
│  └─ verify_explore.py
└─ __init__.py

```

**📝 Important Notes:**

**Schema Files (Avoid Confusion!):**
- **`/schema.py`** (root): Runtime execution schema
  - Used by: `agents/`, `training/`, `envs/`
  - Defines: `Action`, `ActionType`, `State`, `TrajectoryStep`
  - Purpose: What agents see/do and training data format

- **`exploration/schema.py`**: Discovery phase schema
  - Used by: `exploration/`, `workflows/`
  - Defines: `Screen`, `ScreenType`, `ActionSemantic`, `Transition`
  - Purpose: What exploration discovers (semantic level)

These serve **different purposes** and should NOT be merged. See docstrings in each file for detailed explanation.

**Refactored Components:**
- `exploration/analyzer/`: Refactored from monolithic file to submodule for better organization
- `envs/generic_env.py`: Production environment for any website
- `run_exploration.py`: CLI for production exploration

**Removed (Production-Ready):**
- `examples/`: Removed demo scripts (use `run_exploration.py` instead)
- `envs/demo_site/`: Removed demo environment (use `generic_env.py`)
- `workflows/test_env.py`: Removed demo test

```
