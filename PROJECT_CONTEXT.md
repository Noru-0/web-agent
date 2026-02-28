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

### Active Development Areas
- Task synthesis from exploration data
- Semantic action normalization
- URL-based storage system
- Explorer adapters (AgentTrek, WebTactix)

### Recently Completed
- ✅ Installed agent skills: browser-automation, playwright-visual-testing, webapp-testing
- ✅ Semantic/Executable data separation architecture
- ✅ Action deduplication system
- ✅ Task validation framework

### Pending Tasks
- [ ] Additional domain patterns for task synthesis
- [ ] Performance optimizations
- [ ] More comprehensive test coverage
- [ ] Integration with additional explorers

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

### March 1, 2026
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
- None

### Non-Critical
- [List any non-critical issues here]

---

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
