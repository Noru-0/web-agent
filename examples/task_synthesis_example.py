"""
Example: Task Synthesis from Exploration Results

Demonstrates how to use TaskSynthesizer to infer high-level user tasks
from semantic actions discovered during exploration.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from exploration import (
    Screen,
    ActionSemantic,
    ScreenType,
    TaskSynthesizer,
    TaskPriority
)


def create_example_screens():
    """Create example screens with semantic actions for demonstration"""
    
    # Screen 1: Homepage
    homepage = Screen(
        screen_id="screen_001",
        url="https://example.com",
        dom_snapshot="<html>...</html>",
        visible_text="Welcome to Example Store. Search for products...",
        semantic_summary="E-commerce homepage with search functionality",
        screen_type=ScreenType.HOMEPAGE,
        timestamp="2026-02-24T10:00:00"
    )
    
    # Add actions to homepage
    homepage.actions = [
        ActionSemantic(
            intent="search",
            object="products",
            context="via search input",
            confidence=0.9,
            action_id="a_001"
        ),
        ActionSemantic(
            intent="navigate",
            object="categories",
            context="main menu",
            confidence=0.85,
            action_id="a_002"
        )
    ]
    
    # Screen 2: Search Results
    search_results = Screen(
        screen_id="screen_002",
        url="https://example.com/search?q=laptop",
        dom_snapshot="<html>...</html>",
        visible_text="Search results for 'laptop'",
        semantic_summary="Product search results page",
        screen_type=ScreenType.SEARCH,
        timestamp="2026-02-24T10:01:00"
    )
    
    search_results.actions = [
        ActionSemantic(
            intent="filter",
            object="results",
            context="by price range",
            confidence=0.8,
            action_id="a_003"
        ),
        ActionSemantic(
            intent="view",
            object="product details",
            context="click product",
            confidence=0.9,
            action_id="a_004"
        ),
        ActionSemantic(
            intent="search",
            object="products",
            context="refine search",
            confidence=0.85,
            action_id="a_005"
        )
    ]
    
    # Screen 3: Product Detail Page
    product_detail = Screen(
        screen_id="screen_003",
        url="https://example.com/product/123",
        dom_snapshot="<html>...</html>",
        visible_text="Laptop XYZ - $999.99",
        semantic_summary="Product detail page with purchase options",
        screen_type=ScreenType.PRODUCT_DETAIL,
        timestamp="2026-02-24T10:02:00"
    )
    
    product_detail.actions = [
        ActionSemantic(
            intent="add",
            object="cart",
            context="add to shopping cart",
            confidence=0.95,
            action_id="a_006"
        ),
        ActionSemantic(
            intent="view",
            object="product details",
            context="view specifications",
            confidence=0.7,
            action_id="a_007"
        )
    ]
    
    # Screen 4: Shopping Cart
    cart = Screen(
        screen_id="screen_004",
        url="https://example.com/cart",
        dom_snapshot="<html>...</html>",
        visible_text="Shopping Cart (1 item)",
        semantic_summary="Shopping cart with checkout options",
        screen_type=ScreenType.CART,
        timestamp="2026-02-24T10:03:00"
    )
    
    cart.actions = [
        ActionSemantic(
            intent="checkout",
            object="order",
            context="proceed to checkout",
            confidence=0.95,
            action_id="a_008"
        ),
        ActionSemantic(
            intent="view_cart",
            object="items",
            context="review cart items",
            confidence=0.8,
            action_id="a_009"
        )
    ]
    
    # Screen 5: Login Page
    login = Screen(
        screen_id="screen_005",
        url="https://example.com/login",
        dom_snapshot="<html>...</html>",
        visible_text="Sign in to your account",
        semantic_summary="User authentication page",
        screen_type=ScreenType.LOGIN,
        timestamp="2026-02-24T10:04:00"
    )
    
    login.actions = [
        ActionSemantic(
            intent="sign_in",
            object="account",
            context="login form",
            confidence=0.9,
            action_id="a_010"
        ),
        ActionSemantic(
            intent="register",
            object="account",
            context="create new account",
            confidence=0.85,
            action_id="a_011"
        )
    ]
    
    return [homepage, search_results, product_detail, cart, login]


def main():
    """Run task synthesis example"""
    print("=" * 80)
    print("Task Synthesis Example - Domain-Aware Pattern Matching")
    print("=" * 80)
    print()
    
    # Create example screens
    screens = create_example_screens()
    print(f"Created {len(screens)} example screens with semantic actions")
    print()
    
    # Example 1: Auto-detection (default)
    print("=" * 80)
    print("Example 1: AUTO-DETECTION (no domain specified)")
    print("=" * 80)
    synthesizer_auto = TaskSynthesizer()
    task_graph_auto = synthesizer_auto.synthesize(screens)
    print(f"Generated {len(task_graph_auto.tasks)} tasks with auto-detection")
    print()
    
    # Example 2: Explicit e-commerce domain
    print("=" * 80)
    print("Example 2: EXPLICIT DOMAIN (ecommerce)")
    print("=" * 80)
    synthesizer_ecommerce = TaskSynthesizer(domain="ecommerce")
    task_graph_ecommerce = synthesizer_ecommerce.synthesize(screens)
    print(f"Generated {len(task_graph_ecommerce.tasks)} tasks with e-commerce patterns")
    print()
    
    # Example 3: Generic domain
    print("=" * 80)
    print("Example 3: GENERIC DOMAIN (domain-agnostic)")
    print("=" * 80)
    synthesizer_generic = TaskSynthesizer(domain="generic")
    task_graph_generic = synthesizer_generic.synthesize(screens)
    print(f"Generated {len(task_graph_generic.tasks)} tasks with generic patterns")
    print()
    
    # Example 4: Custom patterns
    print("=" * 80)
    print("Example 4: CUSTOM PATTERNS")
    print("=" * 80)
    custom_patterns = [
        (['search', 'find'], "find items", "Search for items"),
        (['add', 'save'], "save item", "Save or bookmark item"),
        (['checkout', 'buy'], "complete purchase", "Finish buying process"),
    ]
    synthesizer_custom = TaskSynthesizer(custom_patterns=custom_patterns)
    task_graph_custom = synthesizer_custom.synthesize(screens)
    print(f"Generated {len(task_graph_custom.tasks)} tasks with custom patterns")
    print()
    
    # Display detailed results from auto-detection example
    task_graph = task_graph_auto
    print("=" * 80)
    print("DETAILED RESULTS (Auto-Detection)")
    print("=" * 80)
    print()
    
    print(f"Total tasks: {len(task_graph.tasks)}")
    print(f"Total screens processed: {task_graph.meta.get('total_screens', 0)}")
    print(f"Total actions: {task_graph.meta.get('total_actions', 0)}")
    print(f"Unique actions: {task_graph.meta.get('unique_actions', 0)}")
    print()
    
    # Group tasks by priority
    for priority in [TaskPriority.INITIAL, TaskPriority.INTERMEDIATE, TaskPriority.TERMINAL]:
        priority_tasks = task_graph.get_tasks_by_priority(priority)
        if priority_tasks:
            print(f"\n{priority.value.upper()} TASKS ({len(priority_tasks)}):")
            print("-" * 80)
            for task in priority_tasks:
                print(f"  Task ID: {task.task_id}")
                print(f"  Name: {task.name}")
                print(f"  Description: {task.description}")
                print(f"  Confidence: {task.confidence:.2f}")
                print(f"  Related Actions: {len(task.related_actions)}")
                print(f"  Entry Screens: {len(task.entry_screens)}")
                print()
    
    # Export to JSON
    print("=" * 80)
    print("JSON OUTPUT")
    print("=" * 80)
    import json
    task_dict = task_graph.to_dict()
    print(json.dumps(task_dict, indent=2))


if __name__ == "__main__":
    main()
