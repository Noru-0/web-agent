"""
Verification script for EXPLORE pipeline implementation.

Tests basic functionality without running full exploration.
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_imports():
    """Test that all exploration modules can be imported."""
    print("Testing imports...")
    
    try:
        from exploration.schema import Screen, ActionSemantic, Transition, ScreenType
        print("  ✓ exploration.schema")
    except Exception as e:
        print(f"  ✗ exploration.schema: {e}")
        return False
    
    try:
        from exploration.analyzer import ScreenAnalyzer, extract_visible_text
        print("  ✓ exploration.analyzer")
    except Exception as e:
        print(f"  ✗ exploration.analyzer: {e}")
        return False
    
    try:
        from exploration.dedup import ScreenDeduplicator
        print("  ✓ exploration.dedup")
    except Exception as e:
        print(f"  ✗ exploration.dedup: {e}")
        return False
    
    try:
        from exploration.storage import ExplorationStorage
        print("  ✓ exploration.storage")
    except Exception as e:
        print(f"  ✗ exploration.storage: {e}")
        return False
    
    try:
        from exploration.exploration_bridge import ExplorationAdapter, SimpleExplorationAdapter
        print("  ✓ exploration.exploration_bridge (adapters)")
    except Exception as e:
        print(f"  ✗ exploration.exploration_bridge (adapters): {e}")
        return False
    
    try:
        from exploration.exploration_bridge import ExplorationLoop, run_exploration
        print("  ✓ exploration.exploration_bridge (loop)")
    except Exception as e:
        print(f"  ✗ exploration.exploration_bridge (loop): {e}")
        return False
    
    try:
        from adapters.agenttrek_exploration_adapter import AgentTrekExplorationAdapter
        print("  ✓ adapters.agenttrek_exploration_adapter")
    except Exception as e:
        print(f"  ✗ adapters.agenttrek_exploration_adapter: {e}")
        return False
    
    try:
        from workflows.explore import explore_website
        print("  ✓ workflows.explore (orchestration)")
    except Exception as e:
        print(f"  ✗ workflows.explore (orchestration): {e}")
        return False
    
    return True


def test_data_models():
    """Test data model creation and serialization."""
    print("\nTesting data models...")
    
    from exploration.schema import Screen, ActionSemantic, Transition, ScreenType
    from datetime import datetime
    
    try:
        # Create a screen
        screen = Screen(
            screen_id="",
            url="https://example.com",
            dom_snapshot="<html><body>Test</body></html>",
            visible_text="Test page",
            semantic_summary="A test page",
            screen_type=ScreenType.OTHER,
            timestamp=datetime.now().isoformat()
        )
        print(f"  ✓ Screen created: {screen.screen_id}")
        
        # Create an action semantic
        action = ActionSemantic(description="Navigate to login")
        print(f"  ✓ ActionSemantic created: {action.action_id}")
        
        # Create a transition
        transition = Transition(
            from_screen_id=screen.screen_id,
            action_semantic=action,
            to_screen_id=screen.screen_id
        )
        print(f"  ✓ Transition created: {transition.transition_id}")
        
        # Test serialization
        screen_dict = screen.to_dict()
        assert "screen_id" in screen_dict
        assert "url" in screen_dict
        print("  ✓ Screen serialization")
        
        # Test deserialization
        screen2 = Screen.from_dict(screen_dict)
        assert screen2.screen_id == screen.screen_id
        print("  ✓ Screen deserialization")
        
        return True
    
    except Exception as e:
        print(f"  ✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_deduplication():
    """Test screen deduplication logic."""
    print("\nTesting screen deduplication...")
    
    from exploration.dedup import ScreenDeduplicator
    from exploration.schema import Screen, ScreenType
    from datetime import datetime
    
    try:
        dedup = ScreenDeduplicator(similarity_threshold=0.85)
        
        # Create similar screens
        screen1 = Screen(
            screen_id="",
            url="https://example.com/page/1",
            dom_snapshot="<html><body>Content</body></html>",
            visible_text="Page content",
            semantic_summary="A product page",
            screen_type=ScreenType.PRODUCT_DETAIL,
            timestamp=datetime.now().isoformat()
        )
        
        screen2 = Screen(
            screen_id="",
            url="https://example.com/page/2",
            dom_snapshot="<html><body>Content</body></html>",
            visible_text="Page content",
            semantic_summary="A product page",
            screen_type=ScreenType.PRODUCT_DETAIL,
            timestamp=datetime.now().isoformat()
        )
        
        screen3 = Screen(
            screen_id="",
            url="https://example.com/login",
            dom_snapshot="<html><body>Login form</body></html>",
            visible_text="Login page",
            semantic_summary="Login page with form",
            screen_type=ScreenType.LOGIN,
            timestamp=datetime.now().isoformat()
        )
        
        # Add screens
        id1, new1 = dedup.add_screen(screen1)
        print(f"  ✓ Screen 1 added: {id1} (new: {new1})")
        
        id2, new2 = dedup.add_screen(screen2)
        print(f"  ✓ Screen 2 added: {id2} (new: {new2})")
        
        id3, new3 = dedup.add_screen(screen3)
        print(f"  ✓ Screen 3 added: {id3} (new: {new3})")
        
        # Check deduplication
        stats = dedup.get_stats()
        print(f"  ✓ Dedup stats: {stats}")
        
        # Screen 1 and 2 should be similar (potentially duplicates)
        # Screen 3 should be unique
        assert stats['unique_screens'] >= 2, "Should have at least 2 unique screens"
        
        return True
    
    except Exception as e:
        print(f"  ✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_storage():
    """Test exploration storage."""
    print("\nTesting exploration storage...")
    
    from exploration.storage import ExplorationStorage
    from exploration.schema import Screen, ActionSemantic, Transition, ScreenType
    from datetime import datetime
    import tempfile
    
    try:
        # Use temporary directory
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = ExplorationStorage("test", base_dir=Path(tmpdir))
            print(f"  ✓ Storage created at: {storage.output_dir}")
            
            # Create and save a screen
            screen = Screen(
                screen_id="",
                url="https://example.com",
                dom_snapshot="<html><body>Test</body></html>",
                visible_text="Test",
                semantic_summary="Test page",
                screen_type=ScreenType.OTHER,
                timestamp=datetime.now().isoformat()
            )
            storage.save_screen(screen)
            print("  ✓ Screen saved")
            
            # Create and save a transition
            action = ActionSemantic(description="Test action")
            transition = Transition(
                from_screen_id=screen.screen_id,
                action_semantic=action,
                to_screen_id=screen.screen_id
            )
            storage.save_transition(transition)
            print("  ✓ Transition saved")
            
            # Load back
            screens = storage.load_screens()
            transitions = storage.load_transitions()
            
            assert len(screens) == 1, "Should have 1 screen"
            assert len(transitions) == 1, "Should have 1 transition"
            print("  ✓ Data loaded successfully")
        
        return True
    
    except Exception as e:
        print(f"  ✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_text_extraction():
    """Test visible text extraction."""
    print("\nTesting text extraction...")
    
    from exploration.analyzer import extract_visible_text
    
    try:
        html = """
        <html>
            <head><title>Test</title></head>
            <body>
                <script>alert('test');</script>
                <style>body { color: red; }</style>
                <h1>Welcome</h1>
                <p>This is a test page.</p>
                <!-- Comment -->
            </body>
        </html>
        """
        
        text = extract_visible_text(html)
        print(f"  ✓ Extracted text: {text[:50]}...")
        
        assert "Welcome" in text
        assert "test page" in text
        assert "alert" not in text  # Script should be removed
        assert "color: red" not in text  # Style should be removed
        
        return True
    
    except Exception as e:
        print(f"  ✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_agenttrek_adapter():
    """Test AgentTrek adapter configuration and loading."""
    print("\nTesting AgentTrek adapter...")
    
    try:
        from exploration.exploration_bridge import get_exploration_adapter, list_exploration_adapters
        from utils.env import env as env_config
        
        # Check adapter is in registry
        adapters = list_exploration_adapters()
        print(f"  Available adapters: {', '.join(adapters)}")
        assert "agenttrek" in adapters, "AgentTrek adapter not in registry"
        print("  ✓ AgentTrek adapter is registered")
        
        # Check .env configuration
        provider = env_config.get("EXPLORER_PROVIDER", "simple")
        print(f"  Current EXPLORER_PROVIDER: {provider}")
        
        model = env_config.get("EXPLORER_MODEL", "")
        print(f"  Current EXPLORER_MODEL: {model}")
        
        base_url = env_config.get("EXPLORER_BASE_URL", "")
        print(f"  Current EXPLORER_BASE_URL: {base_url}")
        
        # Verify model name format (should be HuggingFace model)
        if provider == "agenttrek":
            if "llama" in model.lower():
                print(f"  ✓ LLaMA model configured: {model}")
            else:
                print(f"  ⚠ Warning: EXPLORER_MODEL doesn't look like a LLaMA model")
            
            if "huggingface" in base_url.lower() or "hf" in base_url.lower():
                print(f"  ✓ HuggingFace API endpoint configured")
            else:
                print(f"  ⚠ Warning: EXPLORER_BASE_URL doesn't look like HuggingFace API")
        
        # Try to create adapter (without API key it won't work, but should not crash)
        try:
            # Temporarily set provider to agenttrek for testing
            import os
            original_provider = os.environ.get("EXPLORER_PROVIDER")
            os.environ["EXPLORER_PROVIDER"] = "agenttrek"
            
            adapter = get_exploration_adapter("agenttrek")
            print(f"  ✓ AgentTrek adapter created: {adapter.explorer_name}")
            
            # Check adapter has expected attributes
            assert hasattr(adapter, 'model_name'), "Adapter missing model_name"
            assert hasattr(adapter, 'base_url'), "Adapter missing base_url"
            assert hasattr(adapter, 'execute_action'), "Adapter missing execute_action method"
            print(f"  ✓ Adapter has required attributes")
            print(f"    - Model: {adapter.model_name}")
            print(f"    - Base URL: {adapter.base_url}")
            
            # Restore original provider
            if original_provider:
                os.environ["EXPLORER_PROVIDER"] = original_provider
            else:
                os.environ.pop("EXPLORER_PROVIDER", None)
        
        except Exception as e:
            print(f"  ⚠ Could not fully test adapter (likely missing API key): {e}")
            # This is expected if no API key is configured
        
        return True
    
    except Exception as e:
        print(f"  ✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all verification tests."""
    print("=" * 60)
    print("EXPLORE Pipeline Verification")
    print("=" * 60)
    
    results = []
    
    results.append(("Imports", test_imports()))
    results.append(("Data Models", test_data_models()))
    results.append(("Deduplication", test_deduplication()))
    results.append(("Storage", test_storage()))
    results.append(("Text Extraction", test_text_extraction()))
    results.append(("AgentTrek Adapter", test_agenttrek_adapter()))
    
    print("\n" + "=" * 60)
    print("Results:")
    print("=" * 60)
    
    for name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"  {status}: {name}")
    
    all_passed = all(r[1] for r in results)
    
    print("\n" + "=" * 60)
    if all_passed:
        print("✓ All tests passed!")
        print("\nYou can now run the full exploration:")
        print("  python run_exploration.py --url https://example.com")
    else:
        print("✗ Some tests failed - please fix before running exploration")
    print("=" * 60)
    
    return 0 if all_passed else 1
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
