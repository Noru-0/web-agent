"""
SLM policy model for web agent.

This module defines the Small Language Model architecture for action prediction.
The model takes encoded states as input and predicts actions.

ARCHITECTURAL BOUNDARIES:
- Imports: torch, standard library ONLY
- No imports from: schema, explorers, adapters, envs, browser, agents
- Pure model architecture, no data loading or environment logic
"""

import sys
from pathlib import Path
from typing import Dict, Any, Optional, Tuple

try:
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    raise ImportError("PyTorch required for training. Install with: pip install torch")


class WebAgentPolicy(nn.Module):
    """
    Small Language Model policy for web agent action prediction.
    
    Architecture:
    - Embedding layers for character-level text encoding
    - LSTM/Transformer for sequence modeling
    - Multi-head prediction:
      * Action type (classification)
      * Target element (classification)
      * Value text (sequence generation)
    
    This is a simple, lightweight architecture suitable for:
    - Fast training
    - On-device inference
    - Educational purposes
    
    Can be extended with:
    - Pre-trained embeddings
    - Larger transformer models
    - Vision encoders for screenshots
    """
    
    def __init__(
        self,
        vocab_size: int,
        num_action_types: int,
        max_elements: int,
        embedding_dim: int = 128,
        hidden_dim: int = 256,
        num_layers: int = 2,
        dropout: float = 0.1
    ):
        """
        Initialize policy model.
        
        Args:
            vocab_size: Size of character vocabulary
            num_action_types: Number of action types (CLICK, TYPE, etc.)
            max_elements: Maximum number of interactive elements
            embedding_dim: Dimension of character embeddings
            hidden_dim: Hidden dimension for LSTM and prediction layers
            num_layers: Number of LSTM layers
            dropout: Dropout probability
        """
        super().__init__()
        
        self.vocab_size = vocab_size
        self.num_action_types = num_action_types
        self.max_elements = max_elements
        self.embedding_dim = embedding_dim
        self.hidden_dim = hidden_dim
        
        # Character embedding (shared across all text inputs)
        self.char_embedding = nn.Embedding(vocab_size, embedding_dim, padding_idx=0)
        
        # URL encoder
        self.url_encoder = nn.LSTM(
            embedding_dim,
            hidden_dim // 2,
            num_layers=1,
            batch_first=True,
            bidirectional=True
        )
        
        # Text encoder (for HTML text)
        self.text_encoder = nn.LSTM(
            embedding_dim,
            hidden_dim // 2,
            num_layers=1,
            batch_first=True,
            bidirectional=True
        )
        
        # Element encoder
        self.element_encoder = nn.LSTM(
            embedding_dim,
            hidden_dim // 2,
            num_layers=1,
            batch_first=True,
            bidirectional=True
        )
        
        # State fusion layer
        self.state_fusion = nn.Sequential(
            nn.Linear(hidden_dim * 3, hidden_dim * 2),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim * 2, hidden_dim),
            nn.ReLU(),
            nn.Dropout(dropout)
        )
        
        # Action type prediction head
        self.action_type_head = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim // 2, num_action_types)
        )
        
        # Target element prediction head
        self.target_element_head = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim // 2, max_elements + 1)  # +1 for "no element" class
        )
        
        # Value prediction head (for TYPE actions)
        self.value_decoder = nn.LSTM(
            hidden_dim + embedding_dim,  # state + previous char
            hidden_dim,
            num_layers=num_layers,
            batch_first=True
        )
        self.value_output = nn.Linear(hidden_dim, vocab_size)
    
    def forward(
        self,
        url: torch.Tensor,
        text: torch.Tensor,
        elements: torch.Tensor,
        element_mask: torch.Tensor,
        value_input: Optional[torch.Tensor] = None
    ) -> Dict[str, torch.Tensor]:
        """
        Forward pass.
        
        Args:
            url: (batch_size, url_length) - URL character indices
            text: (batch_size, text_length) - HTML text character indices
            elements: (batch_size, max_elements, element_text_length) - Element character indices
            element_mask: (batch_size, max_elements) - Mask for valid elements
            value_input: (batch_size, value_length) - Input for value generation (teacher forcing)
            
        Returns:
            Dictionary with predictions:
                - action_type_logits: (batch_size, num_action_types)
                - target_element_logits: (batch_size, max_elements + 1)
                - value_logits: (batch_size, value_length, vocab_size) if value_input provided
        """
        batch_size = url.size(0)
        
        # Encode URL
        url_embedded = self.char_embedding(url)  # (batch_size, url_length, embedding_dim)
        url_output, (url_hidden, _) = self.url_encoder(url_embedded)
        url_repr = url_hidden.transpose(0, 1).contiguous().view(batch_size, -1)  # (batch_size, hidden_dim)
        
        # Encode text
        text_embedded = self.char_embedding(text)  # (batch_size, text_length, embedding_dim)
        text_output, (text_hidden, _) = self.text_encoder(text_embedded)
        text_repr = text_hidden.transpose(0, 1).contiguous().view(batch_size, -1)  # (batch_size, hidden_dim)
        
        # Encode elements
        # Flatten batch and elements: (batch_size * max_elements, element_text_length)
        elements_flat = elements.view(-1, elements.size(-1))
        elements_embedded = self.char_embedding(elements_flat)
        elements_output, (elements_hidden, _) = self.element_encoder(elements_embedded)
        # Reshape: (batch_size, max_elements, hidden_dim)
        elements_repr = elements_hidden.transpose(0, 1).contiguous().view(
            batch_size, self.max_elements, -1
        )
        
        # Pool elements with attention (masked by element_mask)
        # Simple mean pooling with mask
        element_mask_expanded = element_mask.unsqueeze(-1)  # (batch_size, max_elements, 1)
        elements_masked = elements_repr * element_mask_expanded
        elements_pooled = elements_masked.sum(dim=1) / (element_mask.sum(dim=1, keepdim=True) + 1e-8)
        
        # Fuse state representations
        state_repr = torch.cat([url_repr, text_repr, elements_pooled], dim=-1)
        state_fused = self.state_fusion(state_repr)  # (batch_size, hidden_dim)
        
        # Predict action type
        action_type_logits = self.action_type_head(state_fused)  # (batch_size, num_action_types)
        
        # Predict target element
        target_element_logits = self.target_element_head(state_fused)  # (batch_size, max_elements + 1)
        
        # Predict value (if input provided for teacher forcing)
        value_logits = None
        if value_input is not None:
            value_length = value_input.size(1)
            # Prepare decoder input
            value_embedded = self.char_embedding(value_input)  # (batch_size, value_length, embedding_dim)
            # Expand state for each time step
            state_expanded = state_fused.unsqueeze(1).expand(-1, value_length, -1)
            # Concatenate state with input
            decoder_input = torch.cat([state_expanded, value_embedded], dim=-1)
            # Decode
            decoder_output, _ = self.value_decoder(decoder_input)
            value_logits = self.value_output(decoder_output)  # (batch_size, value_length, vocab_size)
        
        return {
            "action_type_logits": action_type_logits,
            "target_element_logits": target_element_logits,
            "value_logits": value_logits
        }
    
    def predict(
        self,
        url: torch.Tensor,
        text: torch.Tensor,
        elements: torch.Tensor,
        element_mask: torch.Tensor,
        value_max_length: int = 128,
        temperature: float = 1.0
    ) -> Dict[str, Any]:
        """
        Inference mode: predict action without teacher forcing.
        
        Args:
            url: (batch_size, url_length)
            text: (batch_size, text_length)
            elements: (batch_size, max_elements, element_text_length)
            element_mask: (batch_size, max_elements)
            value_max_length: Maximum length for value generation
            temperature: Sampling temperature
            
        Returns:
            Dictionary with predictions:
                - action_type: (batch_size,) predicted action type indices
                - target_element: (batch_size,) predicted element indices
                - value: (batch_size, value_length) predicted value character indices
        """
        self.eval()
        with torch.no_grad():
            batch_size = url.size(0)
            
            # Forward pass for action type and target
            outputs = self.forward(url, text, elements, element_mask, value_input=None)
            
            # Predict action type
            action_type_probs = F.softmax(outputs["action_type_logits"] / temperature, dim=-1)
            action_type = torch.argmax(action_type_probs, dim=-1)
            
            # Predict target element
            target_element_probs = F.softmax(outputs["target_element_logits"] / temperature, dim=-1)
            target_element = torch.argmax(target_element_probs, dim=-1)
            
            # Auto-regressive value generation
            # Start with <START> token (index 2)
            value_tokens = torch.full((batch_size, 1), 2, dtype=torch.long, device=url.device)
            
            for _ in range(value_max_length - 1):
                # Forward pass with current tokens
                outputs_step = self.forward(
                    url, text, elements, element_mask,
                    value_input=value_tokens
                )
                
                # Get next token prediction
                next_token_logits = outputs_step["value_logits"][:, -1, :]  # (batch_size, vocab_size)
                next_token_probs = F.softmax(next_token_logits / temperature, dim=-1)
                next_token = torch.argmax(next_token_probs, dim=-1, keepdim=True)
                
                # Append to sequence
                value_tokens = torch.cat([value_tokens, next_token], dim=1)
                
                # Check for <END> token (index 3) - stop if all sequences done
                if (next_token == 3).all():
                    break
            
            return {
                "action_type": action_type,
                "target_element": target_element,
                "value": value_tokens
            }
    
    def save(self, path: Path):
        """Save model checkpoint"""
        path.parent.mkdir(parents=True, exist_ok=True)
        torch.save({
            "model_state_dict": self.state_dict(),
            "vocab_size": self.vocab_size,
            "num_action_types": self.num_action_types,
            "max_elements": self.max_elements,
            "embedding_dim": self.embedding_dim,
            "hidden_dim": self.hidden_dim
        }, path)
        
    @classmethod
    def load(cls, path: Path, device: str = "cpu") -> 'WebAgentPolicy':
        """Load model checkpoint"""
        checkpoint = torch.load(path, map_location=device)
        model = cls(
            vocab_size=checkpoint["vocab_size"],
            num_action_types=checkpoint["num_action_types"],
            max_elements=checkpoint["max_elements"],
            embedding_dim=checkpoint["embedding_dim"],
            hidden_dim=checkpoint["hidden_dim"]
        )
        model.load_state_dict(checkpoint["model_state_dict"])
        model.to(device)
        return model


def count_parameters(model: nn.Module) -> int:
    """Count trainable parameters in model"""
    return sum(p.numel() for p in model.parameters() if p.requires_grad)
