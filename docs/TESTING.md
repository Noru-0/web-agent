# Testing the New Implementation

Quick guide to test the new LLM-based task synthesis (Phase 2 & 3).

## Setup

```bash
# 1. Install new dependency
pip install anthropic

# 2. Add API key to .env
echo "ANTHROPIC_API_KEY=your_anthropic_key_here" >> .env

# Or add to .env file manually:
# ANTHROPIC_API_KEY=sk-ant-...
```

## Test Phase 1 + 2 (Exploration + Task Synthesis)

### Test 1: Basic Usage with LLM Synthesis

```bash
# Run exploration with NEW LLM-based synthesis
python run_exploration.py \
    --url http://localhost:9999 \
    --use-llm-synthesis \
    --verbose

# Check outputs:
# - data/raw/localhost_9999/         (Phase 1: exploration data)
# - data/tasks/localhost_9999/tasks_llm.json      (Phase 2: synthesized tasks)
# - data/tasks/localhost_9999/tasks_llm_summary.txt  (readable summary)
```

### Test 2: Compare OLD vs NEW

```bash
# Run with OLD deterministic method
python run_exploration.py --url http://localhost:9999

# Run with NEW LLM method
python run_exploration.py --url http://localhost:9999 --use-llm-synthesis

# Compare outputs:
cat data/tasks/localhost_9999/tasks_summary.txt      # OLD method
cat data/tasks/localhost_9999/tasks_llm_summary.txt  # NEW method

# Which one looks more realistic?
```

### Test 3: Different LLM Provider

```bash
# Use OpenAI instead of Anthropic (if you have GPT-4 access)
export OPENAI_API_KEY=your_key

python run_exploration.py \
    --url http://localhost:9999 \
    --use-llm-synthesis \
    --llm-provider openai
```

### Test 4: Skip Task Synthesis

```bash
# Only run Phase 1 (exploration)
python run_exploration.py \
    --url http://localhost:9999 \
    --skip-task-synthesis
```

## Test Phase 3 (Task Validation) - Manual

Phase 3 validation is not yet integrated into CLI but you can test it programmatically:

```python
# test_phase3.py
import asyncio
import json
from pathlib import Path
from exploration import TaskValidator, SynthesizedTask, TaskStep
from envs.generic_env import GenericWebEnv

async def test_validation():
    # Load tasks from Phase 2
    tasks_file = Path("data/tasks/localhost_9999/tasks_llm.json")
    with open(tasks_file) as f:
        data = json.load(f)

    # Convert to SynthesizedTask objects
    tasks = []
    for task_data in data["tasks"]:
        steps = [
            TaskStep(i+1, step)
            for i, step in enumerate(task_data["steps"])
        ]
        task = SynthesizedTask(
            task_id=task_data["task_id"],
            name=task_data["name"],
            description=task_data["description"],
            steps=steps,
            category=task_data.get("category", "general")
        )
        tasks.append(task)

    # Create environment
    env = GenericWebEnv(start_url="http://localhost:9999", headless=True)

    # Validate tasks
    validator = TaskValidator(env)
    report = await validator.validate_tasks(
        tasks,
        save_validated=True,
        output_dir=Path("data/validated/localhost_9999")
    )

    print(f"\n✅ Validation complete!")
    print(f"Success rate: {report.success_rate*100:.1f}%")
    print(f"Validated: {report.validated_tasks}/{report.total_tasks}")

    await env.close()

# Run
asyncio.run(test_validation())
```

Run it:
```bash
python test_phase3.py

# Check outputs:
# - data/validated/localhost_9999/validated_tasks.json
# - data/validated/localhost_9999/validation_report.json
# - data/validated/localhost_9999/validation_summary.txt
```

## Expected Results

### Phase 2 Output Example

`data/tasks/localhost_9999/tasks_llm_summary.txt`:
```
LLM-BASED TASK SYNTHESIS SUMMARY
================================

Total Tasks: 8
LLM Provider: anthropic
Model: claude-3-5-sonnet-20241022

Categories: search, browse, account, purchase

1. Search for products
   Category: search
   Description: User wants to find products by searching
   Steps (4):
      1. Navigate to homepage
      2. Enter search query
      3. Click search button
      4. View results
...
```

### Phase 3 Output Example (once fully implemented)

`data/validated/localhost_9999/validation_summary.txt`:
```
TASK VALIDATION SUMMARY (Phase 3)
==================================

Total tasks evaluated: 8
✅ Validated (passed): 6 (75.0%)
❌ Failed: 2 (25.0%)

✅ VALIDATED TASKS (6):
1. Search for products
   Steps: 4/4
   Execution time: 8.5s
...

❌ FAILED TASKS (2):
1. Complete checkout
   Reason: Stuck at step 3: state not changing
   Steps completed: 2/5
...
```

## Troubleshooting

### "anthropic module not found"
```bash
pip install anthropic
```

### "API key not found in environment"
```bash
# Add to .env file:
ANTHROPIC_API_KEY=sk-ant-api-...
```

### "LLM call failed"
- Check internet connection
- Verify API key is valid
- Check API quota/billing

### "No tasks generated"
- Make sure Phase 1 completed successfully
- Check exploration data exists in `data/raw/`
- Try with more screens: `--max-screens 100`

## What to Check

1. **Task quality**: Do generated tasks make sense for the website?
2. **Task completeness**: Are all major user flows covered?
3. **Task steps**: Are steps clear and actionable?
4. **Comparison**: Is LLM method better than algorithmic method?

## Report Issues

If you find issues, document:
1. Command used
2. Error message (if any)
3. Expected vs actual output
4. Environment (OS, Python version, etc.)

## Next Steps

After testing:
1. Review generated tasks - are they good quality?
2. Compare OLD vs NEW method - which is better?
3. Provide feedback for improvements
4. Help complete Phase 3 validation implementation

---

**Note:** Phase 3 validation currently uses placeholder execution.
Full implementation with real LLM agent coming soon!
