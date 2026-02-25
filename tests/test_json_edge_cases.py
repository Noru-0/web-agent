#!/usr/bin/env python3
"""
Test edge cases for JSON extraction from LLM responses.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from exploration.analyzer.screen_analyzer import ScreenAnalyzer
import logging
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_edge_cases():
    """Test JSON extraction with edge cases."""
    
    analyzer = ScreenAnalyzer()
    
    test_cases = [
        # Edge Case 1: JSON with braces in string values
        {
            "name": "Braces in strings",
            "input": '''{
  "screen_summary": "Page with {special} characters",
  "semantic_actions": [
    {
      "intent": "click",
      "object": "button with } brace",
      "description": "click the {settings} button"
    }
  ]
}''',
            "should_pass": True
        },
        
        # Edge Case 2: Escaped quotes in strings
        {
            "name": "Escaped quotes",
            "input": '''{
  "screen_summary": "Page with \\"quotes\\" in text",
  "semantic_actions": []
}''',
            "should_pass": True
        },
        
        # Edge Case 3: Multiple JSON objects (should extract first)
        {
            "name": "Multiple JSON objects", 
            "input": '''{"screen_summary": "First page", "semantic_actions": []}

{"screen_summary": "Second page", "semantic_actions": []}''',
            "should_pass": True,
            "expected_summary": "First page"
        },
        
        # Edge Case 4: JSON after multi-line explanation
        {
            "name": "Multi-line explanation before JSON",
            "input": '''Based on the provided DOM structure and visible text,
I'll analyze the screen and extract semantic actions.

Here is my analysis:

```json
{
  "screen_summary": "Login page with form",
  "semantic_actions": [
    {
      "intent": "authenticate",
      "object": "user account"
    }
  ]
}
```''',
            "should_pass": True
        },
        
        # Edge Case 5: Whitespace variations
        {
            "name": "Various whitespace",
            "input": '''   
            
{    "screen_summary"   :   "Test"  ,  "semantic_actions"  :  [ ]   }

            ''',
            "should_pass": True
        },
        
        # Edge Case 6: Real-world Llama 3.3 response format
        {
            "name": "Real Llama 3.3 format",
            "input": '''Sure, I'd be happy to help! Here's the analysis:

```json
{
  "screen_summary": "E-commerce product listing page with search functionality",
  "semantic_actions": [
    {
      "intent": "search",
      "object": "products",
      "context": "product catalog",
      "description": "type search query into search input field in header",
      "confidence": 0.9,
      "grounding_hints": {
        "target_role": "searchbox",
        "keywords": ["search", "find", "query"],
        "preferred_region": "header"
      }
    },
    {
      "intent": "filter",
      "object": "results",
      "context": "product listing",
      "description": "select category from dropdown to filter products",
      "confidence": 0.85,
      "grounding_hints": {
        "target_role": "combobox",
        "keywords": ["category", "filter"],
        "preferred_region": "sidebar"
      }
    }
  ]
}
```

This analysis captures the main interactive elements on the page.''',
            "should_pass": True
        }
    ]
    
    print("\n" + "="*70)
    print("TESTING EDGE CASES")
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
            
            # Check expected summary if specified
            if 'expected_summary' in test:
                assert result['screen_summary'] == test['expected_summary'], \
                    f"Expected '{test['expected_summary']}', got '{result['screen_summary']}'"
            
            print("✅ PASSED")
            print(f"   Summary: {result['screen_summary'][:60]}...")
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
    success = test_edge_cases()
    sys.exit(0 if success else 1)
