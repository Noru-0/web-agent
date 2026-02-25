# Explorers (External Tools)

This directory contains **EXTERNAL** LLM-based exploration frameworks.

⚠️ **IMPORTANT**: These are **NOT part of our codebase**. They are third-party tools we integrate with via adapters.

## Status

Current explorers:
- **AgentTrek/**: External exploration framework (optional)
- **webtactix/**: External exploration framework (optional)

These folders may be:
- Git submodules
- Symlinks to external repos
- Downloaded/cloned separately
- Completely absent (if not using those explorers)

## ⚠️ CRITICAL RULES

1. **Explorers are BLACK BOXES**: Treat these as external dependencies
2. **OPTIONAL**: Your project works without them (use exploration/exploration_bridge.py instead)
3. **NO IMPORTS**: Core agent and training code must NEVER import from here
4. **Use adapters**: All integration happens via `adapters/` (root level)
5. **Offline only**: Explorers are used offline to generate training data

## Production Exploration

For PRODUCTION exploration (not external tools):
```bash
# Use the integrated exploration system
python run_exploration.py --url https://example.com --adapter simple

# Or with LLM adapter
python run_exploration.py --url https://shop.com --adapter agenttrek
```

This uses:
- `exploration/exploration_bridge.py` (our code)
- `adapters/agenttrek_exploration_adapter.py` (our adapter)
- `envs/generic_env.py` (our environment)

NO external explorer code needed!

## Structure

```
explorers/              # EXTERNAL tools (optional)
├── webtactix/          # External: WebTactiX framework  
├── AgentTrek/          # External: AgentTrek framework
└── your_explorer/      # External: Your own explorer

adapters/               # ⚠️ ROOT level - OUR integration code
├── base_adapter.py
├── agenttrek_exploration_adapter.py   # For production exploration
├── webtactix_adapter.py               # For offline data conversion
└── agenttrek_adapter.py               # For offline data conversion
```

## When to Use External Explorers

Use external tools in explorers/ if:
- You have existing exploration data from those frameworks
- You want to convert their outputs to our format
- You're comparing different exploration strategies

DON'T need them if:
- You just want to explore websites (use `run_exploration.py`)
- You're training/running agents (use trajectories)
- You're developing the core system

## Adding a New Explorer

1. Place external tool in `explorers/<name>/` (optional)
2. Create adapter in `adapters/<name>_adapter.py` (root level)
3. Implement `ExplorerAdapter` interface
4. Test conversion: raw logs → unified trajectories

## Example: Converting External Data

```bash
# If you have WebTactiX logs
python scripts/convert_explorer_output.py \
    --adapter webtactix \
    --input explorers/webtactix/logs/ \
    --output data/trajectories/offline/
```

The explorer code itself may use LLMs, complex frameworks, or any dependencies.
The core agent will never see or depend on any of this.
