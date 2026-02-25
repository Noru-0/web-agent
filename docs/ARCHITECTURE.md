# Architecture Overview

This document provides a detailed overview of the web agent system architecture.

## Core Principles

1. **Separation of Concerns**: Explorers (LLM-based) are completely separate from the production agent (SLM-based)
2. **Data Flow Abstraction**: All explorer outputs flow through adapters into a unified format
3. **Project-Owned Types**: Action space and state representation are defined by THIS project
4. **No Leakage**: Core agent and training code NEVER import from explorers/

## System Components

### 1. Explorers (Offline Data Collection)

```
explorers/
├── webtactix/        # External LLM agent (black box)
├── agenttrek/        # External LLM agent (black box)
└── adapters/         # Conversion layer
    ├── base.py
    ├── webtactix_adapter.py
    └── agenttrek_adapter.py
```

**Purpose**: Generate training data offline using LLM-based agents

**Key Points**:
- Explorers are treated as black boxes
- Can use any LLM (GPT-4, Claude, etc.)
- Generate logs in their own format
- NEVER imported by core agent or training code

### 2. Adapter Layer

**Purpose**: Convert explorer-specific logs → unified trajectories

**Interface**: `ExplorerAdapter` base class

**Key Methods**:
- `convert_log_file()`: Convert single log file
- `parse_action()`: Explorer action → unified Action
- `parse_state()`: Explorer state → unified State

### 3. Data Pipeline

```
data/
├── raw/              # Explorer-specific logs
│   ├── webtactix/
│   └── agenttrek/
├── cleaned/          # Validated trajectories
└── trajectories/     # Final training data
    ├── webtactix/
    └── agenttrek/
```

**Flow**:
1. Explorer → `data/raw/<explorer>/` (explorer format)
2. Adapter → `data/trajectories/<explorer>/` (unified format)
3. Cleaning → `data/cleaned/` (validated)
4. Training uses `data/cleaned/`

### 4. Schema (Unified Format)

**Central Schema** (`schema.py`):
- `State`: Browser state representation
- `Action`: Action representation (CLICK, TYPE, etc.)
- `TrajectoryStep`: Single state-action-next_state transition
- `Trajectory`: Complete episode

**Why Important**:
- Single source of truth for data format
- All training data must conform to this schema
- Enforces consistency across explorers

### 5. Browser Layer

```
browser/
├── controller.py     # Browser automation (Playwright)
└── state.py          # State extraction
```

**Purpose**: Low-level browser interactions

**Used By**:
- Explorers (for data collection)
- Core agent (for production)

### 6. Observation Layer

```
observation/
├── encoder.py        # State → features
└── preprocessor.py   # HTML cleaning
```

**Purpose**: Convert raw browser state into features for the SLM

**Key Component**: `StateEncoder`
- Truncates HTML to manageable size
- Extracts interactive elements
- Optionally includes screenshots/DOM tree

### 7. Environment Layer

```
envs/
├── base_env.py       # WebEnv base class
├── generic_env.py    # Generic web environment
└── examples/         # Example environments
```

**Purpose**: Define task-specific environments

**Interface**:
- `reset()`: Initialize environment
- `step(action)`: Execute action, return (observation, done)
- `observe()`: Get current observation
- `close()`: Clean up resources

**Examples**:
- `FormFillingEnv`: Fill and submit forms
- `NavigationEnv`: Navigate to find information

### 8. Production Agents

```
agents/
├── base_agent.py     # Abstract agent interface
├── simple_agent.py   # Rule-based baseline
├── slm_agent.py      # SLM-based agent
└── runner.py         # Episode execution
```

**Purpose**: Production runtime agents

**Dependencies**: ONLY `envs/`, `browser/`, `observation/`, `training/model.py`

**Key Components**:
- `BaseAgent`: Abstract agent interface
- `SLMAgent`: Trained model-based agent
- `SimpleAgent`: Rule-based baseline for comparison

### 9. Training Pipeline

```
training/
├── train.py          # Training script
├── dataset.py        # Trajectory loader
└── evaluate.py       # Evaluation
```

**Purpose**: Train SLM on trajectories

**Input**: `data/cleaned/` (unified trajectories)

