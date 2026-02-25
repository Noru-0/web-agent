#!/usr/bin/env python3
"""
Test robust JSON extraction from LLM responses.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from exploration.analyzer.screen_analyzer import ScreenAnalyzer
import logging
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_json_extraction():
    """Test JSON extraction with various response formats."""
    
    analyzer = ScreenAnalyzer()
    
    test_cases = [
        # Case 1: Clean JSON (baseline - should work)
        {
            "name": "Clean JSON",
            "input": '{"screen_summary": "Test page", "semantic_actions": []}',
            "should_pass": True
        },
        
        # Case 2: JSON with markdown code fence
        {
            "name": "Markdown fence (```json)",
            "input": '''```json
{
  "screen_summary": "Test page with fence",
  "semantic_actions": []
}
```''',
            "should_pass": True
        },
        
        # Case 3: JSON with generic markdown fence
        {
            "name": "Generic markdown fence (```)",
            "input": '''```
{
  "screen_summary": "Test page with fence",
  "semantic_actions": []
}
```''',
            "should_pass": True
        },
        
        # Case 4: JSON with text before
        {
            "name": "Text before JSON",
            "input": '''Here's the analysis:

{
  "screen_summary": "Test page",
  "semantic_actions": []
}''',
            "should_pass": True
        },
        
        # Case 5: JSON with text after
        {
            "name": "Text after JSON",
            "input": '''{
  "screen_summary": "Test page",
  "semantic_actions": []
}

Hope this helps!''',
            "should_pass": True
        },
        
        # Case 6: Complex nested JSON
        {
            "name": "Nested JSON structure",
            "input": '''{
  "screen_summary": "E-commerce page",
  "semantic_actions": [
    {
      "intent": "search",
      "object": "products",
      "description": "type query in search field",
      "confidence": 0.9,
      "grounding_hints": {
        "target_role": "searchbox",
        "keywords": ["search", "find"]
      }
    }
  ]
}''',
            "should_pass": True
        },
        
        # Case 7: Markdown fence with explanation
        {
            "name": "Fence with explanation",
            "input": '''Sure! Here's the analysis:

```json
{
  "screen_summary": "Shopping cart page",
  "semantic_actions": [
    {
      "intent": "checkout",
      "object": "cart",
      "confidence": 0.85
    }
  ]
}
```

This JSON contains the screen analysis.''',
            "should_pass": True
        }
    ]
    
    print("\n" + "="*70)
    print("TESTING JSON EXTRACTION")
    print("="*70)
    
    passed = 0
    failed = 0
    
    for i, test in enumerate(test_cases, 1):
        print(f"\n[Test {i}] {test['name']}")
        print("-" * 70)
        
        try:
            # Extract JSON
            clean_json = analyzer._extract_json_from_response(test['input'])
            
            # Try to parse it
            result = json.loads(clean_json)
            
            # Validate structure
            assert "screen_summary" in result, "Missing screen_summary"
            assert "semantic_actions" in result, "Missing semantic_actions"
            
            print("✅ PASSED")
            print(f"   Summary: {result['screen_summary']}")
            print(f"   Actions: {len(result['semantic_actions'])}")
            
            if test['should_pass']:
                passed += 1
            else:
                print("   ⚠️  Expected to fail but passed!")
                failed += 1
                
        except Exception as e:
            if test['should_pass']:
                print(f"❌ FAILED: {e}")
                print(f"   Input preview: {test['input'][:100]}...")
                failed += 1
            else:
                print(f"✅ Expected failure: {e}")
                passed += 1
    
    print("\n" + "="*70)
    print(f"RESULTS: {passed} passed, {failed} failed out of {len(test_cases)} tests")
    print("="*70)
    
    return failed == 0


if __name__ == "__main__":
    success = test_json_extraction()
    sys.exit(0 if success else 1)
