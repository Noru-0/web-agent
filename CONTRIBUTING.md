# Contributing to Web Agent System

Thank you for your interest in contributing to the Web Agent System! This document provides guidelines and instructions for contributing.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Workflow](#development-workflow)
- [Pull Request Process](#pull-request-process)
- [Coding Standards](#coding-standards)
- [Testing](#testing)
- [Documentation](#documentation)

## Code of Conduct

By participating in this project, you agree to maintain a respectful and inclusive environment for all contributors.

## Getting Started

### Prerequisites

- Python 3.10+
- Node.js and npm (for Playwright)
- Git

### Setup Development Environment

1. Fork the repository
2. Clone your fork:
   ```bash
   git clone https://github.com/YOUR_USERNAME/web-agent.git
   cd web-agent
   ```

3. Create a virtual environment:
   ```bash
   python -m venv .venv
   .venv\Scripts\activate  # Windows
   source .venv/bin/activate  # Linux/Mac
   ```

4. Install dependencies:
   ```bash
   pip install -r requirements.txt
   playwright install chromium
   ```

5. Set up environment variables:
   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

6. Verify system:
   ```bash
   python scripts/verify_system.py
   ```

## Development Workflow

### Branch Naming

Use descriptive branch names:
- `feature/add-new-adapter` - New features
- `fix/exploration-bug` - Bug fixes
- `docs/update-readme` - Documentation updates
- `refactor/storage-module` - Code refactoring

### Making Changes

1. Create a new branch from `main`:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. Make your changes following the [coding standards](#coding-standards)

3. Test your changes:
   ```bash
   pytest tests/
   python scripts/verify_system.py
   ```

4. Commit your changes with clear messages:
   ```bash
   git commit -m "feat: add task synthesis for news domain"
   ```

## Pull Request Process

1. Update documentation if needed
2. Add tests for new features
3. Ensure all tests pass
4. Update CHANGELOG.md if applicable
5. Submit a pull request with:
   - Clear description of changes
   - Reference to related issues
   - Screenshots/examples if applicable

### PR Title Format

```
<type>: <short description>

Examples:
- feat: add URL-based storage system
- fix: resolve task synthesis edge case
- docs: update quickstart guide
- refactor: simplify exploration loop
- test: add integration tests for adapters
```

## Coding Standards

### Python Style

- Follow PEP 8
- Use type hints where possible
- Maximum line length: 100 characters
- Use descriptive variable names

### Code Organization

```python
# Module docstring
"""
Module description.
"""

# Imports (standard lib, third-party, local)
import logging
from typing import Optional

import requests

from exploration.schema import Screen

# Constants
MAX_RETRIES = 3

# Classes and functions
class MyClass:
    """Class docstring."""
    
    def my_method(self, param: str) -> bool:
        """Method docstring.
        
        Args:
            param: Parameter description
            
        Returns:
            Return value description
        """
        pass
```

### Architecture Principles

**⚠️ CRITICAL: Semantic/Executable Separation**

- Agents must NEVER access semantic fields during execution
- Semantic data is for task synthesis and analysis only
- Executable data is for browser actions only
- See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for details

### Commit Message Format

Use conventional commits:

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Adding/updating tests
- `chore`: Maintenance tasks

**Example:**
```
feat(exploration): add URL-based storage system

Each website now gets its own folder based on the URL.
This prevents data loss and allows parallel exploration.

Closes #123
```

## Testing

### Running Tests

```bash
# Run all tests
pytest tests/

# Run specific test file
pytest tests/test_task_synthesis.py

# Run with coverage
pytest --cov=exploration tests/

# Run with verbose output
pytest -v tests/
```

### Writing Tests

- Place tests in `tests/` directory
- Name test files `test_*.py`
- Name test functions `test_*`
- Use descriptive test names
- Include docstrings for complex tests

Example:
```python
def test_url_to_folder_name_with_port():
    """Test URL conversion with port number."""
    from exploration.storage import url_to_folder_name
    
    result = url_to_folder_name("http://localhost:9999")
    assert result == "localhost_9999"
```

## Documentation

### Updating Documentation

- Update relevant docs in `docs/` directory
- Keep README.md in sync with changes
- Add docstrings to all public functions/classes
- Include usage examples for new features

### Documentation Structure

```
docs/
├── README.md              # Index
├── QUICKSTART.md          # Getting started
├── ARCHITECTURE.md        # System design
├── WORKFLOW.md            # Development workflow
├── PHASE3_WORKFLOW.md     # Task synthesis
└── REFERENCE.md           # API reference
```

## Areas for Contribution

### High Priority

- [ ] Additional domain patterns for task synthesis
- [ ] More comprehensive tests
- [ ] Performance optimizations
- [ ] Error handling improvements

### Medium Priority

- [ ] Additional explorer adapters
- [ ] UI/visualization tools
- [ ] Example notebooks
- [ ] Video tutorials

### Documentation

- [ ] API documentation improvements
- [ ] More usage examples
- [ ] Architecture diagrams
- [ ] Translation to other languages

## Questions or Issues?

- Check existing [issues](https://github.com/your-repo/web-agent/issues)
- Read the [documentation](docs/README.md)
- Ask in discussions

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

Thank you for contributing to Web Agent System! 🚀