**Output**: Model checkpoints in `checkpoints/`

### 10. Scripts (Utilities)

```
scripts/
├── run_explorer.py   # Run external explorer
├── convert_data.py   # Run adapters
└── clean_data.py     # Validate trajectories
```

**Purpose**: Workflow automation

## Data Flow Diagram

```
┌─────────────────┐
│ External        │
│ Explorer (LLM)  │
│                 │
│ - WebTactiX     │
│ - AgentTrek     │
└────────┬────────┘
         │
         │ Raw logs (explorer format)
         ▼
    data/raw/
         │
         │ Adapter conversion
         ▼
┌────────────────┐
│ Adapter Layer  │
│                │
│ - Parse logs   │
│ - Convert to   │
│   unified      │
│   format       │
└────────┬───────┘
         │
         │ Unified trajectories
         ▼
data/trajectories/
         │
         │ Cleaning & validation
         ▼
  data/cleaned/
         │
         │ Training data
         ▼
┌────────────────┐
│ Training       │
│                │
│ - Load         │
│   trajectories │
│ - Train SLM    │
└────────┬───────┘
         │
         │ Model checkpoints
         ▼
   checkpoints/
         │
         │ Load for inference
         ▼
┌────────────────┐
│ Core SLM Agent │
│ (Production)   │
│                │
│ - No LLM       │
│ - Fast         │
│ - Deployable   │
└────────────────┘
```

## Workflow

### Phase 1: Data Collection (Offline)

1. Run explorer:
   ```bash
   python scripts/run_explorer.py --explorer webtactix --task "book flight"
   ```

2. Explorer generates logs in `data/raw/webtactix/`

### Phase 2: Data Conversion

1. Run adapter:
   ```bash
   python scripts/convert_data.py --explorer webtactix
   ```

2. Adapter converts logs to unified format in `data/trajectories/webtactix/`

### Phase 3: Data Cleaning

1. Clean and validate:
   ```bash
   python scripts/clean_data.py --input data/trajectories --output data/cleaned
   ```

2. Cleaned trajectories in `data/cleaned/`

### Phase 4: Training

1. Train SLM:
   ```bash
   python training/train.py --data-dir data/cleaned --epochs 10
   ```

2. Checkpoints saved to `checkpoints/`

### Phase 5: Production Inference

1. Run agent:
   ```bash
   python -m core.agent
   ```

2. Agent uses trained SLM for fast, production-ready inference

## Design Decisions

### Why Adapters?

- **Flexibility**: Easy to add new explorers
- **Isolation**: Explorers remain black boxes
- **Consistency**: All training data in unified format

### Why SLM for Production?

- **Speed**: Much faster than LLM
- **Cost**: Lower inference cost
- **Deployment**: Easier to deploy
- **Privacy**: Can run locally

### Why Separate Explorers?

- **Modularity**: Core agent doesn't depend on specific explorers
- **Experimentation**: Easy to try different LLM agents
- **Clean Architecture**: Clear separation of concerns

## Adding New Components

### Add a New Explorer

1. Place code in `explorers/<name>/`
2. Create adapter in `adapters/<name>_adapter.py` (root level)
3. Implement `ExplorerAdapter` interface
4. Run: `python scripts/convert_data.py --explorer <name>`

### Add a New Environment

1. Create class extending `WebEnv` in `envs/`
2. Implement: `reset()`, `step()`, `observe()`, `close()`
3. Use in agent: `agent.run_episode(env)`

### Add a New Model

1. Create class extending `TransformerSLM` in `training/model.py`
2. Implement: `forward()`, `predict()`, `load()`, `save()`
3. Use in agent: `SLMAgent(model, encoder)`

## Testing Strategy

1. **Unit Tests**: Test each component independently
2. **Integration Tests**: Test data flow (adapter → training → agent)
3. **End-to-End Tests**: Run full pipeline on sample data

## Future Enhancements

1. **Vision Support**: Add screenshot encoding for vision-language models
2. **Multi-Task Learning**: Train on diverse tasks simultaneously
3. **Curriculum Learning**: Gradually increase task difficulty
4. **Active Learning**: Have agent request more data for uncertain situations
5. **Online Fine-Tuning**: Continually improve agent from production data
