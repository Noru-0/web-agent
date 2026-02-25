# Workflows

This directory contains workflow scripts and the EXPLORE pipeline orchestration.

## Purpose

Workflows implement and test specific stages of the research pipeline:
- **EXPLORE**: Orchestration of systematic web exploration  
- **Testing**: Validation scripts for isolated component testing

The EXPLORE workflow coordinates exploration using domain logic from the `exploration/` module.

## Separation of Concerns

- **exploration/**: Domain logic (Screen, ActionSemantic, analysis, deduplication, storage)
- **workflows/**: Orchestration logic (BFS loop, budget control, CLI entrypoints)

## Available Workflows

### EXPLORE Pipeline

**Location:** `workflows/explore.py` and related modules

**Purpose:** 
Performs controlled web exploration to collect screens and semantic transitions for later task synthesis and SLM training.

**Key Features:**
- LLM-based screen understanding and action listing
- BFS-style one-step exploration (no multi-step planning)
- Screen deduplication based on semantic similarity
- Explorer-agnostic design via adapters
- JSONL storage for screens and transitions

**Module Structure:**
- `exploration/*` - Domain logic (data models, analysis, dedup, storage)
- `workflows/explore.py` - Orchestration (BFS loop, budget control)
- `workflows/exploration_adapter.py` - Action execution bridge

**Documentation:** See [EXPLORE_README.md](EXPLORE_README.md) for complete details

**Quick Start:**
```bash
# Verify installation
python workflows/verify_explore.py

# Run exploration demo
python examples/run_exploration.py
```

**Requirements:**
- `OPENAI_API_KEY` environment variable
- Dependencies: `openai`, `beautifulsoup4`, `playwright`

**Output:**
- `data/raw/<explorer_name>/screens.jsonl` - Discovered screens
- `data/raw/<explorer_name>/transitions.jsonl` - Semantic transitions
- `data/raw/<explorer_name>/metadata.json` - Exploration summary

---

## Available Tests

### `test_env.py`

Tests the browser and environment layer.

**What it validates:**
- Browser session can open real webpages
- Actions execute correctly
- Observations are returned properly

**Requirements:**
- Playwright installed: `pip install playwright`
- Chromium installed: `playwright install chromium`

**Usage:**
```bash
python workflows/test_env.py
```

**What you'll see:**
- Browser window opens (non-headless)
- Navigates to example.com
- Clicks the "More information" link
- Prints observations at each step

**Success criteria:**
- ✓ Browser opens
- ✓ One action executes
- ✓ Observation printed

## Architecture Note

These tests do NOT require:
- ❌ Explorers
- ❌ LLMs
- ❌ Training code
- ❌ Trained models

They test only the minimal browser and environment abstractions.
