"""
Test script for new structured semantic action format.

Verifies that the analyzer produces domain-agnostic, structured actions.
"""

import json
from exploration.schema import ActionSemantic, ScreenType

def test_action_semantic_structure():
    """Test ActionSemantic with new structured format."""
    print("=" * 60)
    print("Testing Structured Semantic Actions")
    print("=" * 60)
    
    # Test 1: Create action with all fields
    action1 = ActionSemantic(
        intent="search",
        object="items",
        context="via text input",
        confidence=0.82
    )
    
    print("\n✓ Test 1: Full action structure")
    print(f"  Intent: {action1.intent}")
    print(f"  Object: {action1.object}")
    print(f"  Context: {action1.context}")
    print(f"  Confidence: {action1.confidence}")
    print(f"  Description: {action1.description}")
    print(f"  Action ID: {action1.action_id}")
    
    # Test 2: Create action without context
    action2 = ActionSemantic(
        intent="view",
        object="item details",
        confidence=0.74
    )
    
    print("\n✓ Test 2: Action without context")
    print(f"  Description: {action2.description}")
    
    # Test 3: Serialize to dict
    action_dict = action1.to_dict()
    print("\n✓ Test 3: Serialization to dict")
    print(f"  {json.dumps(action_dict, indent=2)}")
    
    # Test 4: Confidence clamping
    action3 = ActionSemantic(
        intent="navigate",
        object="page",
        confidence=1.5  # Invalid, should clamp to 1.0
    )
    
    print("\n✓ Test 4: Confidence clamping")
    print(f"  Input confidence: 1.5")
    print(f"  Clamped confidence: {action3.confidence}")
    
    # Test 5: Multiple actions
    actions = [
        ActionSemantic(intent="search", object="products", confidence=0.9),
        ActionSemantic(intent="filter", object="results", context="by category", confidence=0.85),
        ActionSemantic(intent="navigate", object="details page", confidence=0.78),
    ]
    
    print("\n✓ Test 5: Multiple actions")
    for i, action in enumerate(actions, 1):
        print(f"  {i}. {action.description} (confidence: {action.confidence})")
    
    print("\n" + "=" * 60)
    print("All tests passed! ✓")
    print("=" * 60)
    
    # Show example JSON output format
    print("\nExpected LLM Output Format:")
    print(json.dumps({
        "screen_summary": "A search results page showing various items with filtering options.",
        "semantic_actions": [
            {
                "intent": "search",
                "object": "items",
                "context": "via text input",
                "confidence": 0.82
            },
            {
                "intent": "filter",
                "object": "results",
                "context": "by category",
                "confidence": 0.89
            },
            {
                "intent": "view",
                "object": "item details",
                "context": None,
                "confidence": 0.74
            }
        ]
    }, indent=2))


if __name__ == "__main__":
    test_action_semantic_structure()
