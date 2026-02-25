"""
Validation utilities for enforcing semantic-only control.

Provides helper functions to validate that data structures contain
NO executable information (selectors, DOM, coordinates, etc.)

Use these validators at critical boundaries:
- Before passing data to LLM
- Before building prompts
- After projecting to semantic graph
"""

from typing import Dict, Any, List
import logging

logger = logging.getLogger(__name__)


# Forbidden fields that indicate executable data
FORBIDDEN_EXECUTABLE_FIELDS = {
    'selector',
    'xpath',
    'css_selector',
    'dom_snapshot',
    'dom_path',
    'coordinates',
    'position',
    'element_text',
    'element_type',
    'element_id',
    'element_tag',
    'bbox',
    'bounding_box',
    'interactive_elements',
}


def validate_semantic_only(
    data: Dict[str, Any],
    context: str = "data",
    raise_on_violation: bool = True
) -> bool:
    """
    Validate that data structure contains NO executable information.
    
    STRICT ENFORCEMENT:
    - Recursively checks all nested dictionaries and lists
    - Detects forbidden executable fields
    - Optionally raises exception on violations
    
    Args:
        data: Dictionary or object to validate
        context: Context string for error messages
        raise_on_violation: If True, raises ValueError on violations
        
    Returns:
        True if validation passes, False if violations found
        
    Raises:
        ValueError: If raise_on_violation=True and violations found
        
    Examples:
        >>> # Valid semantic data
        >>> semantic_action = {"intent": "search", "object": "items"}
        >>> validate_semantic_only(semantic_action)  # Returns True
        
        >>> # Invalid - contains executable
        >>> bad_action = {"intent": "search", "selector": "#search-btn"}
        >>> validate_semantic_only(bad_action)  # Raises ValueError
    """
    violations = []
    _check_dict_recursive(data, context, violations, path=[])
    
    if violations:
        error_msg = (
            f"SEMANTIC-ONLY VALIDATION FAILED: Executable data found in {context}\\n"
            "This violates the semantic-only control principle.\\n"
            "Violations:\\n"
        )
        for path, field in violations:
            error_msg += f"  - {path}: contains '{field}'\\n"
        
        logger.error(error_msg)
        
        if raise_on_violation:
            raise ValueError(error_msg)
        return False
    
    logger.debug(f"Semantic-only validation passed for {context}")
    return True


def _check_dict_recursive(
    obj: Any,
    context: str,
    violations: List,
    path: List[str]
):
    """
    Recursively check object for forbidden executable fields.
    
    Args:
        obj: Object to check
        context: Context string
        violations: List to append violations to
        path: Current path in object tree
    """
    if isinstance(obj, dict):
        # Check keys for forbidden fields
        for key in obj.keys():
            if key in FORBIDDEN_EXECUTABLE_FIELDS:
                path_str = '.'.join(path + [key]) if path else key
                violations.append((path_str, key))
        
        # Recursively check values
        for key, value in obj.items():
            _check_dict_recursive(value, context, violations, path + [key])
    
    elif isinstance(obj, (list, tuple)):
        # Check list items
        for i, item in enumerate(obj):
            _check_dict_recursive(item, context, violations, path + [f"[{i}]"])


def assert_no_selectors(data: Any, message: str = "Selector found in semantic data"):
    """
    Assert that data contains no selector fields.
    
    Quick assertion for critical code paths.
    
    Args:
        data: Data to check (dict, list, or object)
        message: Error message if assertion fails
        
    Raises:
        AssertionError: If selector fields found
    """
    if isinstance(data, dict):
        assert 'selector' not in data, f"{message}: 'selector' field present"
        assert 'xpath' not in data, f"{message}: 'xpath' field present"
        assert 'css_selector' not in data, f"{message}: 'css_selector' field present"
        
        # Recursively check nested dicts
        for value in data.values():
            if isinstance(value, (dict, list)):
                assert_no_selectors(value, message)
    
    elif isinstance(data, (list, tuple)):
        for item in data:
            assert_no_selectors(item, message)


def filter_semantic_fields(action_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Filter action dictionary to contain ONLY semantic fields.
    
    Useful for preparing data for LLM prompts.
    
    Args:
        action_dict: Action dictionary (may contain executable fields)
        
    Returns:
        New dictionary with only semantic fields
    """
    # Allowed semantic fields
    semantic_fields = {
        'action_id',
        'intent',
        'object',
        'context',
        'description',
        'confidence',
        'category',
        'expected_outcome',
    }
    
    # Filter to semantic fields only
    semantic_dict = {
        k: v for k, v in action_dict.items()
        if k in semantic_fields
    }
    
    return semantic_dict


def strip_executable_from_graph(graph: Dict[str, Any]) -> Dict[str, Any]:
    """
    Strip all executable fields from exploration graph.
    
    Used by semantic projector to ensure clean output.
    
    Args:
        graph: Exploration graph dictionary
        
    Returns:
        New dictionary with executable fields removed
    """
    import copy
    cleaned = copy.deepcopy(graph)
    
    # Remove forbidden fields recursively
    _remove_forbidden_fields(cleaned)
    
    return cleaned


def _remove_forbidden_fields(obj: Any):
    """
    Recursively remove forbidden fields from object.
    
    Args:
        obj: Object to clean (modified in place)
    """
    if isinstance(obj, dict):
        # Remove forbidden keys
        keys_to_remove = [k for k in obj.keys() if k in FORBIDDEN_EXECUTABLE_FIELDS]
        for key in keys_to_remove:
            del obj[key]
        
        # Recursively clean values
        for value in obj.values():
            _remove_forbidden_fields(value)
    
    elif isinstance(obj, (list, tuple)):
        for item in obj:
            _remove_forbidden_fields(item)


# Export validation functions
__all__ = [
    'validate_semantic_only',
    'assert_no_selectors',
    'filter_semantic_fields',
    'strip_executable_from_graph',
    'FORBIDDEN_EXECUTABLE_FIELDS',
]
