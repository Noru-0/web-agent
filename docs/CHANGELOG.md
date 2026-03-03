# Changelog

All notable changes to the Web Agent System will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- URL-based storage system - each website gets unique folder
- Automatic task synthesis (Phase 3) after exploration
- Domain-aware task patterns (ecommerce, news, social, banking, streaming)
- Consolidated documentation (6 core files)
- GitHub repository setup (LICENSE, CONTRIBUTING.md, templates)

### Changed
- Storage system no longer auto-cleans data (preserves exploration history)
- Documentation reduced from 18 to 6 core files
- Improved .gitignore with comprehensive patterns

### Fixed
- Task synthesis now handles JSONL format correctly
- Storage system properly handles multi-website exploration

## [0.2.0] - 2026-02-25

### Added
- URL-based folder naming for multi-website exploration
- Automatic task synthesis pipeline integration
- Task synthesis with domain detection
- JSONL format support for screens/actions/transitions
- Comprehensive documentation restructure

### Changed
- ExplorationStorage defaults to `auto_clean=False`
- Exploration workflow now includes Phase 3 automatically
- Documentation consolidated and reorganized

### Removed
- 11 obsolete documentation files
- Demo/example code (production-ready focus)

## [0.1.0] - 2026-02-24

### Added
- Production CLI (`run_exploration.py`)
- Generic web environment for any website
- Semantic/Executable separation architecture
- AgentTrek and WebTactix adapter support
- Screen analyzer and deduplicator
- Trajectory recording system
- SLM agent implementation
- Basic training pipeline

### Initial Features
- LLM-based website exploration
- Semantic action extraction
- Task synthesis from exploration data
- Browser automation with Playwright
- Data cleaning and validation
- Model training and evaluation

---

## Versioning

- **MAJOR** version: Incompatible API changes
- **MINOR** version: New functionality (backwards-compatible)
- **PATCH** version: Bug fixes (backwards-compatible)

## Categories

- **Added**: New features
- **Changed**: Changes to existing functionality
- **Deprecated**: Soon-to-be removed features
- **Removed**: Removed features
- **Fixed**: Bug fixes
- **Security**: Security improvements
