# Web Agent Documentation

Comprehensive documentation for the Web Agent exploration and training system.

---

## 📖 Documentation Index

### 🚀 Getting Started

**[QUICKSTART.md](QUICKSTART.md)** - Complete quickstart guide
- Installation and setup
- Running exploration (Phase 2 & 3)
- Data processing and cleaning
- Model training
- Agent execution
- Storage system (URL-based folders)

### 🏗️ Architecture

**[ARCHITECTURE.md](ARCHITECTURE.md)** - System architecture and design
- Overall system design
- Component interaction
- Data flow architecture
- Semantic/Executable separation principles
- Architectural enforcement rules

### 📋 Workflow

**[WORKFLOW.md](WORKFLOW.md)** - Complete development workflow
- Phase 1: Offline data collection
- Phase 2: Data conversion
- Phase 3: Task synthesis
- Phase 4: Model training
- Phase 5: Evaluation
- Phase 6: Production deployment

### 🎯 Task Synthesis

**[PHASE3_WORKFLOW.md](PHASE3_WORKFLOW.md)** - Detailed task synthesis guide
- Automatic task synthesis after exploration
- Manual task synthesis
- Domain-specific patterns
- Task graph output format
- Examples and troubleshooting

### 📚 Reference

**[REFERENCE.md](REFERENCE.md)** - Complete API and command reference
- Data structures and schemas
- CLI commands
- Python APIs
- Soft hints system
- Adapter interfaces
- Configuration options

---

## 🎯 Quick Navigation by Use Case

### "I want to explore a website"
1. Start with [QUICKSTART.md → Exploration](QUICKSTART.md#khám-phá-website-exploration)
2. See detailed workflow in [PHASE3_WORKFLOW.md](PHASE3_WORKFLOW.md)
3. Check [REFERENCE.md](REFERENCE.md) for CLI options

### "I want to understand the system architecture"
1. Read [ARCHITECTURE.md](ARCHITECTURE.md) for overall design
2. See [WORKFLOW.md](WORKFLOW.md) for end-to-end flow
3. Check [PHASE3_WORKFLOW.md](PHASE3_WORKFLOW.md) for task synthesis specifics

### "I want to train a model"
1. Follow [QUICKSTART.md → Training](QUICKSTART.md#huấn-luyện-model)
2. See [WORKFLOW.md → Phase 4](WORKFLOW.md#phase-4-model-training)
3. Check training README in `../training/README.md`

### "I want to implement an adapter"
1. Review [ARCHITECTURE.md → Adapters](ARCHITECTURE.md)
2. Check [REFERENCE.md → Adapter Interface](REFERENCE.md)
3. See examples in `../adapters/`

### "I want to understand storage"
1. Quick overview: [QUICKSTART.md → Storage](QUICKSTART.md)
2. Technical details: [ARCHITECTURE.md](ARCHITECTURE.md)
3. Each website gets its own folder: `data/raw/{url_folder}/`

---

## 📁 Documentation Structure

```
docs/
├── README.md                # This file - documentation index
├── QUICKSTART.md            # Complete getting started guide
├── ARCHITECTURE.md          # System architecture & design principles
├── WORKFLOW.md              # Complete development workflow
├── PHASE3_WORKFLOW.md       # Task synthesis detailed guide
├── REFERENCE.md             # Complete API & CLI reference
└── diagrams/                # Architecture diagrams
```

---

## 🔥 Most Common Tasks

### Run Exploration
```bash
python run_exploration.py --url http://localhost:9999
# → Automatically explores + synthesizes tasks
# → Output: data/raw/localhost_9999/ + data/tasks/localhost_9999/
```

### Train Model
```bash
python -m training.train
```

### Run Agent
```bash
python agents/runner.py
```

---

## 💡 Key Concepts

### Phase 2: Exploration
- Automated website exploration using AgentTrek/WebTactix
- Discovers screens, actions, transitions
- Outputs: `screens.jsonl`, `actions.jsonl`, `transitions.jsonl`, `metadata.json`

### Phase 3: Task Synthesis
- **Automatic** after exploration (can disable with `--skip-task-synthesis`)
- Deterministic task aggregation from semantic actions
- Domain-aware patterns (ecommerce, news, social, banking, streaming)
- Outputs: `tasks.json`, `tasks_summary.txt`

### Storage System
- **URL-based folders**: Each website gets unique folder (e.g., `localhost_9999`)
- **No auto-cleanup**: Previous explorations preserved
- **JSONL format**: Newline-delimited JSON for screens/actions/transitions
- **Parallel exploration**: Can explore multiple sites simultaneously

### Semantic/Executable Separation
- **Semantic**: Intent, description, context (for LLM/task synthesis)
- **Executable**: Selectors, types, values (for browser execution)
- **Strict separation**: Agents use ONLY executable, never semantic
- See [ARCHITECTURE.md](ARCHITECTURE.md) for details

---

## 🆘 Getting Help

1. **Quick commands**: See [QUICKSTART.md](QUICKSTART.md)
2. **Architecture questions**: See [ARCHITECTURE.md](ARCHITECTURE.md)
3. **Workflow questions**: See [WORKFLOW.md](WORKFLOW.md)
4. **API reference**: See [REFERENCE.md](REFERENCE.md)
5. **Task synthesis**: See [PHASE3_WORKFLOW.md](PHASE3_WORKFLOW.md)

---

## 📝 Recent Updates

- **URL-based storage**: Each website now gets unique folder
- **Automatic task synthesis**: Phase 3 runs automatically after exploration
- **Consolidated docs**: Reduced from 18 to 6 core documentation files

### "I need API reference"
→ See [REFERENCE.md](REFERENCE.md)  
→ Check code patterns in [REFERENCE.md](REFERENCE.md#common-patterns)

---

## 📖 Reading Order for New Contributors

1. **[../README.md](../README.md)** - Project overview
2. **[../QUICKSTART.md](../QUICKSTART.md)** - Get it running
3. **[ARCHITECTURE.md](ARCHITECTURE.md)** - Understand the system
4. **[SEMANTIC_EXECUTABLE_SEPARATION.md](SEMANTIC_EXECUTABLE_SEPARATION.md)** - Core data model
5. **[WORKFLOW.md](WORKFLOW.md)** - Development practices
6. **[REFERENCE.md](REFERENCE.md)** - API and commands

---

## 🔍 Key Principles

### 1. Semantic-Only Control
Agents receive **only semantic descriptions**, never executable details (selectors, coordinates).

→ See [SEMANTIC_ONLY_ENFORCEMENT.md](SEMANTIC_ONLY_ENFORCEMENT.md)

### 2. Separation of Concerns
**Semantic** (what to do) is strictly separated from **Executable** (how to do it).

→ See [SEMANTIC_EXECUTABLE_SEPARATION.md](SEMANTIC_EXECUTABLE_SEPARATION.md)

### 3. Soft Hints for Guidance
LLMs can provide soft hints to guide execution without violating agent autonomy.

→ See [SOFT_HINTS.md](SOFT_HINTS.md)

---

## 📝 Contributing to Documentation

When updating docs:

1. **Keep docs in sync** - Update related docs when making changes
2. **Link between docs** - Use relative links to connect related content
3. **Use examples** - Include code examples for clarity
4. **Test commands** - Verify all commands work before documenting

---

## 🆘 Getting Help

- Check [REFERENCE.md](REFERENCE.md) for commands and APIs
- Review [ARCHITECTURE.md](ARCHITECTURE.md) for system understanding
- See code examples in `../adapters/` and `../tests/`
- Open issues on GitHub for bugs or questions

---

**Last Updated:** 2026-02-11
