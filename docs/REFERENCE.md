# Quick Reference Guide

> **Comprehensive reference for commands, APIs, and common patterns**

---

## Table of Contents

1. [Commands](#commands)
2. [Data Structures](#data-structures)
3. [API Reference](#api-reference)
4. [Common Patterns](#common-patterns)

---

## Commands

### System Verification

```bash
# Verify full system
python scripts/verify_system.py

# Verify exploration pipeline
python workflows/verify_explore.py
```

### Exploration

```bash
# Basic exploration (uses .env config)
python run_exploration.py --url https://example.com

# With options
python run_exploration.py \
    --url https://example.com \
    --max-screens 50 \
    --max-transitions 200 \
    --no-headless \
    --max-actions-per-screen 10

# AgentTrek exploration (set EXPLORER_PROVIDER=agenttrek in .env)
python run_exploration.py --url https://example.com
```

### Data Processing

```bash
# Convert explorer data
python scripts/convert_data.py \
    --adapter agenttrek \
    --input data/raw/agenttrek/episode.json \
    --output data/trajectories/offline/

# Convert directory
python scripts/convert_explorer_output.py \
    --explorer agenttrek \
    --input-dir data/raw/agenttrek/ \
    --output-dir data/trajectories/offline/

# Clean data
python scripts/clean_data.py \
    --input data/trajectories/offline/ \
    --output data/cleaned/ \
    --min-steps 3 \
    --max-steps 50

# Check for duplicates
python scripts/check_duplicates.py

# Deduplicate data
python scripts/deduplicate_data.py --backup
```

### Training

```bash
# Train model
python training/train.py \
    --data-dir data/cleaned/ \
    --model-name model-v1 \
    --epochs 10 \
    --batch-size 32

# Evaluate model
python training/evaluate.py \
    --model checkpoints/model-v1/ \
    --test-data data/cleaned/test/

# Run agent
python agent/runner.py \
    --agent slm \
    --url https://example.com \
    --task "Search for shoes"
```

---

## Data Structures

### Semantic/Executable Separation

#### ActionSemantic (What to do)

```python
from exploration.schema import ActionSemantic

action = ActionSemantic(
    action_id="abc123",
    intent="search",           # What intent
    object="products",         # What object
    context="via search box",  # What context
    description="search products via search box",
    confidence=0.85
)
```

**✅ Contains:** Intent, object, context, description  
**❌ NEVER contains:** Selectors, element types, coordinates

#### ActionExecutable (How to do it)

```python
from exploration.executable_schema import ActionExecutable, ActionType

executable = ActionExecutable(
    action_id="abc123",        # Same ID links them
    type=ActionType.TYPE,
    selector="input[name='q']",
    value="shoes",
    element_text="Search",
    element_type="input",
    confidence=1.0
)
```

**✅ Contains:** Type, selector, value, element properties  
**❌ NEVER contains:** Intent, object, description

#### Action (Storage bundle)

```python
from exploration.schema import Action

action = Action(
    action_id="abc123",
    semantic=ActionSemantic(...),    # Reasoning info
    executable=ActionExecutable(...), # Execution info
    source_screen_id="screen_xyz",
    confidence=0.85
)
```

**✅ Use for:** Storage, retrieval, linking  
**❌ Don't use for:** Passing to agents, LLM prompts

### Storage Structure

```
data/raw/{explorer_name}/
├── screens.jsonl         # Screen info (NO action data)
├── actions.jsonl         # Actions (single source of truth)
├── transitions.jsonl     # Transitions (action_id references)
└── metadata.json         # Summary with separation_valid flag
```

#### screens.jsonl

```json
{
  "screen_id": "abc123",
  "url": "http://example.com",
  "dom_snapshot": "...",
  "visible_text": "...",
  "semantic_summary": "Search page with product listings",
  "screen_type": "search_results",
  "meta": {
    "action_ids": ["action1", "action2"]  // Only IDs, not full actions
  }
}
```

#### actions.jsonl

```json
{
  "action_id": "action1",
  "semantic": {
    "intent": "search",
    "object": "products",
    "context": "via search box",
    "description": "search products",
    "confidence": 0.9
  },
  "executable": {
    "type": "type",
    "selector": "input[name='q']",
    "value": "shoes",
    "confidence": 1.0
  },
  "source_screen_id": "abc123",
  "confidence": 0.9
}
```

#### transitions.jsonl

```json
{
  "transition_id": "trans123",
  "from_screen_id": "screen1",
  "action_id": "action1",     // Only ID reference, not full action
  "to_screen_id": "screen2",
  "success": true,
  "timestamp": "2026-02-11T10:00:00"
}
```

---

## API Reference

### Exploration

```python
from workflows.explore import explore_website
from envs.generic_env import GenericWebEnv

# Create environment
env = GenericWebEnv(
    start_url="https://example.com",
    headless=True,
    max_steps=100
)

# Run exploration
result = await explore_website(
    env=env,
    start_url="https://example.com",
    max_screens=50,
    max_transitions=200,
    max_actions_per_screen=10
)

# Access results
print(f"Screens: {result.get_unique_screen_count()}")
print(f"Actions: {result.get_action_count()}")
print(f"Transitions: {result.get_transition_count()}")
```

### Explorer Adapters

```python
from exploration.exploration_bridge import get_exploration_adapter

# Get adapter by name
adapter = get_exploration_adapter("agenttrek")

# Execute semantic action
success = await adapter.execute_action(action_semantic, env)
```

### Storage

```python
from exploration.storage import ExplorationStorage

# Create storage
storage = ExplorationStorage("my_explorer", auto_clean=True)

# Save individual items
storage.save_screen(screen)
storage.save_action(action)
storage.save_transition(transition)

# Save complete result (only saves transitions + metadata)
storage.save_exploration_result(result)

# Load data
screens = storage.load_screens()
actions = storage.load_actions()
transitions = storage.load_transitions()
```

### Screen Analysis

```python
from exploration.analyzer import ScreenAnalyzer

analyzer = ScreenAnalyzer()

# Analyze screen
semantic_summary, screen_type, action_semantics = analyzer.analyze_screen(
    url="https://example.com",
    dom_snapshot=html,
    visible_text=text
)

# action_semantics is List[ActionSemantic] with optional hints
```

---

## Common Patterns

### ✅ Correct Patterns

#### 1. Create Semantic-Only Action

```python
from exploration.schema import ActionSemantic

action = ActionSemantic(
    intent="view",
    object="product details",
    description="view product details",
    confidence=0.9
)
```

#### 2. Pass Only Semantic to Explorer

```python
# CORRECT: Pass only semantic
success = await explorer.execute_action(action.semantic, env)

# CORRECT: Or pass ActionSemantic directly
success = await explorer.execute_action(action_semantic, env)
```

#### 3. Reference Actions by ID

```python
# In Screen
screen.meta = {
    "action_ids": ["action1", "action2"]  # Only IDs
}

# In Transition
transition = Transition(
    from_screen_id="screen1",
    action_id="action1",  # Only ID
    to_screen_id="screen2"
)

# Retrieve full action later
action = result.actions[action_id]
```

#### 4. Store Actions Separately

```python
# Save action to actions.jsonl
storage.save_action(action)

# Screen only references action IDs
screen.meta["action_ids"].append(action.action_id)
storage.save_screen(screen)
```

### ❌ Incorrect Patterns

#### 1. Don't Embed Actions in Screens

```python
# ❌ WRONG: Embedding full actions
screen.meta = {
    "actions": [action.to_dict(), ...]  # NO!
}

# ✅ CORRECT: Only references
screen.meta = {
    "action_ids": ["action1", "action2"]
}
```

#### 2. Don't Pass Executable to Explorer

```python
# ❌ WRONG: Passing executable
await explorer.execute_action(action.executable, env)

# ❌ WRONG: Passing full Action
await explorer.execute_action(action, env)

# ✅ CORRECT: Only semantic
await explorer.execute_action(action.semantic, env)
```

#### 3. Don't Mix Semantic and Executable

```python
# ❌ WRONG: Selector in semantic
action = ActionSemantic(
    intent="click",
    object="button#submit",  # NO! This is executable detail
    description="click button"
)

# ✅ CORRECT: Only semantic info
action = ActionSemantic(
    intent="click",
    object="submit button",
    description="click submit button"
)
```

---

## Environment Variables

```bash
# .env configuration

# Explorer Settings
EXPLORER_PROVIDER=agenttrek         # or "simple"
EXPLORER_MAX_STEPS=50
EXPLORER_MODEL=meta-llama/Llama-3.1-8B-Instruct
EXPLORER_BASE_URL=https://router.huggingface.co/v1
EXPLORER_TEMPERATURE=0.2

# API Keys
HUGGINGFACE_API_KEY=hf_xxx
OPENAI_API_KEY=sk-xxx

# Browser Settings
BROWSER_HEADLESS=true
BROWSER_TIMEOUT=30000

# Agent Settings
AGENT_TYPE=slm
AGENT_MODEL_PATH=checkpoints/model-v1/
```

---

## Validation

### Check Data Separation

```python
from exploration.validation import validate_separation

# Validate single action
is_valid, errors = validate_separation(action)

# Validate exploration result
is_valid = result.validate_separation()
```

### Metadata Check

```json
{
  "separation_valid": true,  // ← Check this flag
  "unique_screens": 10,
  "actions": 25,
  "transitions": 30
}
```

---

## See Also

- [Architecture](ARCHITECTURE.md) - System architecture and design principles
- [Workflow](WORKFLOW.md) - Complete development workflow  
- [Phase 3 Workflow](PHASE3_WORKFLOW.md) - Task synthesis guide
- [Quickstart](QUICKSTART.md) - Getting started guide
- [README](README.md) - Documentation index

---

**For more detailed examples, see:**
- `exploration/` - Core exploration logic
- `adapters/` - Explorer adapter implementations
- `tests/` - Test examples
