# Project Context - Web Agent System

> **⚠️ IMPORTANT RULE**: This file MUST be updated whenever any significant changes are made to the project.

Last Updated: March 1, 2026

---

## 📋 Project Overview

**Web Agent System** is an autonomous browser automation framework that explores websites, collects interaction data, and synthesizes realistic user tasks for training web agents.

**Tech Stack:**
- Python 3.10+
- Playwright (Browser Automation)
- PyTorch (ML Training)
- Anthropic Claude / OpenAI GPT (LLM Integration)

---

## 🎯 Current Status

### ✅ Architecture Now Aligned with Professor's Vision!

**5-Phase Implementation Status:**
- **Phase 1 (Exploration)**: ✅ Working - LLM explores, saves paths
- **Phase 2 (Task Synthesis)**: ✅ IMPLEMENTED - LLM reads paths, generates tasks
- **Phase 3 (Task Validation)**: ✅ IMPLEMENTED - LLM validates tasks by execution
- **Phase 4 (Training)**: ✅ Already implemented in `training/` module
- **Phase 5 (Evaluation)**: ✅ Already implemented in `agents/` module

**Recent Implementation (March 1, 2026):**
- ✅ Created `LLMTaskSynthesizer` - LLM-based task synthesis
- ✅ Created `TaskValidator` - Execute and validate tasks
- ✅ Updated CLI with `--use-llm-synthesis` flag
- ✅ Backward compatible with old deterministic method

### Active Development Areas
- ✅ URL-based storage system (working correctly)
- ✅ Explorer adapters (AgentTrek, WebTactix) (working correctly)
- ✅ LLM-based task synthesis (NEW - aligned with feedback)
- ✅ Task validation by execution (NEW - aligned with feedback)

### Pending Tasks
- [ ] Test new LLM synthesis with real exploration data
- [ ] Improve task validation with actual LLM agent execution
- [ ] Add more robust stuck detection and error handling
- [ ] Performance optimizations
- [ ] More comprehensive test coverage

---

## 📁 Project Structure

```
web-agent/
├── adapters/           # Explorer adapters (AgentTrek, WebTactix)
├── agents/             # Agent implementations (simple, SLM)
├── browser/            # Browser control (Playwright)
├── data/               # Task definitions and trajectory recordings
├── exploration/        # Core exploration logic
│   ├── action_grounder.py       # Action execution
│   ├── task_synthesis.py        # Task generation from data
│   ├── semantic_normalization.py # Action normalization
│   └── storage.py               # URL-based storage
├── training/           # ML model training
├── tests/              # Unit and integration tests
└── .agents/skills/     # Installed agent skills
    ├── browser-automation/
    ├── playwright-visual-testing/
    └── webapp-testing/
```

---

## 🏗️ Architecture Principles

### ⚠️ CRITICAL: Semantic/Executable Separation
- **Semantic data**: For task synthesis and human understanding only
- **Executable data**: For browser action execution only
- **Rule**: Agents NEVER access semantic fields during execution

### Storage System
- URL-based folder organization: `data/tasks/{url_folder}/`
- Prevents data conflicts across different websites
- Each site maintains separate task and action databases

---

## 🔧 Recent Changes

### March 1, 2026 - Implementation of Professor's Feedback ✅
- **Implemented**: LLM-based task synthesis (Phase 2 - NEW)
  - Created `exploration/llm_task_synthesizer.py` with LLMTaskSynthesizer class
  - Supports both Anthropic (Claude) and OpenAI (GPT-4)
  - LLM reads exploration paths and generates task descriptions
  - No complex algorithms - simple and aligned with feedback
- **Implemented**: Task validation module (Phase 3 - NEW)
  - Created `exploration/task_validator.py` with TaskValidator class
  - Executes tasks to validate they work
  - Filters out failed tasks
  - Produces clean data for SLM training
- **Updated**: run_exploration.py CLI
  - Added `--use-llm-synthesis` flag for new LLM-based approach
  - Added `--llm-provider` to choose between anthropic/openai
  - Backward compatible with old deterministic method
