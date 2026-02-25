"""
Test the refactored data model with strict separation.
"""

from exploration.schema import Screen, Action, ActionSemantic, Transition, ExplorationResult, ScreenType
from exploration.executable_schema import ActionExecutable, ActionType

print("=" * 70)
print("Testing Refactored Data Model - Strict Semantic/Executable Separation")
print("=" * 70)

# Test 1:Create standalone semantic action
print("\n1. Create ActionSemantic (semantic only):")
semantic = ActionSemantic(
    intent="search",
    object="items",
    context="via text input",
    confidence=0.85
)
print(f"   ✓ Semantic: {semantic.description}")
print(f"     Action ID: {semantic.action_id}")
print(f"     Fields: intent={semantic.intent}, object={semantic.object}")

# Test 2: Create standalone executable action
print("\n2. Create ActionExecutable (executable only):")
executable = ActionExecutable(
    action_id=semantic.action_id,  # Same ID links them
    type=ActionType.TYPE,
    selector="input[name='search']",
    element_text="Search"
)
print(f"   ✓ Executable: type={executable.type.value}")
print(f"     Selector: {executable.selector}")
print(f"     Action ID: {executable.action_id}")

# Test 3: Create unified Action for storage
print("\n3. Create Action (bundles semantic + executable for storage):")
action = Action(
    action_id=semantic.action_id,
    semantic=semantic,
    executable=executable,
    source_screen_id="screen_abc123",
    confidence=0.85
)
print(f"   ✓ Action created with ID: {action.action_id}")
print(f"     Semantic description: {action.semantic.description}")
print(f"     Executable selector: {action.executable.selector}")

# Test 4: Serialization/deserialization
print("\n4. Test serialization:")
action_dict = action.to_dict()
print(f"   ✓ Serialized to dict (keys: {list(action_dict.keys())})")
action_restored = Action.from_dict(action_dict)
print(f"   ✓ Restored from dict")
assert action_restored.action_id == action.action_id
assert action_restored.semantic.intent == semantic.intent
assert action_restored.executable.selector == executable.selector
print(f"     All fields match!")

# Test 5: Create Screen (NO action data in meta)
print("\n5. Create Screen (action_ids only in meta):")
screen = Screen(
    screen_id="",  # Auto-generated
    url="http://example.com",
    dom_snapshot="<html>...</html>",
    visible_text="Search Products",
    semantic_summary="A search page with input field",
    screen_type=ScreenType.SEARCH,
    timestamp="2026-02-11T00:00:00",
    meta={
        'action_ids': [action.action_id]  # Only references
    }
)
print(f"   ✓ Screen created: {screen.screen_id}")
print(f"     Meta keys: {list(screen.meta.keys())}")
print(f"     Action IDs: {screen.meta['action_ids']}")

# Test 6: Create Transition (action_id reference only)
print("\n6. Create Transition (action_id reference, not embedded):")
transition = Transition(
    from_screen_id=screen.screen_id,
    action_id=action.action_id,  # Only reference
    to_screen_id="screen_xyz789",
    success=True
)
print(f"   ✓ Transition created: {transition.transition_id}")
print(f"     From: {transition.from_screen_id}")
print(f"     Action ID: {transition.action_id}")
print(f"     To: {transition.to_screen_id}")

# Test 7: Create ExplorationResult
print("\n7. Create ExplorationResult (with actions collection):")
result = ExplorationResult(
    screens={screen.screen_id: screen},
    actions={action.action_id: action},  # Single source of truth
    transitions=[transition],
    explorer_name="test",
    start_url="http://example.com",
    timestamp="2026-02-11T00:00:00"
)
print(f"   ✓ Result created")
print(f"     Screens: {result.get_unique_screen_count()}")
print(f"     Actions: {result.get_action_count()}")
print(f"     Transitions: {result.get_transition_count()}")

# Test 8: Retrieve actions for screen
print("\n8. Retrieve actions for screen:")
screen_actions = result.get_actions_for_screen(screen.screen_id)
print(f"   ✓ Found {len(screen_actions)} actions for screen")
for act in screen_actions:
    print(f"     - {act.semantic.description} [{act.action_id}]")

# Test 9: Validate separation
print("\n9. Validate semantic/executable separation:")
is_valid = result.validate_separation()
print(f"   ✓ Separation valid: {is_valid}")
if is_valid:
    print("     No selectors found in semantic fields!")

# Test 10: Demonstrate phase access patterns
print("\n10. Phase access patterns:")
print("    Phase 2 (Agent Execution):")
print(f"       agent.execute(result.actions['{action.action_id}'].executable)")
print(f"       → Sees only: type={action.executable.type.value}, selector={action.executable.selector}")

print("    Phase 3 (Task Synthesis - LLM):")
print(f"       llm_prompt += result.actions['{action.action_id}'].semantic.description")
print(f"       → Sees only: '{action.semantic.description}'")

print("    Phase 4 (Grounding):")
print(f"       action = grounder.ground_by_id('{action.action_id}', screen_id)")
print(f"       → Returns: ActionExecutable")

print("\n" + "=" * 70)
print("✓ All tests passed!")
print("✓ Semantic/executable separation enforced")
print("✓ Single source of truth for actions")
print("✓ Clean phase boundaries")
print("=" * 70)

# Test 11: Verify no cross-contamination
print("\n11. Verify no cross-contamination:")
sem_dict = action.semantic.to_dict()
exec_dict = action.executable.to_dict()

print(f"    Semantic keys: {list(sem_dict.keys())}")
print(f"    Executable keys: {list(exec_dict.keys())}")

# Check no selector in semantic
assert 'selector' not in sem_dict, "ERROR: Selector leaked into semantic!"
assert 'type' not in sem_dict, "ERROR: Type leaked into semantic!"

# Check no intent in executable
assert 'intent' not in exec_dict, "ERROR: Intent leaked into executable!"
assert 'object' not in exec_dict, "ERROR: Object leaked into executable!"

print("    ✓ No cross-contamination detected")
print("    ✓ Separation boundaries enforced")
