"""
Adapter registry for explorer adapters.

This module provides a central registry for all available adapters
and a factory method to create them by name.

Usage:
    adapter = create_adapter("webtactix")
    trajectory = adapter.convert(input_path, output_path)
"""

from typing import Dict, Type, List
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from adapters.base_adapter import ExplorerAdapter
from adapters.webtactix_adapter import WebTactiXAdapter
from adapters.agenttrek_adapter import AgentTrekAdapter


# Global registry of adapters
_ADAPTER_REGISTRY: Dict[str, Type[ExplorerAdapter]] = {}


def register_adapter(name: str, adapter_class: Type[ExplorerAdapter]):
    """
    Register an adapter in the global registry.
    
    Args:
        name: Unique name for the adapter (e.g., "webtactix")
        adapter_class: Adapter class (must subclass ExplorerAdapter)
    """
    if not issubclass(adapter_class, ExplorerAdapter):
        raise TypeError(f"{adapter_class} must subclass ExplorerAdapter")
    
    _ADAPTER_REGISTRY[name.lower()] = adapter_class


def create_adapter(name: str) -> ExplorerAdapter:
    """
    Factory method to create an adapter by name.
    
    Args:
        name: Adapter name (e.g., "webtactix", "agenttrek")
        
    Returns:
        Instantiated adapter
        
    Raises:
        ValueError: If adapter not found
    """
    name = name.lower()
    
    if name not in _ADAPTER_REGISTRY:
        available = ", ".join(_ADAPTER_REGISTRY.keys())
        raise ValueError(
            f"Unknown adapter: {name}. "
            f"Available adapters: {available}"
        )
    
    adapter_class = _ADAPTER_REGISTRY[name]
    return adapter_class()


def list_adapters() -> List[str]:
    """
    List all registered adapter names.
    
    Returns:
        List of adapter names
    """
    return sorted(_ADAPTER_REGISTRY.keys())


def get_adapter_info() -> Dict[str, str]:
    """
    Get information about all registered adapters.
    
    Returns:
        Dict mapping adapter names to their class names
    """
    return {
        name: adapter_class.__name__
        for name, adapter_class in _ADAPTER_REGISTRY.items()
    }


# Register built-in adapters
register_adapter("webtactix", WebTactiXAdapter)
register_adapter("agenttrek", AgentTrekAdapter)


# Convenience function for CLI
def print_available_adapters():
    """Print information about available adapters"""
    print("Available adapters:")
    for name, class_name in get_adapter_info().items():
        print(f"  - {name:15s} ({class_name})")
