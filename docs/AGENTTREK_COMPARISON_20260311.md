# AgentTrek Before/After Comparison (2026-03-11)

## Scope
- Target: `http://localhost:7770`
- Adapter: `agenttrek`
- Clean rerun performed after grounding/selector policy optimization in:
  - `adapters/agenttrek_exploration_adapter.py`
- Validation benchmark: fixed `tasks_llm_10.json` (10 tasks) from baseline backup for apples-to-apples comparison.

## Commands Used (After)
- Exploration + synthesis:
  - `/home/tbkiet/miniconda3/envs/web-agent/bin/python -m scripts.run_exploration --url http://localhost:7770 --adapter agenttrek --max-screens 20 --max-transitions 80 --max-actions-per-screen 8 --use-llm-synthesis --llm-provider openai --screenshot-mode png_file --screenshot-dir data/raw/localhost_7770/screenshots_png -v`
- Validation (10-task fixed benchmark):
  - `/home/tbkiet/miniconda3/envs/web-agent/bin/python -m scripts.run_validation --tasks data/tasks/localhost_7770/tasks_llm_10.json --url http://localhost:7770 -v`

## Comparison Table

| Metric | Before | After | Delta |
|---|---:|---:|---:|
| Unique screens (metadata) | 1 | 7 | +6 |
| Actions discovered (metadata) | 3 | 11 | +8 |
| Transitions (metadata) | 0 | 6 | +6 |
| Transition records (jsonl lines) | 16 | 12 | -4 |
| Transition success | 6/16 (37.5%) | 12/12 (100.0%) | +62.5 pp |
| Transition failures | 10 | 0 | -10 |
| Validation (10 tasks) | 6/10 (60.0%) | 5/10 (50.0%) | -10.0 pp |

## Action Fail Reasons

### Transition-level fail reasons
- Before:
  - `'ActionSemantic' object has no attribute 'hints'`: 10
- After:
  - No transition failures

### Validation-level fail reasons (10-task benchmark)
- Before (4 failed):
  - `Failed at step 1: could not execute action`
  - `Failed at step 2: could not execute action`
  - `Failed at step 3: could not execute action`
- After (5 failed):
  - `Failed at step 1: could not execute action`
  - `Failed at step 2: could not execute action`
  - `Failed at step 3: could not execute action`

## Interpretation
- The optimization significantly improved **exploration execution quality** (more screens/actions/transitions, and transition failures dropped to 0).
- The **10-task validation success rate decreased** from 60% to 50%, indicating current validator outcomes are not perfectly aligned with exploration improvements and are sensitive to task phrasing/execution abstraction.
- During rerun logs, several click failures were due to non-visible text locators on product links; this suggests the next iteration should add visibility-aware selector fallback (e.g., scroll/alternate selector strategy).
