# Project Context Update Template

> Copy and paste this template when updating PROJECT_CONTEXT.md

---

## Template for Recent Changes

```markdown
### [YYYY-MM-DD]
- **Added**: [What was added - new features, files, capabilities]
- **Fixed**: [What was fixed - bugs resolved, issues addressed]
- **Modified**: [What was changed - updates to existing features]
- **Removed**: [What was removed - deprecated features, old files]
- **Impact**: [How this affects the project - who needs to know, what changed]
- **Files**: [List of affected files - paths relative to project root]
```

---

## Quick Checklist

Before committing, ensure you've updated these sections in PROJECT_CONTEXT.md:

- [ ] **Last Updated** - Update date at the top of the file
- [ ] **Recent Changes** - Add entry with today's date and details
- [ ] **Current Status** - Update if features completed or new tasks started
- [ ] **Known Issues** - Add new issues or mark resolved ones
- [ ] **Project Structure** - Update if files/folders added or removed
- [ ] **Recent Changes** should include:
  - [ ] Clear description of what changed
  - [ ] Why it changed (if not obvious)
  - [ ] Impact on other parts of the system
  - [ ] List of modified files

---

## Examples

### Example 1: New Feature
```markdown
### 2026-03-15
- **Added**: User authentication module in `auth/` directory
- **Added**: Login/logout endpoints in API
- **Modified**: Database schema to include users table
- **Impact**: Breaking change - requires database migration
- **Files**: auth/__init__.py, auth/handlers.py, migrations/001_add_users.sql, config/agent.yaml
```

### Example 2: Bug Fix
```markdown
### 2026-03-14
- **Fixed**: Memory leak in browser session management
- **Modified**: Added proper cleanup in `browser/session.py`
- **Impact**: Improves stability for long-running explorations
- **Files**: browser/session.py, tests/test_browser_cleanup.py
```

### Example 3: Refactoring
```markdown
### 2026-03-13
- **Refactored**: Storage module to use URL-based folders
- **Modified**: Updated all storage calls across codebase
- **Removed**: Old flat-file storage system
- **Impact**: All exploration data now organized by URL, prevents data conflicts
- **Files**: exploration/storage.py, adapters/*.py, tests/test_storage.py
```

### Example 4: Documentation
```markdown
### 2026-03-12
- **Added**: Comprehensive API documentation in docs/API.md
- **Modified**: Updated README with new examples
- **Impact**: Easier onboarding for new contributors
- **Files**: docs/API.md, README.md
```

### Example 5: Dependency Update
```markdown
### 2026-03-11
- **Modified**: Updated Playwright to v1.42.0
- **Fixed**: Compatibility issues with latest Chromium
- **Impact**: Requires reinstalling Playwright browsers: `playwright install chromium`
- **Files**: requirements.txt, browser/controller.py
```

---

## Status Update Examples

### Completing a Feature

Move from "Pending Tasks" to "Recently Completed":

```markdown
### Recently Completed
- ✅ Task synthesis from exploration data
- ✅ Semantic action normalization
- ✅ URL-based storage system

### Pending Tasks
- [ ] Additional domain patterns for task synthesis
- [ ] Performance optimizations
```

### Adding a New Issue

Add to "Known Issues":

```markdown
### Known Issues

#### Critical
- Browser crashes on certain JavaScript-heavy sites (Issue #123)

#### Non-Critical
- Task synthesis sometimes generates duplicate tasks
- Slow performance with >1000 screens in memory
```

### Starting New Work

Add to "Active Development Areas":

```markdown
### Active Development Areas
- Task synthesis from exploration data ⬅️ In progress
- Multi-browser support (Firefox, Safari)
- Parallel exploration with multiple agents
```

---

## Tips

1. **Be specific**: "Added login feature" → "Added JWT-based authentication with refresh tokens"
2. **Include impact**: Always explain why the change matters
3. **List files**: Helps others find related code quickly
4. **Use consistent format**: Makes it easier to scan history
5. **Update immediately**: Don't wait - update right after making changes
6. **Link issues**: Reference GitHub issues when applicable (Issue #123)

---

## Common Mistakes to Avoid

❌ **Too vague**: "Updated some files"
✅ **Better**: "Refactored storage module to use URL-based organization"

❌ **No context**: "Fixed bug"
✅ **Better**: "Fixed memory leak in browser session causing crashes after 100+ navigations"

❌ **Missing files**: "Updated adapter"
✅ **Better**: "Updated AgentTrek adapter (adapters/agenttrek_adapter.py, tests/test_agenttrek.py)"

❌ **No date**: Just adding to "Recent Changes" without date
✅ **Better**: Always use "### YYYY-MM-DD" format

---

## When in Doubt

If you're unsure whether a change is "significant enough" to warrant updating PROJECT_CONTEXT.md, ask:

- Will other developers need to know about this?
- Does this change how the system works?
- Would I want to know about this if I joined the project tomorrow?

If yes to any of these → **Update PROJECT_CONTEXT.md**

---

**Remember: When you update PROJECT_CONTEXT.md, you're helping future you and your teammates! 🎯**
