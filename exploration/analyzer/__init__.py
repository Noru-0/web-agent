"""
Screen analysis submodule for exploration.

Refactored from monolithic analyzer.py for better organization:
- screen_analyzer.py: Main ScreenAnalyzer class
- Future: action_generator.py for action-specific logic

This __init__.py maintains backward compatibility.
"""

from exploration.analyzer.screen_analyzer import (
    ScreenAnalyzer,
    extract_visible_text
)

__all__ = [
    "ScreenAnalyzer",
    "extract_visible_text"
]
