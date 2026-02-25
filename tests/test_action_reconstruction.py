"""
Test ActionSemantic serialization and reconstruction
"""

from exploration.schema import ActionSemantic

print("=" * 60)
print("Testing ActionSemantic Serialization/Reconstruction")
print("=" * 60)

# Create an action
action1 = ActionSemantic(
    intent="search",
    object="items",
    context="via text input",
    confidence=0.82
)

print("\n1. Original action:")
print(f"   Intent: {action1.intent}")
print(f"   Object: {action1.object}")
print(f"   Context: {action1.context}")
print(f"   Confidence: {action1.confidence}")
print(f"   Description: {action1.description}")

# Serialize to dict
action_dict = action1.to_dict()

print("\n2. Serialized to dict:")
import json
print(f"   {json.dumps(action_dict, indent=2)}")

# Reconstruct from dict
action2 = ActionSemantic.from_dict(action_dict)

print("\n3. Reconstructed action:")
print(f"   Intent: {action2.intent}")
print(f"   Object: {action2.object}")
print(f"   Context: {action2.context}")
print(f"   Confidence: {action2.confidence}")
print(f"   Description: {action2.description}")

# Verify they match
assert action1.intent == action2.intent
assert action1.object == action2.object
assert action1.context == action2.context
assert action1.confidence == action2.confidence
assert action1.description == action2.description

print("\n" + "=" * 60)
print("✓ All tests passed!")
print("✓ ActionSemantic can be serialized/reconstructed correctly")
print("=" * 60)
