"""
Collation and encoding for training.

This module converts State observations and Actions into tensor representations
suitable for model training. It keeps encoding logic separate from the model architecture.

ARCHITECTURAL BOUNDARIES:
- Imports: schema.py, torch, standard library ONLY
- No imports from: explorers, adapters, envs, browser, agents
- Pure data transformation, no environment interaction
"""

import sys
from pathlib import Path
from typing import List, Dict, Any, Tuple
import re

sys.path.insert(0, str(Path(__file__).parent.parent))
from schema import State, Action, ActionType

try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    raise ImportError("PyTorch required for training. Install with: pip install torch")


class StateEncoder:
    """
    Encodes State observations into tensor representations.
    
    This encoder:
    1. Extracts text from HTML (simplified)
    2. Encodes URL
    3. Encodes interactive elements
    4. Creates fixed-size representation
    
    Design:
    - Simple text-based encoding (character-level or word-level)
    - Can be extended with embeddings, transformers, etc.
    - Keeps encoding separate from model architecture
    """
    
    def __init__(
        self,
        vocab_size: int = 1000,
        max_text_length: int = 512,
        max_url_length: int = 128,
        max_elements: int = 50,
        max_element_text_length: int = 32
    ):
        """
        Initialize state encoder.
        
        Args:
            vocab_size: Vocabulary size for text encoding
            max_text_length: Maximum length for HTML text
            max_url_length: Maximum length for URL
            max_elements: Maximum number of interactive elements
            max_element_text_length: Maximum text length per element
        """
        self.vocab_size = vocab_size
        self.max_text_length = max_text_length
        self.max_url_length = max_url_length
        self.max_elements = max_elements
        self.max_element_text_length = max_element_text_length
        
        # Character vocabulary (simple encoding)
        self.char_to_idx = self._build_char_vocab()
        self.idx_to_char = {v: k for k, v in self.char_to_idx.items()}
    
    def _build_char_vocab(self) -> Dict[str, int]:
        """Build character vocabulary"""
        # Basic ASCII + special tokens
        vocab = {"<PAD>": 0, "<UNK>": 1, "<START>": 2, "<END>": 3}
        
        # Printable ASCII characters
        for i in range(32, 127):
            vocab[chr(i)] = len(vocab)
        
        return vocab
    
    def _encode_text(self, text: str, max_length: int) -> torch.Tensor:
        """
        Encode text into character indices.
        
        Args:
            text: Input text
            max_length: Maximum sequence length
            
        Returns:
            Tensor of shape (max_length,) with character indices
        """
        # Clean text
        text = text.lower()[:max_length]
        
        # Convert to indices
        indices = [
            self.char_to_idx.get(c, self.char_to_idx["<UNK>"])
            for c in text
        ]
        
        # Pad to max_length
        indices = indices + [self.char_to_idx["<PAD>"]] * (max_length - len(indices))
        
        return torch.tensor(indices[:max_length], dtype=torch.long)
    
    def _extract_text_from_html(self, html: str, max_length: int) -> str:
        """
        Extract visible text from HTML (simplified extraction).
        
        Args:
            html: HTML content
            max_length: Maximum text length
            
        Returns:
            Extracted text
        """
        # Remove script and style tags
        html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL | re.IGNORECASE)
        
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', ' ', html)
        
        # Clean whitespace
        text = ' '.join(text.split())
        
        return text[:max_length]
    
    def encode_state(self, state: State) -> Dict[str, torch.Tensor]:
        """
        Encode State into tensor representation.
        
        Args:
            state: State object from schema
            
        Returns:
            Dictionary with encoded tensors:
                - url: (max_url_length,)
                - text: (max_text_length,)
                - elements: (max_elements, max_element_text_length)
                - element_mask: (max_elements,) - 1 for valid elements, 0 for padding
        """
        # Encode URL
        url_encoded = self._encode_text(state.url, self.max_url_length)
        
        # Extract and encode visible text from HTML
        text = self._extract_text_from_html(state.html, self.max_text_length)
        text_encoded = self._encode_text(text, self.max_text_length)
        
        # Encode interactive elements
        elements = state.interactive_elements or []
        element_tensors = []
        element_mask = []
        
        for i in range(self.max_elements):
            if i < len(elements):
                elem = elements[i]
                # Use element text or tag as representation
                elem_text = elem.get("text", "") or elem.get("tag", "")
                elem_encoded = self._encode_text(elem_text, self.max_element_text_length)
                element_tensors.append(elem_encoded)
                element_mask.append(1)
            else:
                # Padding
                elem_encoded = torch.zeros(self.max_element_text_length, dtype=torch.long)
                element_tensors.append(elem_encoded)
                element_mask.append(0)
        
        elements_encoded = torch.stack(element_tensors)  # (max_elements, max_element_text_length)
        element_mask = torch.tensor(element_mask, dtype=torch.float32)
        
        return {
            "url": url_encoded,
            "text": text_encoded,
            "elements": elements_encoded,
            "element_mask": element_mask
        }


