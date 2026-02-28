# Agent Rules & Guidelines

> **Rules for AI agents working on this project**

---

## 🚨 CRITICAL RULES

### 1. Always Update PROJECT_CONTEXT.md

**MANDATORY**: After making ANY significant changes to the project, you MUST update the `PROJECT_CONTEXT.md` file at the root of the project.

**What to update:**
- Add changes to "Recent Changes" section with date
- Update "Current Status" if features completed/started
- Update "Known Issues" if bugs discovered/fixed
- Update "Project Structure" if files/folders added/removed
- Update "Last Updated" timestamp at the top

**Example update:**
```markdown
## 🔧 Recent Changes

### March 1, 2026
- **Added**: New feature X in module Y
- **Fixed**: Bug in component Z
- **Modified**: Updated configuration in config.yaml
- **Files**: adapters/new_adapter.py, config/agent.yaml
```

### 2. Semantic/Executable Separation

**DO NOT** mix semantic and executable data:
- ❌ Never access `semantic_description` during agent execution
- ✅ Use only `executable_data` for browser actions
- ✅ Use semantic fields only for task synthesis and analysis

See [docs/ARCHITECTURE.md](../docs/ARCHITECTURE.md) for details.

### 3. URL-Based Storage

When working with data storage:
- Each website gets its own folder: `data/tasks/{url_folder}/`
- Use `url_to_folder_name()` from `exploration/storage.py`
- Never mix data from different domains

---

## 📋 Development Workflow Rules

### Before Starting Work
1. Read `PROJECT_CONTEXT.md` to understand current state
2. Check "Pending Tasks" and "Known Issues"
3. Verify no one else is working on the same feature

### During Development
1. Follow coding standards in `CONTRIBUTING.md`
2. Write tests for new features
3. Run `pytest tests/` before committing
4. Use conventional commit messages

### After Completing Work
1. **Update `PROJECT_CONTEXT.md`** (MANDATORY)
2. Run all tests: `pytest tests/`
3. Update relevant documentation in `docs/`
4. Update `CHANGELOG.md` if applicable
5. Commit with clear, descriptive message

---

## 🔍 Code Review Checklist

Before submitting changes, verify:

- [ ] `PROJECT_CONTEXT.md` has been updated
- [ ] All tests pass (`pytest tests/`)
- [ ] No semantic/executable data mixing
- [ ] Type hints added to new functions
- [ ] Docstrings added to new classes/functions
- [ ] No hardcoded values (use config files)
- [ ] Error handling is appropriate
- [ ] Code follows PEP 8 style guide

---

## 🧪 Testing Rules

### Test Requirements
- All new features MUST have tests
- Place tests in `tests/` directory
- Name test files `test_*.py`
- Aim for >80% code coverage

### Running Tests
```bash
# All tests
pytest tests/

# Specific test
pytest tests/test_feature.py

# With coverage
pytest --cov=exploration tests/
```

---

## 📝 Documentation Rules

### When to Update Docs
- New features → Update relevant docs in `docs/`
- API changes → Update `docs/REFERENCE.md`
- Architecture changes → Update `docs/ARCHITECTURE.md`
- New workflows → Update `docs/WORKFLOW.md`

### Documentation Priority
1. `PROJECT_CONTEXT.md` - Always first!
2. Code docstrings - For maintainability
3. `README.md` - If user-facing changes
4. Detailed docs in `docs/` - For complex features

---

## 🚀 Installed Skills

The following agent skills are available:

### browser-automation
- **Location**: `.agents/skills/browser-automation/`
- **Purpose**: Browser automation patterns and templates
- **Use when**: Working on browser control, Playwright integration

### playwright-visual-testing
- **Location**: `.agents/skills/playwright-visual-testing/`
- **Purpose**: Visual regression testing with Playwright
- **Use when**: Adding/updating visual tests, screenshot comparison

### webapp-testing
- **Location**: `.agents/skills/webapp-testing/`
- **Purpose**: Web application testing strategies
- **Use when**: Writing E2E tests, UI testing

---

## ⚠️ Common Pitfalls to Avoid

1. **Forgetting to update PROJECT_CONTEXT.md**
   - Set a reminder! This is the #1 rule

2. **Breaking semantic/executable separation**
   - Review architecture docs before modifying data models

3. **Not running tests before committing**
   - Use git hooks or IDE integration

4. **Mixing data from different domains**
   - Always use URL-based storage properly

5. **Skipping documentation**
   - Code is read more than written - document well!

---

## 🎯 Project Goals

Keep these goals in mind when making changes:

1. **Autonomous Exploration**: Enable agents to explore websites independently
2. **Data Quality**: Generate high-quality, realistic training data
3. **Maintainability**: Keep code clean, tested, and documented
4. **Extensibility**: Easy to add new explorers and adapters
5. **Reproducibility**: Experiments should be reproducible

---

## 📞 Questions?

If uncertain about any rule or guideline:
1. Check `PROJECT_CONTEXT.md` for current state
2. Review relevant docs in `docs/`
3. Look at similar existing code for patterns
4. Check `CONTRIBUTING.md` for style guidelines

---

**Remember: Good agents follow rules, great agents improve them!** 🎯

_Last Updated: March 1, 2026_
