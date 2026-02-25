"""
Data storage for exploration results.

Stores screens and transitions in JSONL format
for reproducibility and offline analysis.
"""

import json
import logging
import re
from pathlib import Path
from typing import List
from datetime import datetime
from urllib.parse import urlparse

from exploration.schema import Screen, Transition, ExplorationResult

logger = logging.getLogger(__name__)


def url_to_folder_name(url: str) -> str:
    """
    Convert URL to safe folder name.
    
    Examples:
        http://localhost:9999 -> localhost_9999
        https://shop.example.com -> shop.example.com
        https://example.com/path -> example.com
    
    Args:
        url: URL string
    
    Returns:
        Safe folder name
    """
    try:
        parsed = urlparse(url)
        
        # Get domain and port
        domain = parsed.netloc or parsed.hostname or "unknown"
        
        # Remove www. prefix
        domain = re.sub(r'^www\.', '', domain)
        
        # Replace : with _ for port numbers
        domain = domain.replace(':', '_')
        
        # Replace other unsafe characters
        safe_name = re.sub(r'[^a-zA-Z0-9._-]', '_', domain)
        
        # Remove trailing underscores
        safe_name = safe_name.strip('_')
        
        return safe_name or "unknown"
    
    except Exception:
        # Fallback to sanitized URL
        safe_name = re.sub(r'[^a-zA-Z0-9._-]', '_', url)
        return safe_name[:50]  # Limit length