class ActionEncoder:
    """
    Encodes Actions into label representations for classification.
    
    Action encoding:
    - Action type: categorical (CLICK, TYPE, SCROLL, etc.)
    - Target: element index (for CLICK) or text (for TYPE)
    - Value: text value (for TYPE actions)
    
    This is a classification problem:
    - Predict action type (6 classes)
    - Predict target element (max_elements classes for CLICK)
    - Predict value (character sequence for TYPE)
    """
    
    def __init__(self, max_elements: int = 50, max_value_length: int = 128):
        """
        Initialize action encoder.
        
        Args:
            max_elements: Maximum number of interactive elements
            max_value_length: Maximum length for type values
        """
        self.max_elements = max_elements
        self.max_value_length = max_value_length
        
        # Action type mapping
        self.action_types = list(ActionType)
        self.action_type_to_idx = {
            action_type: idx for idx, action_type in enumerate(self.action_types)
        }
        self.idx_to_action_type = {
            idx: action_type for action_type, idx in self.action_type_to_idx.items()
        }
        
        # Character vocabulary (same as StateEncoder for consistency)
        self.char_to_idx = self._build_char_vocab()
    
    def _build_char_vocab(self) -> Dict[str, int]:
        """Build character vocabulary"""
        vocab = {"<PAD>": 0, "<UNK>": 1, "<START>": 2, "<END>": 3}
        for i in range(32, 127):
            vocab[chr(i)] = len(vocab)
        return vocab
    
    def encode_action(
        self,
        action: Action,
        elements: List[Dict[str, str]] = None
    ) -> Dict[str, torch.Tensor]:
        """
        Encode Action into label tensors.
        
        Args:
            action: Action object from schema
            elements: List of interactive elements (for target matching)
            
        Returns:
            Dictionary with encoded labels:
                - action_type: scalar (action type index)
                - target_element: scalar (element index for CLICK, -1 otherwise)
                - value: (max_value_length,) character indices for TYPE
        """
        # Encode action type
        action_type_idx = self.action_type_to_idx[action.type]
        
        # Encode target element
        target_element_idx = -1
        if action.type == ActionType.CLICK and elements:
            # Try to match target selector to an element
            target_element_idx = self._match_target_to_element(action.target, elements)
        
        # Encode value (for TYPE actions)
        value_text = action.value if action.value else ""
        value_indices = [
            self.char_to_idx.get(c, self.char_to_idx["<UNK>"])
            for c in value_text[:self.max_value_length]
        ]
        value_indices = value_indices + [self.char_to_idx["<PAD>"]] * (self.max_value_length - len(value_indices))
        value_encoded = torch.tensor(value_indices[:self.max_value_length], dtype=torch.long)
        
        return {
            "action_type": torch.tensor(action_type_idx, dtype=torch.long),
            "target_element": torch.tensor(target_element_idx, dtype=torch.long),
            "value": value_encoded
        }
    
    def _match_target_to_element(
        self,
        target: str,
        elements: List[Dict[str, str]]
    ) -> int:
        """
        Match target selector to element index.
        
        Simple heuristic: exact match on selector or text.
        Returns -1 if no match found.
        """
        for i, elem in enumerate(elements):
            if i >= self.max_elements:
                break
            
            # Check selector match
            if elem.get("selector") == target:
                return i
            
            # Check text match (case-insensitive)
            if elem.get("text", "").lower() == target.lower():
                return i
        
        return -1
    
    def decode_action_type(self, action_type_idx: int) -> ActionType:
        """Decode action type index to ActionType"""
        return self.idx_to_action_type[action_type_idx]
    
    @property
    def num_action_types(self) -> int:
        """Number of action types"""
        return len(self.action_types)


def collate_fn(
    batch: List[Tuple[State, Action, Dict[str, Any]]],
    state_encoder: StateEncoder,
    action_encoder: ActionEncoder
) -> Dict[str, Any]:
    """
    Collate function for DataLoader.
    
    Converts a batch of (state, action, meta) tuples into batched tensors.
    
    Args:
        batch: List of (state, action, meta) tuples
        state_encoder: StateEncoder instance
        action_encoder: ActionEncoder instance
        
    Returns:
        Dictionary with batched tensors:
            - states: Dict with batched state tensors
            - labels: Dict with batched action labels
            - meta: List of meta dictionaries
    """
    states = []
    labels = []
    metas = []
    
    for state, action, meta in batch:
        # Encode state
        state_encoded = state_encoder.encode_state(state)
        states.append(state_encoded)
        
        # Encode action
        elements = state.interactive_elements or []
        action_encoded = action_encoder.encode_action(action, elements)
        labels.append(action_encoded)
        
        metas.append(meta)
    
    # Batch states
    batched_states = {
        "url": torch.stack([s["url"] for s in states]),
        "text": torch.stack([s["text"] for s in states]),
        "elements": torch.stack([s["elements"] for s in states]),
        "element_mask": torch.stack([s["element_mask"] for s in states])
    }
    
    # Batch labels
    batched_labels = {
        "action_type": torch.stack([l["action_type"] for l in labels]),
        "target_element": torch.stack([l["target_element"] for l in labels]),
        "value": torch.stack([l["value"] for l in labels])
    }
    
    return {
        "states": batched_states,
        "labels": batched_labels,
        "meta": metas
    }


def create_collate_fn(
    state_encoder: StateEncoder,
    action_encoder: ActionEncoder
):
    """
    Create collate function with specific encoders.
    
    This is a factory function to create a collate_fn with bound encoders
    for use with PyTorch DataLoader.
    
    Usage:
        state_enc = StateEncoder()
        action_enc = ActionEncoder()
        collate = create_collate_fn(state_enc, action_enc)
        
        loader = DataLoader(dataset, batch_size=32, collate_fn=collate)
    """
    def _collate(batch):
        return collate_fn(batch, state_encoder, action_encoder)
    return _collate
