# Quick Start: New LLM-based Workflow

> **Updated:** March 1, 2026 - Aligned with Professor Vũ's 5-phase approach

This guide shows how to use the NEW LLM-based task synthesis and validation workflow.

---

## 🎯 The 5 Phases

```
Phase 1: Exploration      → LLM explores website, saves paths
Phase 2: Task Synthesis   → LLM reads paths, generates tasks (NEW!)
Phase 3: Task Validation  → LLM validates tasks by execution (NEW!)
Phase 4: Training         → Train SLM on validated tasks
Phase 5: Evaluation       → Test SLM performance
```

---

## 🚀 Quick Start

### Setup

```bash
# Install dependencies (includes anthropic for Claude)
pip install -r requirements.txt

# Install browser
playwright install chromium

# Set up environment variables
cp .env.example .env
# Add your API keys to .env:
#   ANTHROPIC_API_KEY=your_key_here
#   OPENAI_API_KEY=your_key_here (optional)
```

### Run Complete Pipeline (Phase 1 + 2)

```bash
# NEW: LLM-based task synthesis with Claude
python run_exploration.py \
    --url https://example.com \
    --use-llm-synthesis

# Or use OpenAI instead of Anthropic
python run_exploration.py \
    --url https://example.com \
    --use-llm-synthesis \
    --llm-provider openai
```

**Output:**
- `data/raw/{url}/` - Phase 1 exploration data
- `data/tasks/{url}/tasks_llm.json` - Phase 2 synthesized tasks
- `data/tasks/{url}/tasks_llm_summary.txt` - Human-readable summary

### Run Phase 3 (Task Validation) - Coming Soon

```bash
# Validate tasks from Phase 2
python scripts/run_task_validation.py \
    --input data/tasks/localhost_9999/tasks_llm.json \
    --output data/validated/localhost_9999/
```

**Output:**
- `data/validated/{url}/validated_tasks.json` - Clean tasks for training
- `data/validated/{url}/validation_report.json` - Validation stats
- `data/validated/{url}/validation_summary.txt` - Human-readable report

---

## 📖 Detailed Examples

### Example 1: E-commerce Site

```bash
# Explore and synthesize tasks
python run_exploration.py \
    --url https://shop.example.com \
    --use-llm-synthesis \
    --max-screens 100 \
    --verbose

# Expected tasks:
# - Search for products
# - View product details
# - Add items to cart
# - Checkout process
# etc.
```

### Example 2: News Website

```bash
python run_exploration.py \
    --url https://news.example.com \
    --use-llm-synthesis \
    --llm-provider anthropic

# Expected tasks:
# - Browse news categories
# - Read article
# - Search articles
# - Filter by date/topic
# etc.
```

### Example 3: Compare OLD vs NEW Methods

```bash
# Run with OLD deterministic method
python run_exploration.py --url https://example.com

# Run with NEW LLM method
python run_exploration.py --url https://example.com --use-llm-synthesis

# Compare outputs:
# - data/tasks/{url}/tasks.json (OLD)
# - data/tasks/{url}/tasks_llm.json (NEW)
```

---

## 🔍 Understanding the Output

### Phase 2 Output: tasks_llm.json

```json
{
  "tasks": [
    {
      "task_id": "task_1",
      "name": "Search for product",
      "description": "User wants to find a specific product by searching",
      "category": "search",
      "steps": [
        "Navigate to homepage",
        "Enter search query in search box",
        "Click search button",
        "Review search results"
      ],
      "confidence": 1.0
    }
  ],
  "metadata": {
    "total_tasks": 10,
    "synthesizer": "LLMTaskSynthesizer",
    "llm_provider": "anthropic",
    "model": "claude-3-5-sonnet-20241022"
  }
}
```

### Phase 3 Output: validation_report.json

```json
{
  "total_tasks": 10,
  "validated_tasks": 7,
  "failed_tasks": 3,
  "success_rate": 0.7,
  "validation_results": [
    {
      "task_id": "task_1",
      "task_name": "Search for product",
      "success": true,
      "steps_completed": 4,
      "total_steps": 4,
      "execution_time": 12.5
    }
  ]
}
```

---

## 🛠️ Programmatic Usage

### Python API - Phase 2 (Task Synthesis)

```python
from exploration import LLMTaskSynthesizer
from exploration.storage import ExplorationStorage
from pathlib import Path

# Load exploration data
storage = ExplorationStorage("localhost_9999")
exploration_result = storage.load_exploration_result()

# Synthesize tasks with LLM
synthesizer = LLMTaskSynthesizer(llm_provider="anthropic")
tasks = synthesizer.synthesize_tasks(exploration_result)

# Save results
output_dir = Path("data/tasks/localhost_9999")
synthesizer.save_tasks(tasks, output_dir / "tasks_llm.json")
synthesizer.save_summary(tasks, output_dir / "tasks_llm_summary.txt")

print(f"Synthesized {len(tasks)} tasks")
for task in tasks:
    print(f"  - {task.name}: {len(task.steps)} steps")
```