class ExplorationStorage:
    """
    Handles storage of exploration results to disk.
    
    Writes to:
    - data/raw/<explorer_name>/screens.jsonl
    - data/raw/<explorer_name>/transitions.jsonl
    """
    
    def __init__(self, explorer_name: str, base_dir: Path = None, auto_clean: bool = False):
        """
        Initialize storage.
        
        Args:
            explorer_name: Name of explorer/subfolder (e.g., "agenttrek", "localhost_9999")
            base_dir: Base directory for data storage (defaults to data/raw)
            auto_clean: If True, clears old exploration data on initialization (default: False)
        """
        self.explorer_name = explorer_name
        
        if base_dir is None:
            # Default to data/raw in project root
            project_root = Path(__file__).parent.parent
            base_dir = project_root / "data" / "raw"
        
        self.output_dir = base_dir / explorer_name
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.screens_file = self.output_dir / "screens.jsonl"
        self.actions_file = self.output_dir / "actions.jsonl"  # NEW: Separate actions storage
        self.transitions_file = self.output_dir / "transitions.jsonl"
        self.metadata_file = self.output_dir / "metadata.json"
        
        # Auto-clean old data before new exploration (default: False to preserve history)
        if auto_clean:
            self.clear()
            logger.info(f"Cleared old exploration data")
        else:
            logger.info(f"Using existing directory (auto_clean=False)")
        
        logger.info(f"Exploration storage initialized at: {self.output_dir}")
    
    def save_screen(self, screen: Screen):
        """
        Append a screen to screens.jsonl.
        
        NOTE: Screens do NOT contain action data.
        Actions are stored separately via save_action().
        
        Args:
            screen: Screen to save
        """
        try:
            with open(self.screens_file, 'a', encoding='utf-8') as f:
                json_line = json.dumps(screen.to_dict())
                f.write(json_line + '\n')
            logger.debug(f"Saved screen: {screen.screen_id}")
        
        except Exception as e:
            logger.error(f"Error saving screen {screen.screen_id}: {e}")
    
    def save_action(self, action: 'Action'):
        """
        Append an action to actions.jsonl.
        
        Actions are the single source of truth for semantic + executable.
        
        Args:
            action: Action to save (contains both semantic and executable)
        """
        try:
            with open(self.actions_file, 'a', encoding='utf-8') as f:
                json_line = json.dumps(action.to_dict())
                f.write(json_line + '\n')
            logger.debug(f"Saved action: {action.action_id}")
        
        except Exception as e:
            logger.error(f"Error saving action {action.action_id}: {e}")
    
    def save_transition(self, transition: Transition):
        """
        Append a transition to transitions.jsonl.
        
        NOTE: Transitions store ONLY action_id reference.
        To get full action, load from actions.jsonl.
        
        Args:
            transition: Transition to save
        """
        try:
            with open(self.transitions_file, 'a', encoding='utf-8') as f:
                json_line = json.dumps(transition.to_dict())
                f.write(json_line + '\n')
            logger.debug(f"Saved transition: {transition.transition_id}")
        
        except Exception as e:
            logger.error(f"Error saving transition {transition.transition_id}: {e}")
    
    def save_exploration_result(self, result: ExplorationResult):
        """
        Save complete exploration result.
        
        NOTE: Screens and actions are saved incrementally during exploration.
        This method only saves transitions and metadata summary.
        
        Args:
            result: ExplorationResult to save
        """
        logger.info(f"Finalizing exploration result: {result.get_unique_screen_count()} screens, "
                   f"{result.get_action_count()} actions, {result.get_transition_count()} transitions")
        
        # Screens and actions already saved incrementally during exploration
        # Only save transitions (created after action execution)
        for transition in result.transitions:
            self.save_transition(transition)
        
        # Save metadata summary
        self._save_metadata(result)
        
        logger.info(f"Exploration finalized at: {self.output_dir}")
    
    def _save_metadata(self, result: ExplorationResult):
        """
        Save exploration metadata to a summary file.
        
        Args:
            result: ExplorationResult
        """
        metadata_file = self.output_dir / "metadata.json"
        
        metadata = {
            "explorer_name": result.explorer_name,
            "start_url": result.start_url,
            "timestamp": result.timestamp,
            "unique_screens": result.get_unique_screen_count(),
            "actions": result.get_action_count(),
            "transitions": result.get_transition_count(),
            "separation_valid": result.validate_separation(),
            "meta": result.meta
        }
        
        try:
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2)
            logger.info(f"Saved metadata to: {metadata_file}")
        
        except Exception as e:
            logger.error(f"Error saving metadata: {e}")
    
    def load_screens(self) -> List[Screen]:
        """
        Load all screens from screens.jsonl.
        
        Returns:
            List of Screen objects
        """
        screens = []
        
        if not self.screens_file.exists():
            logger.warning(f"Screens file not found: {self.screens_file}")
            return screens
        
        try:
            with open(self.screens_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        data = json.loads(line)
                        screen = Screen.from_dict(data)
                        screens.append(screen)
            
            logger.info(f"Loaded {len(screens)} screens from {self.screens_file}")
        
        except Exception as e:
            logger.error(f"Error loading screens: {e}")
        
        return screens
    
    def load_actions(self) -> List['Action']:
        """
        Load all actions from actions.jsonl.
        
        Returns:
            List of Action objects (semantic + executable)
        """
        from exploration.schema import Action
        actions = []
        
        if not self.actions_file.exists():
            logger.warning(f"Actions file not found: {self.actions_file}")
            return actions
        
        try:
            with open(self.actions_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        data = json.loads(line)
                        action = Action.from_dict(data)
                        actions.append(action)
            
            logger.info(f"Loaded {len(actions)} actions from {self.actions_file}")
        
        except Exception as e:
            logger.error(f"Error loading actions: {e}")
        
        return actions
    
    def load_transitions(self) -> List[Transition]:
        """
        Load all transitions from transitions.jsonl.
        
        Returns:
            List of Transition objects
        """
        transitions = []
        
        if not self.transitions_file.exists():
            logger.warning(f"Transitions file not found: {self.transitions_file}")
            return transitions
        
        try:
            with open(self.transitions_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        data = json.loads(line)
                        transition = Transition.from_dict(data)
                        transitions.append(transition)
            
            logger.info(f"Loaded {len(transitions)} transitions from {self.transitions_file}")
        
        except Exception as e:
            logger.error(f"Error loading transitions: {e}")
        
        return transitions
    
    def clear(self):
        """
        Clear all stored data files.
        Removes screens, actions, transitions, and metadata.
        """
        files_removed = []
        
        if self.screens_file.exists():
            self.screens_file.unlink()
            files_removed.append("screens.jsonl")
        
        if self.actions_file.exists():
            self.actions_file.unlink()
            files_removed.append("actions.jsonl")
            
        if self.transitions_file.exists():
            self.transitions_file.unlink()
            files_removed.append("transitions.jsonl")
            
        if self.metadata_file.exists():
            self.metadata_file.unlink()
            files_removed.append("metadata.json")
        
        if files_removed:
            logger.debug(f"Cleared files: {', '.join(files_removed)}")
        else:
            logger.debug("No old data to clear")