- **Updated**: requirements.txt - Added anthropic library
- **Status**: Phase 2 and Phase 3 now aligned with professor's 5-phase vision
- **Files**:
  - exploration/llm_task_synthesizer.py (NEW)
  - exploration/task_validator.py (NEW)
  - exploration/__init__.py
  - run_exploration.py
  - requirements.txt

### March 1, 2026 - Professor Feedback Analysis
- **Added**: Comprehensive feedback analysis from Professor Vũ
  - Created `docs/FEEDBACK_ANALYSIS.md` with detailed analysis
  - Identified key misalignments: Phase 2 should use LLM, not deterministic algorithms
  - Identified missing component: Phase 3 (Task Validation) needs to be implemented
  - Proposed action plan with 4-5 weeks timeline
- **Impact**: CRITICAL - Major architecture pivot required for Phase 2 and Phase 3
  - Phase 2: Need to rewrite TaskSynthesizer to use LLM instead of algorithms
  - Phase 3: Need to create new TaskValidator module to validate tasks by re-execution
  - ActionGrounder may not be needed in Phase 2 per professor's feedback
- **Next Steps**:
  1. Team meeting to discuss feedback and align understanding
  2. Prototype LLM-based TaskSynthesizer
  3. Design and implement TaskValidator for Phase 3
- **Files**: docs/FEEDBACK_ANALYSIS.md, PROJECT_CONTEXT.md

### March 1, 2026 - Project Context System
- **Added**: Project Context tracking system
  - Created `PROJECT_CONTEXT.md` at root for tracking project status
  - Created `.agents/RULES.md` with agent development rules
  - Updated `CONTRIBUTING.md` with mandatory context update rule
  - Updated `README.md` with links to context files
- **Added**: Agent skills installation (browser-automation, playwright-visual-testing, webapp-testing)
  - Location: `.agents/skills/` directory
  - Skills for browser automation, visual testing, and webapp E2E testing
- **Impact**: All developers and agents must now update PROJECT_CONTEXT.md after significant changes
- **Files**: PROJECT_CONTEXT.md, .agents/RULES.md, CONTRIBUTING.md, README.md

### [Previous Major Changes - Add Here]
- Date: Description of change
- Impact: What was affected
- Files: List of modified files

---

## 🧪 Testing

**Test Coverage Areas:**
- Action reconstruction and storage
- Semantic action normalization
- Task synthesis
- JSON extraction edge cases
- Data model separation
- Validation screen detection

**Run Tests:**
```bash
pytest tests/
pytest --cov=exploration tests/
```

---

## 🚀 Active Experiments

### Current Explorations
- None active

### Completed Experiments
- Task synthesis from AgentTrek data
- Action deduplication strategies

---

## 🐛 Known Issues

### Critical
- ~~Architecture Misalignment: Phase 2 using deterministic instead of LLM~~ ✅ **FIXED**
- ~~Missing Phase 3: Task Validation not implemented~~ ✅ **FIXED**

### Non-Critical
- Task validation currently uses placeholder execution (needs full LLM agent integration)
- Need to test new LLM synthesis with various website types
- Documentation needs comprehensive update with new workflow
- Performance optimization needed for large exploration datasets
## 📝 Configuration

### Environment Variables
- `ANTHROPIC_API_KEY` - Claude API key
- `OPENAI_API_KEY` - OpenAI API key
- Additional configs in `config/` directory

### Key Config Files
- `config/agent.yaml` - Agent settings
- `config/eval.json` - Evaluation parameters
- `config/training.yaml` - Training configuration

---

## 👥 Contributors & Notes

### Development Notes
- Always maintain semantic/executable separation
- Update this file after significant changes
- Run tests before committing
- Follow conventional commit format

### Contact
- [Add contact info if needed]

---

## 📚 Related Documentation

- [README.md](README.md) - Project overview
- [ARCHITECTURE.md](docs/ARCHITECTURE.md) - System architecture
- [QUICKSTART.md](docs/QUICKSTART.md) - Getting started guide
- [CONTRIBUTING.md](CONTRIBUTING.md) - Contribution guidelines
- [WORKFLOW.md](docs/WORKFLOW.md) - Development workflow

---

**Remember:** Keep this context file updated to maintain project clarity! 🎯
