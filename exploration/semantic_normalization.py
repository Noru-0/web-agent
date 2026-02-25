"""
Semantic action normalization utilities.

Handles conversion of various semantic action formats (strings, dicts, objects)
into a consistent normalized format.

CRITICAL: Semantic actions can come in multiple forms:
- Free-text strings from LLM
- Structured dicts with intent/object/context
- ActionSemantic objects

All must be normalized to ensure safe access to description.
"""

from typing import Dict, Any, Optional, Union
import logging

logger = logging.getLogger(__name__)


def normalize_semantic(semantic: Union[str, Dict[str, Any], Any]) -> Dict[str, Any]:
    """
    Normalize semantic action to consistent dictionary format.
    
    CRITICAL: This ensures semantic ALWAYS has a description field.
    Handles:
    - Free-text strings → {"description": str, ...}
    - Dicts without description → add generated description
    - Objects with .to_dict() → convert to dict
    - None or empty → return unknown action dict
    
    Args:
        semantic: Input semantic (string, dict, object, or None)
        
    Returns:
        Normalized dict with guaranteed "description" field
        
    Examples:
        >>> normalize_semantic("click login button")
        {"description": "click login button", "intent": None, "object": None}
        
        >>> normalize_semantic({"intent": "search", "object": "items"})
        {"intent": "search", "object": "items", "description": "search items"}
    """
    # Case 0: None or empty input
    if semantic is None or (isinstance(semantic, str) and not semantic.strip()):
        logger.debug("Normalizing None/empty semantic")
        return {
            "description": "unknown action",
            "intent": None,
            "object": None,
            "context": None,
            "confidence": 0.0
        }
    
    # Case 1: String input → wrap in dict
    if isinstance(semantic, str):
        logger.debug(f"Normalizing string semantic: {semantic[:50]}")
        return {
            "description": semantic,
            "intent": None,
            "object": None,
            "context": None,
            "confidence": 0.5  # Low confidence for free-text
        }
    
    # Case 2: Dict input → ensure description exists
    if isinstance(semantic, dict):
        normalized = semantic.copy()
        
        # Generate description if missing
        if "description" not in normalized:
            description = generate_description_from_fields(normalized)
            normalized["description"] = description
            logger.debug(f"Generated description: {description}")
        
        # Ensure all required fields exist
        normalized.setdefault("intent", None)
        normalized.setdefault("object", None)
        normalized.setdefault("context", None)
        normalized.setdefault("confidence", 0.75)
        
        return normalized
    
    # Case 3: Object with to_dict() → convert
    if hasattr(semantic, 'to_dict'):
        dict_form = semantic.to_dict()
        return normalize_semantic(dict_form)  # Recurse
    
    # Case 4: Object with description attribute
    if hasattr(semantic, 'description'):
        return {
            "description": semantic.description,
            "intent": getattr(semantic, 'intent', None),
            "object": getattr(semantic, 'object', None),
            "context": getattr(semantic, 'context', None),
            "confidence": getattr(semantic, 'confidence', 0.75)
        }
    
    # Fallback: Convert to string
    logger.warning(f"Unknown semantic type: {type(semantic)}, converting to string")
    return {
        "description": str(semantic),
        "intent": None,
        "object": None,
        "context": None,
        "confidence": 0.0  # Very low confidence
    }


def generate_description_from_fields(semantic_dict: Dict[str, Any]) -> str:
    """
    Generate description from intent, object, context fields.
    
    Args:
        semantic_dict: Dictionary with optional intent/object/context
        
    Returns:
        Generated description string
    """
    intent = semantic_dict.get("intent")
    obj = semantic_dict.get("object")
    context = semantic_dict.get("context")
    
    # If all are None, use any available string field
    if not intent and not obj:
        # Try to find any string value
        for key, value in semantic_dict.items():
            if isinstance(value, str) and value and key != "action_id":
                return value
        return "unknown action"
    
    # Build from intent + object + context
    parts = []
    if intent:
        parts.append(str(intent))
    if obj:
        parts.append(str(obj))
    
    description = " ".join(parts) if parts else "unknown action"
    
    if context:
        description += f" ({context})"
    
    return description


def safe_get_description(semantic: Union[str, Dict[str, Any], Any]) -> str:
    """
    Safely extract description from semantic action.
    
    ALWAYS returns a string, never raises exceptions.
    
    Args:
        semantic: Semantic action in any format
        
    Returns:
        Description string
    """
    try:
        normalized = normalize_semantic(semantic)
        return normalized.get("description", "unknown action")
    except Exception as e:
        logger.error(f"Error extracting description: {e}", exc_info=True)
        return str(semantic)[:100] if semantic else "unknown action"


def normalize_action_list(actions: list) -> list:
    """
    Normalize a list of semantic actions.
    
    Handles mixed lists of strings, dicts, and objects.
    
    Args:
        actions: List of semantic actions in various formats
        
    Returns:
        List of normalized dicts
    """
    normalized = []
    
    for i, action in enumerate(actions):
        try:
            norm = normalize_semantic(action)
            normalized.append(norm)
        except Exception as e:
            logger.error(f"Error normalizing action {i}: {e}")
            # Add fallback
            normalized.append({
                "description": f"action_{i}",
                "intent": None,
                "object": None,
                "context": None,
                "confidence": 0.0
            })
    
    return normalized


def is_valid_semantic(semantic: Any) -> bool:
    """
    Check if semantic is valid and has description.
    
    Args:
        semantic: Semantic to validate
        
    Returns:
        True if valid and has description
    """
    if not semantic:
        return False
    
    try:
        normalized = normalize_semantic(semantic)
        return bool(normalized.get("description"))
    except Exception:
        return False


# Export functions
__all__ = [
    'normalize_semantic',
    'generate_description_from_fields',
    'safe_get_description',
    'normalize_action_list',
    'is_valid_semantic',
]
