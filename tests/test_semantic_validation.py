"""
Test script to verify semantic-only control enforcement.

Run this to validate that the system correctly rejects executable
data leakage into semantic representations.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from exploration.validation import (
    validate_semantic_only,
    assert_no_selectors,
    filter_semantic_fields,
    FORBIDDEN_EXECUTABLE_FIELDS
)


def test_valid_semantic_data():
    """Test that valid semantic data passes."""
    print("Test 1: Valid semantic data...")
    
    semantic_action = {
        "action_id": "act_001",
        "intent": "search",
        "object": "items",
        "context": "via text input",
        "description": "search items via text input",
        "confidence": 0.85
    }
    
    try:
        result = validate_semantic_only(semantic_action, "test_action")
        print(f"  ✓ PASSED: Valid semantic data accepted (result={result})")
        return True
    except ValueError as e:
        print(f"  ✗ FAILED: Valid data rejected: {e}")
        return False


def test_invalid_with_selector():
    """Test that data with selector is rejected."""
    print("\nTest 2: Invalid data with selector...")
    
    bad_action = {
        "action_id": "act_002",
        "intent": "click",
        "object": "button",
        "selector": "#submit-btn",  # FORBIDDEN
        "description": "click button"
    }
    
    try:
        validate_semantic_only(bad_action, "bad_action", raise_on_violation=True)
        print("  ✗ FAILED: Selector not detected")
        return False
    except ValueError as e:
        print(f"  ✓ PASSED: Selector correctly rejected")
        print(f"    Error (expected): {str(e)[:100]}...")
        return True


def test_invalid_with_xpath():
    """Test that data with xpath is rejected."""
    print("\nTest 3: Invalid data with xpath...")
    
    bad_action = {
        "intent": "navigate",
        "xpath": "//div[@id='main']/button",  # FORBIDDEN
    }
    
    try:
        validate_semantic_only(bad_action, "bad_action_xpath", raise_on_violation=True)
        print("  ✗ FAILED: XPath not detected")
        return False
    except ValueError as e:
        print(f"  ✓ PASSED: XPath correctly rejected")
        return True


def test_nested_violation():
    """Test that nested executable fields are detected."""
    print("\nTest 4: Nested executable field...")
    
    screen_data = {
        "screen_id": "scr_001",
        "semantic_summary": "Homepage",
        "available_actions": [
            {
                "intent": "search",
                "description": "search items"
            },
            {
                "intent": "click",
                "selector": "button.submit"  # FORBIDDEN (nested)
            }
        ]
    }
    
    try:
        validate_semantic_only(screen_data, "screen_with_actions", raise_on_violation=True)
        print("  ✗ FAILED: Nested selector not detected")
        return False
    except ValueError as e:
        print(f"  ✓ PASSED: Nested selector correctly rejected")
        return True


def test_assert_no_selectors():
    """Test the assert_no_selectors helper."""
    print("\nTest 5: assert_no_selectors helper...")
    
    # Should pass
    good_data = {"intent": "search", "object": "items"}
    try:
        assert_no_selectors(good_data)
        print("  ✓ PASSED: Clean data accepted")
    except AssertionError as e:
        print(f"  ✗ FAILED: Clean data rejected: {e}")
        return False
    
    # Should fail
    bad_data = {"intent": "click", "selector": "#btn"}
    try:
        assert_no_selectors(bad_data, "Test assertion")
        print("  ✗ FAILED: Selector not caught by assertion")
        return False
    except AssertionError as e:
        print(f"  ✓ PASSED: Assertion correctly raised")
        return True


def test_filter_semantic_fields():
    """Test the semantic field filter."""
    print("\nTest 6: filter_semantic_fields helper...")
    
    mixed_data = {
        "action_id": "act_001",
        "intent": "search",
        "object": "items",
        "selector": "#search",  # Should be removed
        "xpath": "//input",  # Should be removed
        "description": "search items",
        "confidence": 0.9
    }
    
    filtered = filter_semantic_fields(mixed_data)
    
    # Check semantic fields present
    if "intent" not in filtered or "object" not in filtered:
        print("  ✗ FAILED: Semantic fields removed")
        return False
    
    # Check executable fields removed
    if "selector" in filtered or "xpath" in filtered:
        print("  ✗ FAILED: Executable fields not removed")
        return False
    
    print(f"  ✓ PASSED: Filtered correctly")
    print(f"    Original keys: {set(mixed_data.keys())}")
    print(f"    Filtered keys: {set(filtered.keys())}")
    return True


def test_forbidden_fields_list():
    """Test that forbidden fields list is comprehensive."""
    print("\nTest 7: Forbidden fields comprehensive...")
    
    expected_forbidden = {
        'selector', 'xpath', 'coordinates', 'dom_snapshot',
        'element_id', 'element_text', 'element_type'
    }
    
    missing = expected_forbidden - FORBIDDEN_EXECUTABLE_FIELDS
    if missing:
        print(f"  ⚠ WARNING: Missing forbidden fields: {missing}")
        return False
    
    print(f"  ✓ PASSED: All expected fields forbidden")
    print(f"    Total forbidden fields: {len(FORBIDDEN_EXECUTABLE_FIELDS)}")
    return True


def main():
    """Run all tests."""
    print("="*70)
    print("SEMANTIC-ONLY CONTROL VALIDATION TESTS")
    print("="*70)
    
    tests = [
        test_valid_semantic_data,
        test_invalid_with_selector,
        test_invalid_with_xpath,
        test_nested_violation,
        test_assert_no_selectors,
        test_filter_semantic_fields,
        test_forbidden_fields_list,
    ]
    
    results = []
    for test_func in tests:
        try:
            result = test_func()
            results.append(result)
        except Exception as e:
            print(f"  ✗ ERROR: Test crashed: {e}")
            results.append(False)
    
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    passed = sum(results)
    total = len(results)
    print(f"Passed: {passed}/{total}")
    
    if passed == total:
        print("\n✓ ALL TESTS PASSED")
        print("\nSemantic-only control is properly enforced.")
        print("The system will reject any executable data leakage.")
        return 0
    else:
        print(f"\n✗ {total - passed} TESTS FAILED")
        print("\nValidation enforcement may be incomplete.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
