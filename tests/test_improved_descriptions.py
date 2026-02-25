#!/usr/bin/env python3
"""
Test improved semantic descriptions.
Quick test to verify LLM generates specific descriptions.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from exploration.analyzer.screen_analyzer import ScreenAnalyzer
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_description_quality():
    """Test that analyzer generates specific descriptions."""
    
    # Sample HTML with search box
    html = """
    <html>
    <body>
        <header>
            <input type="search" placeholder="Search products..." name="q">
            <button type="submit">Search</button>
        </header>
        <main>
            <div class="product-card">
                <h3>Product Name</h3>
                <a href="/product/1">View Details</a>
                <button>Add to Cart</button>
            </div>
        </main>
    </body>
    </html>
    """
    
    visible_text = "Search products... Search View Details Add to Cart"
    
    try:
        analyzer = ScreenAnalyzer()
        
        logger.info("Analyzing screen...")
        summary, screen_type, actions = analyzer.analyze_screen(
            url="http://example.com",
            dom_snapshot=html,
            visible_text=visible_text
        )
        
        logger.info(f"\n{'='*60}")
        logger.info(f"Screen Summary: {summary}")
        logger.info(f"Screen Type: {screen_type}")
        logger.info(f"\nActions ({len(actions)}):")
        logger.info(f"{'='*60}")
        
        for i, action in enumerate(actions, 1):
            logger.info(f"\n{i}. {action.description}")
            logger.info(f"   Intent: {action.intent}")
            logger.info(f"   Object: {action.object}")
            logger.info(f"   Confidence: {action.confidence}")
            
            if action.grounding_hints:
                logger.info(f"   Hints:")
                logger.info(f"     - Target role: {action.grounding_hints.target_role}")
                logger.info(f"     - Keywords: {action.grounding_hints.keywords}")
                logger.info(f"     - Region: {action.grounding_hints.preferred_region}")
            
            # Check if description is specific
            desc_lower = action.description.lower()
            has_element_type = any(word in desc_lower for word in ['button', 'input', 'link', 'dropdown', 'field'])
            has_action_type = any(word in desc_lower for word in ['click', 'type', 'select', 'enter'])
            
            if has_element_type and has_action_type:
                logger.info(f"   ✅ Description is SPECIFIC")
            else:
                logger.warning(f"   ⚠️  Description may be too generic")
        
        logger.info(f"\n{'='*60}")
        logger.info(f"Test complete!")
        
        return actions
        
    except Exception as e:
        logger.error(f"Error during test: {e}", exc_info=True)
        return []


if __name__ == "__main__":
    print("\n" + "="*60)
    print("TESTING IMPROVED SEMANTIC DESCRIPTIONS")
    print("="*60)
    
    actions = test_description_quality()
    
    if actions:
        print(f"\n✓ Generated {len(actions)} actions")
        print("\nCheck logs above to verify descriptions are specific")
        print("(should include element type + action type + location)")
    else:
        print("\n⚠ No actions generated or test failed")
        print("Check logs for errors")
