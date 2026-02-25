# Agents

This directory contains the **production runtime agent** that runs in inference mode.

## Architecture

```
agents/
├── base_agent.py      # Abstract interface (BaseAgent)
├── simple_agent.py    # Rule-based implementation (SimpleAgent, RandomAgent)
└── runner.py          # Episode controller (AgentRunner)
```

## Components

### BaseAgent (base_agent.py)

Abstract interface that all agents must implement:

```python
class BaseAgent(ABC):
    def reset(self):
        """Called at the start of each episode"""
        pass
    
    def act(self, observation: Dict[str, Any]) -> Action:
        """Select action given observation"""
        pass
```

**Key properties:**
- Minimal interface (2 methods)
- Stateless from external perspective
- No dependencies on explorers or training
- Designed for easy SLM replacement

### SimpleAgent (simple_agent.py)

Rule-based agent using fixed heuristics:

```python
agent = SimpleAgent(click_first=True)
agent.reset()
action = agent.act(observation)
```

**Strategies:**
- `click_first=True`: Always click first clickable element
- `click_first=False`: Cycle through clickable elements

**Also includes:**
- `RandomAgent`: Takes random valid actions
- `create_simple_agent()`: Factory function

### AgentRunner (runner.py)

Orchestrates agent-environment interaction:

```python
runner = AgentRunner(agent, env, max_steps=10)
summary = await runner.run_episode()
```

**Responsibilities:**
- Reset agent and environment
- Run episode loop (observe → act → step)
- Track episode statistics
- Return summary with actions, observations, completion status

**Key feature:** The runner has NO agent logic and NO environment logic. It only coordinates.

## Usage

### Basic Usage

```python
from agents.simple_agent import create_simple_agent
from agents.runner import run_single_episode
from envs.demo_site.env import DemoWebEnv

# Create components
env = DemoWebEnv(headless=False)
agent = create_simple_agent(strategy="click_first")

# Run episode
summary = await run_single_episode(agent, env, max_steps=5, verbose=True)

# Check results
print(f"Steps taken: {summary.steps}")
print(f"Completed: {summary.completed}")

await env.close()
```

### Command Line

```bash
# Run with default settings
python examples/run_agent.py

# Run in headless mode
python examples/run_agent.py --headless

# Customize steps and strategy
python examples/run_agent.py --steps 10 --agent cycle
```

## Design Principles

### 1. Strict Architectural Boundaries

The agent system depends ONLY on:
- `envs/` (WebEnv interface)
- `schema.py` (Action, Observation types)

It must NOT import:
- `explorers/` (offline data collection)
- `adapters/` (data conversion)
- `training/` (model training)
- LLM APIs

### 2. Stable Interface

The `BaseAgent` interface is designed to remain stable so that:
- `SimpleAgent` can be replaced with `SLMAgent` later
- Environment code doesn't need to change
- Runner code doesn't need to change

### 3. Production Focus