### Python API - Phase 3 (Task Validation)

```python
import asyncio
from exploration import TaskValidator, LLMTaskSynthesizer
from envs.generic_env import GenericWebEnv
from pathlib import Path

async def validate_tasks():
    # Load tasks from Phase 2
    synthesizer = LLMTaskSynthesizer()
    # ... load tasks ...
    
    # Create environment
    env = GenericWebEnv(start_url="https://example.com")
    
    # Validate tasks
    validator = TaskValidator(env)
    report = await validator.validate_tasks(
        tasks,
        save_validated=True,
        output_dir=Path("data/validated/example_com")
    )
    
    print(f"Validation: {report.validated_tasks}/{report.total_tasks} passed")
    
    await env.close()

# Run validation
asyncio.run(validate_tasks())
```

---

## 🎓 Key Differences: OLD vs NEW

### OLD Method (Deterministic)

❌ Problems:
- Pattern-based algorithms
- Domain-specific rules
- Over-engineered
- Not aligned with professor's vision

```bash
# OLD way (still available for backward compatibility)
python run_exploration.py --url https://example.com
# Uses deterministic TaskSynthesizer
```

### NEW Method (LLM-based)

✅ Benefits:
- LLM understands context
- More realistic tasks
- Simpler implementation
- Aligned with professor's 5-phase approach

```bash
# NEW way (recommended)
python run_exploration.py --url https://example.com --use-llm-synthesis
# Uses LLMTaskSynthesizer
```

---

## 💡 Tips & Best Practices

### 1. API Keys

Make sure you have API keys configured:

```bash
# In .env file
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
```

### 2. Cost Considerations

LLM synthesis uses API calls which cost money:
- Claude 3.5 Sonnet: ~$3 per 1M tokens
- GPT-4 Turbo: ~$10 per 1M tokens

Typical usage: ~5000-10000 tokens per synthesis = $0.01-0.10 per run

### 3. Choose Provider

- **Anthropic (Claude)**: Better at understanding web tasks, recommended
- **OpenAI (GPT-4)**: Also works well, alternative if you prefer

### 4. Debugging

Use verbose mode to see LLM interactions:

```bash
python run_exploration.py \
    --url https://example.com \
    --use-llm-synthesis \
    --verbose \
    --no-headless  # See browser
```

### 5. Validation Takes Time

Phase 3 validation executes each task, which takes time:
- Simple task: 10-30 seconds
- Complex task: 1-2 minutes
- 10 tasks: ~5-15 minutes

Be patient!

---

## 🔄 Complete Workflow

```bash
# 1. Explore website (Phase 1)
python run_exploration.py --url https://example.com --skip-task-synthesis

# 2. Synthesize tasks with LLM (Phase 2)  
python scripts/run_task_synthesis.py \
    --input data/raw/example_com \
    --output data/tasks/example_com \
    --use-llm

# 3. Validate tasks (Phase 3)
python scripts/run_task_validation.py \
    --input data/tasks/example_com/tasks_llm.json \
    --output data/validated/example_com

# 4. Train SLM (Phase 4)
python training/train.py \
    --data data/validated/example_com/validated_tasks.json

# 5. Evaluate SLM (Phase 5)
python agents/runner.py \
    --model checkpoints/model.pt \
    --url https://example.com
```

---

## 📚 References

- **Full Analysis**: [docs/FEEDBACK_ANALYSIS.md](FEEDBACK_ANALYSIS.md)
- **Implementation Checklist**: [docs/ACTION_CHECKLIST.md](ACTION_CHECKLIST.md)
- **Project Status**: [../PROJECT_CONTEXT.md](../PROJECT_CONTEXT.md)

---

## ❓ Troubleshooting

### "anthropic module not found"

```bash
pip install anthropic
```

### "API key not found"

Add to `.env`:
```
ANTHROPIC_API_KEY=your_key_here
```

### "Tasks synthesis failed"

1. Check API key is valid
2. Check internet connection
3. Try with `--verbose` to see errors
4. Try different LLM provider: `--llm-provider openai`

### "No tasks generated"

1. Make sure Phase 1 completed successfully
2. Check that exploration data exists in `data/raw/`
3. Try with more screens: `--max-screens 100`

---

**Last Updated:** March 1, 2026  
**Status:** ✅ Phase 2 & 3 implemented and ready to use!
