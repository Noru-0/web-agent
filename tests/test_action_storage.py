#!/usr/bin/env python3
"""
Quick test to verify actions.jsonl is created during exploration.
"""

import asyncio
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from exploration.storage import ExplorationStorage


async def test_action_storage():
    """Test that actions are saved during exploration."""
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    # Create temporary storage with auto_clean=True
    storage = ExplorationStorage("test_actions", auto_clean=True)
    
    logger.info(f"Storage directory: {storage.output_dir}")
    logger.info(f"Actions file: {storage.actions_file}")
    
    # Check if actions file will be created (it shouldn't exist yet after clean)
    if storage.actions_file.exists():
        logger.warning(f"Actions file already exists: {storage.actions_file}")
    else:
        logger.info("Actions file doesn't exist yet (expected after auto_clean)")
    
    # Create a simple mock test
    from exploration.schema import Action, ActionSemantic
    from exploration.executable_schema import ActionExecutable, ActionType
    
    # Create a test action
    semantic = ActionSemantic(
        intent="click",
        object="button",
        context=None,
        description="Test action",
        confidence=0.9,
        action_id="test_action_001"
    )
    
    executable = ActionExecutable(
        action_id="test_action_001",
        type=ActionType.CLICK,
        selector="button.test"
    )
    
    action = Action(
        action_id="test_action_001",
        semantic=semantic,
        executable=executable,
        source_screen_id="test_screen",
        confidence=0.9
    )
    
    # Save the action
    logger.info("Saving test action...")
    storage.save_action(action)
    
    # Check if file was created
    if storage.actions_file.exists():
        logger.info(f"✅ SUCCESS: Actions file created at {storage.actions_file}")
        
        # Read and verify content
        with open(storage.actions_file, 'r') as f:
            content = f.read()
            logger.info(f"File content:\n{content}")
        
        return True
    else:
        logger.error(f"❌ FAILED: Actions file not created")
        return False


if __name__ == "__main__":
    success = asyncio.run(test_action_storage())
    sys.exit(0 if success else 1)
