"""
Test script to verify semantic action normalization works correctly.

This tests the fix for: 'str' object has no attribute 'description' errors
"""

from exploration.semantic_normalization import (
    normalize_semantic,
    safe_get_description,
    generate_description_from_fields
)
from exploration.schema import ActionSemantic


def test_string_semantic():
    """Test string-based semantic actions"""
    print("\n=== Test 1: String Semantic ===")
    
    semantic_str = "click the login button"
    normalized = normalize_semantic(semantic_str)
    description = safe_get_description(semantic_str)
    
    print(f"Input: {semantic_str}")
    print(f"Normalized: {normalized}")
    print(f"Description: {description}")
    assert description == semantic_str, "String description should match input"
    print("✓ PASSED")


def test_dict_semantic():
    """Test dict-based semantic actions"""
    print("\n=== Test 2: Dict Semantic ===")
    
    # With explicit description
    semantic_dict1 = {
        'intent': 'login',
        'object': 'button',
        'description': 'click the login button'
    }
    description1 = safe_get_description(semantic_dict1)
    print(f"Input (with desc): {semantic_dict1}")
    print(f"Description: {description1}")
    assert description1 == 'click the login button'
    
    # Without description (auto-generate)
    semantic_dict2 = {
        'intent': 'submit',
        'object': 'form',
        'context': 'checkout'
    }
    normalized2 = normalize_semantic(semantic_dict2)
    description2 = safe_get_description(normalized2)
    print(f"\nInput (no desc): {semantic_dict2}")
    print(f"Description: {description2}")
    assert 'submit' in description2.lower()
    assert 'form' in description2.lower()
    print("✓ PASSED")


def test_object_semantic():
    """Test ActionSemantic object-based actions"""
    print("\n=== Test 3: Object Semantic ===")
    
    # With all fields
    semantic_obj1 = ActionSemantic(
        intent='checkout',
        object='cart',
        context='shopping'
    )
    description1 = safe_get_description(semantic_obj1)
    print(f"Input: ActionSemantic(intent='checkout', object='cart', context='shopping')")
    print(f"Description: {description1}")
    assert description1 == 'checkout cart (shopping)'
    
    # With only intent
    semantic_obj2 = ActionSemantic(intent='navigate')
    description2 = safe_get_description(semantic_obj2)
    print(f"\nInput: ActionSemantic(intent='navigate')")
    print(f"Description: {description2}")
    assert description2 == 'navigate'
    
    # With explicit description
    semantic_obj3 = ActionSemantic(
        intent='click',
        description='click the submit button'
    )
    description3 = safe_get_description(semantic_obj3)
    print(f"\nInput: ActionSemantic(intent='click', description='click the submit button')")
    print(f"Description: {description3}")
    assert description3 == 'click the submit button'
    print("✓ PASSED")


def test_from_string_classmethod():
    """Test ActionSemantic.from_string() class method"""
    print("\n=== Test 4: from_string() ClassMethod ===")
    
    semantic = ActionSemantic.from_string("navigate to homepage")
    print(f"Input: 'navigate to homepage'")
    print(f"Created: {semantic}")
    print(f"Description: {semantic.description}")
    assert semantic.description == "navigate to homepage"
    assert semantic.intent is None
    assert semantic.object is None
    print("✓ PASSED")


def test_edge_cases():
    """Test edge cases and error conditions"""
    print("\n=== Test 5: Edge Cases ===")
    
    # None input
    result1 = safe_get_description(None)
    print(f"Input: None → Description: '{result1}'")
    assert result1 == "unknown action"
    
    # Empty string
    result2 = safe_get_description("")
    print(f"Input: '' → Description: '{result2}'")
    assert result2 == "unknown action"
    
    # Empty dict
    result3 = safe_get_description({})
    print(f"Input: {{}} → Description: '{result3}'")
    assert result3 == "unknown action"
    
    # ActionSemantic with no fields
    semantic_empty = ActionSemantic()
    result4 = safe_get_description(semantic_empty)
    print(f"Input: ActionSemantic() → Description: '{result4}'")
    assert result4 == "unknown action"
    
    print("✓ PASSED")


def test_backward_compatibility():
    """Test that old code patterns still work"""
    print("\n=== Test 6: Backward Compatibility ===")
    
    # Old pattern: ActionSemantic with all required fields
    semantic_old = ActionSemantic(
        intent='login',
        object='button',
        context='homepage'
    )
    
    # Should still work with new code
    normalized = normalize_semantic(semantic_old)
    description = safe_get_description(semantic_old)
    
    print(f"Old-style ActionSemantic: {semantic_old}")
    print(f"Normalized: {normalized}")
    print(f"Description: {description}")
    assert 'login' in description.lower()
    assert 'button' in description.lower()
    print("✓ PASSED")


def main():
    """Run all tests"""
    print("=" * 60)
    print("SEMANTIC ACTION NORMALIZATION TESTS")
    print("=" * 60)
    
    try:
        test_string_semantic()
        test_dict_semantic()
        test_object_semantic()
        test_from_string_classmethod()
        test_edge_cases()
        test_backward_compatibility()
        
        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED")
        print("=" * 60)
        print("\nThe semantic action bug fix is working correctly!")
        print("You can now run exploration without AttributeError exceptions.")
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
