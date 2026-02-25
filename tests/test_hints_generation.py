#!/usr/bin/env python3
"""
Test if LLM is generating hints properly.
"""

import json
from exploration.analyzer import ScreenAnalyzer

def test_hints():
    """Test hint generation on a sample screen."""
    
    # Sample screen data
    url = "http://localhost:9999"
    visible_text = """
    Home | Products | Cart | Login
    
    Search: [                    ] [Go]
    
    Featured Products:
    - Product A - $10 [View Details]
    - Product B - $20 [View Details]
    - Product C - $30 [View Details]
    
    Categories: Electronics, Clothing, Books
    """
    
    dom_snapshot = """
    <header>
        <nav><a>Home</a> <a>Products</a> <a>Cart</a> <a>Login</a></nav>
    </header>
    <main>
        <div class="search-box">
            <input id="search-input" placeholder="Search">
            <button id="search-btn">Go</button>
        </div>
        <section class="products">
            <div class="product"><h3>Product A</h3><p>$10</p><a>View Details</a></div>
            <div class="product"><h3>Product B</h3><p>$20</p><a>View Details</a></div>
            <div class="product"><h3>Product C</h3><p>$30</p><a>View Details</a></div>
        </section>
        <aside class="categories">
            <a>Electronics</a> <a>Clothing</a> <a>Books</a>
        </aside>
    </main>
    """
    
    print("="*60)
    print("Testing LLM Hint Generation")
    print("="*60)
    
    analyzer = ScreenAnalyzer()
    
    try:
        summary, screen_type, action_semantics = analyzer.analyze_screen(
            url=url,
            visible_text=visible_text,
            dom_snapshot=dom_snapshot
        )
        
        print(f"\nScreen Summary: {summary}")
        print(f"Screen Type: {screen_type}")
        print(f"\nActions found: {len(action_semantics)}")
        
        for i, action in enumerate(action_semantics, 1):
            print(f"\n--- Action {i} ---")
            print(f"Intent: {action.intent}")
            print(f"Object: {action.object}")
            print(f"Description: {action.description}")
            print(f"Confidence: {action.confidence}")
            
            if action.grounding_hints:
                print(f"\n✓ Grounding hints present!")
                print(f"  Target role: {action.grounding_hints.target_role}")
                print(f"  Element affordance: {action.grounding_hints.element_affordance}")
                print(f"  Keywords: {action.grounding_hints.keywords}")
                print(f"  Exclude keywords: {action.grounding_hints.exclude_keywords}")
                print(f"  Preferred region: {action.grounding_hints.preferred_region}")
                print(f"  Interaction order: {action.grounding_hints.interaction_order}")
                print(f"  Sub-instance: {action.grounding_hints.sub_instance}")
            else:
                print(f"\n✗ NO GROUNDING HINTS - LLM did not generate hints")
        
        print("\n" + "="*60)
        print("Debug: Full result")
        print("="*60)
        print(json.dumps({
            'summary': summary,
            'screen_type': str(screen_type),
            'actions': [
                {
                    'semantic': {
                        'intent': a.intent,
                        'object': a.object,
                        'description': a.description,
                        'confidence': a.confidence,
                        'grounding_hints': a.grounding_hints.to_dict() if a.grounding_hints else None
                    }
                }
                for a in action_semantics
            ]
        }, indent=2))
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_hints()
