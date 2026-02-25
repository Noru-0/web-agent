#!/usr/bin/env python3
"""
Test validation screen detection for fail-repair trajectories.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from exploration.dedup import ScreenDeduplicator
from exploration.schema import Screen, ScreenType
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_test_screen(url: str, dom: str, text: str, summary: str) -> Screen:
    """Helper to create test screen."""
    return Screen(
        screen_id="",  # Will be auto-generated in __post_init__
        url=url,
        dom_snapshot=dom,
        visible_text=text,
        semantic_summary=summary,
        screen_type=ScreenType.FORM,
        timestamp=datetime.now().isoformat()
    )


def test_validation_detection():
    """Test validation screen detection logic."""
    
    deduplicator = ScreenDeduplicator(similarity_threshold=0.85)
    
    print("\n" + "="*70)
    print("TESTING VALIDATION SCREEN DETECTION")
    print("="*70)
    
    # Test Case 1: Normal form → validation error (SHOULD DETECT)
    print("\n[Test 1] Form submission → Validation error")
    print("-" * 70)
    
    form_screen = create_test_screen(
        url="http://shop.com/checkout",
        dom="<form><input name='email'/><button>Submit</button></form>",
        text="Email Address Submit",
        summary="Checkout form with email field"
    )
    
    error_screen = create_test_screen(
        url="http://shop.com/checkout",  # Same URL
        dom="<form><input name='email'/><button>Submit</button><div class='error'>Email is required</div></form>",
        text="Email Address Submit Email is required",  # Error appeared
        summary="Checkout form with validation error"
    )
    
    is_validation = deduplicator.is_validation_screen(form_screen, error_screen)
    print(f"   Result: {'✅ VALIDATION DETECTED' if is_validation else '❌ NOT DETECTED'}")
    print(f"   URL same: Yes")
    print(f"   DOM changed: Yes (error message added)")
    print(f"   Has keywords: Yes ('required')")
    assert is_validation, "Should detect validation screen"
    
    # Test Case 2: Navigation to different page (SHOULD NOT DETECT)
    print("\n[Test 2] Navigation to different page")
    print("-" * 70)
    
    product_screen = create_test_screen(
        url="http://shop.com/product/123",
        dom="<div class='product'><h1>Product Name</h1></div>",
        text="Product Name Add to Cart",
        summary="Product detail page"
    )
    
    cart_screen = create_test_screen(
        url="http://shop.com/cart",  # Different URL
        dom="<div class='cart'><h1>Shopping Cart</h1></div>",
        text="Shopping Cart Checkout",
        summary="Shopping cart page"
    )
    
    is_validation = deduplicator.is_validation_screen(product_screen, cart_screen)
    print(f"   Result: {'❌ INCORRECTLY DETECTED' if is_validation else '✅ NOT VALIDATION'}")
    print(f"   URL same: No (different page)")
    print(f"   Should be: Normal navigation")
    assert not is_validation, "Should not detect validation for navigation"
    
    # Test Case 3: Same screen, no changes (SHOULD NOT DETECT)
    print("\n[Test 3] Same screen, no changes")
    print("-" * 70)
    
    screen1 = create_test_screen(
        url="http://shop.com/products",
        dom="<div>Product List</div>",
        text="Product List",
        summary="Product listing page"
    )
    
    screen2 = create_test_screen(
        url="http://shop.com/products",
        dom="<div>Product List</div>",  # Exact same DOM
        text="Product List",  # Same text
        summary="Product listing page"
    )
    
    is_validation = deduplicator.is_validation_screen(screen1, screen2)
    print(f"   Result: {'❌ INCORRECTLY DETECTED' if is_validation else '✅ NOT VALIDATION'}")
    print(f"   URL same: Yes")
    print(f"   DOM changed: No")
    print(f"   Should be: Exact duplicate")
    assert not is_validation, "Should not detect validation when nothing changed"
    
    # Test Case 4: Multiple validation keywords (SHOULD DETECT)
    print("\n[Test 4] Multiple validation errors")
    print("-" * 70)
    
    form2_screen = create_test_screen(
        url="http://example.com/register",
        dom="<form><input name='username'/><input name='password'/></form>",
        text="Username Password Register",
        summary="Registration form"
    )
    
    multi_error_screen = create_test_screen(
        url="http://example.com/register",
        dom="<form><input name='username'/><p>Username is required</p><input name='password'/><p>Password must be at least 8 characters</p></form>",
        text="Username Username is required Password Password must be at least 8 characters Register",
        summary="Registration form with validation errors"
    )
    
    is_validation = deduplicator.is_validation_screen(form2_screen, multi_error_screen)
    print(f"   Result: {'✅ VALIDATION DETECTED' if is_validation else '❌ NOT DETECTED'}")
    print(f"   Keywords found: 'required', 'must'")
    assert is_validation, "Should detect validation with multiple errors"
    
    # Test Case 5: DOM changed but no validation keywords (SHOULD NOT DETECT)
    print("\n[Test 5] DOM changed but no validation")
    print("-" * 70)
    
    list1_screen = create_test_screen(
        url="http://shop.com/products?page=1",
        dom="<div>Product 1, Product 2</div>",
        text="Product 1 Product 2",
        summary="Product list page 1"
    )
    
    list2_screen = create_test_screen(
        url="http://shop.com/products?page=2",  # Similar URL
        dom="<div>Product 3, Product 4</div>",  # Different content
        text="Product 3 Product 4",
        summary="Product list page 2"
    )
    
    is_validation = deduplicator.is_validation_screen(list1_screen, list2_screen)
    print(f"   Result: {'❌ INCORRECTLY DETECTED' if is_validation else '✅ NOT VALIDATION'}")
    print(f"   URL similar: Yes")
    print(f"   DOM changed: Yes")
    print(f"   Has keywords: No")
    assert not is_validation, "Should not detect validation without keywords"
    
    print("\n" + "="*70)
    print("✅ ALL TESTS PASSED")
    print("="*70)


def test_deduplication_with_validation():
    """Test that validation screens bypass similarity threshold."""
    
    print("\n" + "="*70)
    print("TESTING DEDUPLICATION WITH VALIDATION SCREENS")
    print("="*70)
    
    deduplicator = ScreenDeduplicator(similarity_threshold=0.90)
    
    # Add initial form screen
    print("\n[Step 1] Add initial form screen")
    form_screen = create_test_screen(
        url="http://shop.com/checkout",
        dom="<form><input name='email'/><button>Submit</button></form>",
        text="Email Submit",
        summary="Checkout form"
    )
    
    canonical_id, is_new = deduplicator.add_screen(form_screen, previous_screen=None)
    print(f"   Screen ID: {canonical_id[:8]}...")
    print(f"   Is new: {is_new}")
    assert is_new, "First screen should be new"
    
    # Add validation error screen (should be NEW despite high similarity)
    print("\n[Step 2] Add validation error screen")
    error_screen = create_test_screen(
        url="http://shop.com/checkout",  # Same URL
        dom="<form><input name='email'/><button>Submit</button><div class='error'>Email is required</div></form>",
        text="Email Submit Email is required",
        summary="Checkout form with error"  # Very similar summary
    )
    
    canonical_id2, is_new2 = deduplicator.add_screen(error_screen, previous_screen=form_screen)
    print(f"   Screen ID: {canonical_id2[:8]}...")
    print(f"   Is new: {is_new2}")
    print(f"   Validation detected: {deduplicator.is_validation_screen(form_screen, error_screen)}")
    
    assert is_new2, "Validation screen should be treated as NEW"
    assert canonical_id != canonical_id2, "Should have different screen IDs"
    
    # Add another similar form (without validation) - should be DUPLICATE
    print("\n[Step 3] Add similar form without validation")
    similar_form = create_test_screen(
        url="http://shop.com/checkout",
        dom="<form><input name='email'/><button>Submit</button></form>",
        text="Email Submit",
        summary="Checkout form page"  # Slightly different summary to get different screen_id
    )
    
    canonical_id3, is_new3 = deduplicator.add_screen(similar_form, previous_screen=error_screen)
    print(f"   Screen ID: {canonical_id3[:8]}...")
    print(f"   Is new: {is_new3}")
    
    assert not is_new3, "Non-validation duplicate should be detected"
    assert canonical_id3 == canonical_id, "Should map to original screen"
    
    stats = deduplicator.get_stats()
    print("\n[Final Stats]")
    print(f"   Unique screens: {stats['unique_screens']}")
    print(f"   Total screens: {stats['total_screens_seen']}")
    print(f"   Duplicates: {stats['duplicates_found']}")
    
    assert stats['unique_screens'] == 2, "Should have 2 unique screens (form + error)"
    assert stats['total_screens_seen'] == 3, "Should have seen 3 screens total"
    assert stats['duplicates_found'] == 1, "Should have 1 duplicate (similar_form)"
    
    print("\n" + "="*70)
    print("✅ DEDUPLICATION WITH VALIDATION WORKS CORRECTLY")
    print("="*70)


if __name__ == "__main__":
    try:
        test_validation_detection()
        test_deduplication_with_validation()
        print("\n🎉 ALL TESTS PASSED - Fail-repair trajectories preserved!\n")
        sys.exit(0)
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}\n")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}\n")
        import traceback
        traceback.print_exc()
        sys.exit(1)