These agents are designed for production inference:
- Fast execution (no learning during runtime)
- Minimal state
- Clear error handling
- No trajectory storage (that's for training)

### 4. Separation of Concerns

```
┌─────────────────────────────────────────────┐
│              AgentRunner                    │
│  (coordinates, no logic)                    │
└─────────────┬───────────────────┬───────────┘
              │                   │
     ┌────────▼────────┐  ┌──────▼──────────┐
     │   BaseAgent     │  │    WebEnv       │
     │  (act logic)    │  │  (step logic)   │
     └─────────────────┘  └─────────────────┘
```

Each component has a single responsibility and knows nothing about the others' internals.

## Replacing SimpleAgent with SLMAgent

When the SLM is trained, you can replace the agent with zero code changes:

```python
# Before (simple agent)
from agents.simple_agent import SimpleAgent
agent = SimpleAgent()

# After (SLM agent)
from agents.slm_agent import SLMAgent
agent = SLMAgent(model_path="checkpoints/slm-v1.pt")

# Runner code stays exactly the same
runner = AgentRunner(agent, env)
summary = await runner.run_episode()
```

This is possible because both implement the same `BaseAgent` interface.

## Testing

The simple agent serves as a baseline for:
- Validating environment correctness
- Comparing against trained agents
- Debugging episode loops
- Integration testing

To test the agent system:

```bash
python examples/run_agent.py
```

You should see:
1. Browser opens and loads example.com
2. Agent observes page
3. Agent clicks elements
4. Episode completes after N steps
5. Summary printed with statistics

## SLMAgent (slm_agent.py)

The **SLMAgent** uses trained model checkpoints for production inference.

### Key Features

1. **Checkpoint Loading**: Loads trained model from disk
2. **Encoder Initialization**: Sets up encoders matching training configuration
3. **Inference Only**: No training logic, `model.eval()`, `torch.no_grad()`
4. **Safe Decoding**: Fallback to WAIT action for invalid predictions
5. **BaseAgent Interface**: Drop-in replacement for SimpleAgent

### Usage

```python
from agents.slm_agent import SLMAgent

# Load from checkpoint
agent = SLMAgent.from_checkpoint(
    checkpoint_path="checkpoints/best_model.pt",
    device="cpu",           # or "cuda"
    temperature=0.0         # 0.0 = greedy/deterministic
)

# Use exactly like SimpleAgent
agent.reset()
action = agent.act(observation)
```

### Implementation

```python
class SLMAgent(BaseAgent):
    def __init__(
        self,
        model: WebAgentPolicy,
        state_encoder: StateEncoder,
        action_encoder: ActionEncoder,
        device: str = "cpu",
        temperature: float = 0.0
    ):
        # Initialize with trained model and encoders
        self.model = model.to(device).eval()
        self.state_encoder = state_encoder
        self.action_encoder = action_encoder
        
    def reset(self):
        # Clear any cached state
        pass
    
    def act(self, observation: Dict[str, Any]) -> Action:
        # 1. Convert observation to State
        state = State(
            url=observation["url"],
            html=observation["html"],
            interactive_elements=observation["interactive_elements"]
        )
        
        # 2. Encode state (matching training)
        encoded = self.state_encoder.encode_state(state)
        
        # 3. Model inference (no gradients)
        with torch.no_grad():
            outputs = self.model.predict(
                url=encoded["url"].unsqueeze(0),
                text=encoded["text"].unsqueeze(0),
                elements=encoded["elements"].unsqueeze(0),
                element_mask=encoded["element_mask"].unsqueeze(0)
            )
        
        # 4. Decode to valid Action
        action = self._decode_action(outputs, state)
        
        return action
    
    @classmethod
    def from_checkpoint(cls, checkpoint_path, device="cpu", temperature=0.0):
        # Load checkpoint and create agent
        checkpoint = torch.load(checkpoint_path, map_location=device)
        
        # Reconstruct model from checkpoint config
        model = WebAgentPolicy(
            vocab_size=checkpoint["vocab_size"],
            num_action_types=checkpoint["num_action_types"],
            max_elements=checkpoint["max_elements"],
            embedding_dim=checkpoint["embedding_dim"],
            hidden_dim=checkpoint["hidden_dim"]
        )
        model.load_state_dict(checkpoint["model_state_dict"])
        
        # Create encoders (matching training config)
        state_encoder = StateEncoder(...)
        action_encoder = ActionEncoder(...)
        
        return cls(model, state_encoder, action_encoder, device, temperature)
```

### Design Principles

**Inference Only**:
- Model set to eval mode: `model.eval()`
- No gradients: `with torch.no_grad()`
- No training logic whatsoever

**Minimal Dependencies**:
- Imports: `schema.py`, `agents.base_agent`, `training.model`, `training.collate`, `torch`
- Never imports: `explorers`, `adapters`, `training.dataset/trainer/eval`, `envs`, `browser`

**Safe Decoding**:
- Invalid action type → WAIT action
- Invalid target index → First element or empty string
- Malformed value → Empty string
- Never crashes on bad predictions

**Deterministic by Default**:
- `temperature=0.0` → greedy sampling (argmax)
- Same observation → same action (reproducible)
- Recommended for production

### Running End-to-End

```bash
# 1. Train model (creates checkpoint)
python training/train.py --data_dir data/trajectories --epochs 10

# 2. Run SLM agent with checkpoint
python examples/run_slm_agent.py --checkpoint checkpoints/best_model.pt

# 3. With options
python examples/run_slm_agent.py \
    --checkpoint checkpoints/best_model.pt \
    --device cuda \
    --temperature 0.0 \
    --max-steps 20 \
    --record trajectories/slm_run.json \
    --verbose
```

### Zero-Code Agent Swap

Because SLMAgent implements BaseAgent, you can swap agents without changing any other code:

```python
# Before: Rule-based agent
agent = SimpleAgent(click_first=True)

# After: Trained SLM agent  
agent = SLMAgent.from_checkpoint("checkpoints/best_model.pt")

# Runner code identical for both
runner = AgentRunner(agent, env, max_steps=20)
summary = runner.run_episode()
```

This is the power of the stable BaseAgent interface!

### Complete System Flow

```
OFFLINE (Training):
  └─ Trajectories → Training → Checkpoint (.pt file)

ONLINE (Production):
  └─ Checkpoint → SLMAgent → AgentRunner → Environment

Data Flow:
  └─ Observation (dict) → State (dataclass) → Tensors → Model → Logits → Action (dataclass)
```

See **[examples/run_slm_agent.py](../examples/run_slm_agent.py)** for complete usage example.

## Summary

The agent system is the **production runtime** component:

- **BaseAgent**: Stable interface for all agents
- **SimpleAgent**: Rule-based baseline
- **AgentRunner**: Episode coordinator
- **Designed for SLM replacement**: Future-proof architecture

This completes the online (production) half of the system. The offline half (explorers, training) generates the model that powers the SLM agent.
