"""
SLM-based runtime agent for production inference.

This agent loads a trained checkpoint and performs fast inference
to select actions. It implements the BaseAgent interface and can be
used as a drop-in replacement for SimpleAgent.

ARCHITECTURAL BOUNDARIES:
- Imports: schema.py, agents.base_agent, training.model, training.collate, torch, stdlib ONLY
- No imports from: explorers, adapters, training.dataset/trainer/eval, envs, browser
- Inference only: model.eval(), no gradients, no training logic

Design Philosophy:
- Runtime agent is thin glue around trained model
- Schema enforcement at boundaries (Observation → Action)
- Safe defaults over clever decoding
- Production-first: fast, deterministic, robust
"""

import sys
from pathlib import Path
from typing import Dict, Any, Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    raise ImportError("PyTorch required for SLMAgent. Install with: pip install torch")

from schema import Action, ActionType, State
from agents.base_agent import BaseAgent
from training.model import WebAgentPolicy
from training.collate import StateEncoder, ActionEncoder


class SLMAgent(BaseAgent):
    """
    Small Language Model agent for production inference.
    
    This agent:
    1. Loads a trained checkpoint
    2. Encodes observations using the same encoders as training
    3. Performs inference with the trained model
    4. Decodes model outputs into valid Actions
    
    Usage:
        agent = SLMAgent.from_checkpoint("checkpoints/best_model.pt")
        
        observation = env.reset()
        action = agent.act(observation)
    """
    
    def __init__(
        self,
        model: WebAgentPolicy,
        state_encoder: StateEncoder,
        action_encoder: ActionEncoder,
        device: str = "cpu",
        temperature: float = 0.0,
        name: str = "slm"
    ):
        """
        Initialize SLM agent.
        
        Args:
            model: Trained policy model
            state_encoder: State encoder (must match training)
            action_encoder: Action encoder (must match training)
            device: Device to run inference on ("cpu" or "cuda")
            temperature: Sampling temperature (0.0 = greedy/argmax)
            name: Agent name
        """
        super().__init__(name)
        
        self.model = model
        self.state_encoder = state_encoder
        self.action_encoder = action_encoder
        self.device = device
        self.temperature = temperature if temperature > 0 else 1.0  # Avoid division by zero
        self.use_argmax = temperature == 0.0
        
        # Move model to device and set to eval mode
        self.model.to(device)
        self.model.eval()
        
        # Cache for interactive elements (for target decoding)
        self._current_elements = []
    
    def reset(self):
        """Reset agent state at the beginning of an episode"""
        self._current_elements = []
    
    def act(self, observation: Dict[str, Any]) -> Action:
        """
        Select action given observation.
        
        Args:
            observation: Current observation from environment
                Must contain:
                - url: str
                - html: str
                - interactive_elements: List[Dict]
                
        Returns:
            Action to execute
        """
        # Convert observation to State
        state = self._observation_to_state(observation)
        
        # Cache elements for target decoding
        self._current_elements = state.interactive_elements or []
        
        # Encode state
        state_encoded = self.state_encoder.encode_state(state)
        
        # Add batch dimension and move to device
        url = state_encoded["url"].unsqueeze(0).to(self.device)
        text = state_encoded["text"].unsqueeze(0).to(self.device)
        elements = state_encoded["elements"].unsqueeze(0).to(self.device)
        element_mask = state_encoded["element_mask"].unsqueeze(0).to(self.device)
        
        # Inference (no gradients)
        with torch.no_grad():
            if self.use_argmax:
                # Greedy decoding (deterministic)
                outputs = self.model.predict(
                    url=url,
                    text=text,
                    elements=elements,
                    element_mask=element_mask,
                    value_max_length=128,
                    temperature=1.0  # Temperature is handled in predict
                )
            else:
                # Sample with temperature
                outputs = self.model.predict(
                    url=url,
                    text=text,
                    elements=elements,
                    element_mask=element_mask,
                    value_max_length=128,
                    temperature=self.temperature
                )
        
        # Decode outputs to Action
        action = self._decode_action(outputs, state)
        
        return action
    
    def _observation_to_state(self, observation: Dict[str, Any]) -> State:
        """
        Convert environment observation to State.
        
        Args:
            observation: Raw observation dict from environment
            
        Returns:
            State object
        """
        return State(
            url=observation.get("url", ""),
            html=observation.get("html", ""),
            interactive_elements=observation.get("interactive_elements", [])
        )
    
    def _decode_action(self, outputs: Dict[str, torch.Tensor], state: State) -> Action:
        """
        Decode model outputs into a valid Action.
        
        Args:
            outputs: Model predictions
                - action_type: (batch_size,) action type indices
                - target_element: (batch_size,) element indices
                - value: (batch_size, value_length) character indices
            state: Current state (for element lookup)
            
        Returns:
            Valid Action object
        """
        # Extract predictions (remove batch dimension)
        action_type_idx = outputs["action_type"][0].item()
        target_element_idx = outputs["target_element"][0].item()
        value_chars = outputs["value"][0]  # (value_length,)
        
        # Decode action type
        try:
            action_type = self.action_encoder.decode_action_type(action_type_idx)
        except (KeyError, IndexError):
            # Invalid action type -> safe fallback
            action_type = ActionType.WAIT
        
        # Decode target
        target = self._decode_target(action_type, target_element_idx, state)
        
        # Decode value (for TYPE actions)
        value = None
        if action_type == ActionType.TYPE:
            value = self._decode_value(value_chars)
        
        # Create Action
        action = Action(
            type=action_type,
            target=target,
            value=value
        )
        
        return action
    
    def _decode_target(
        self,
        action_type: ActionType,
        element_idx: int,
        state: State
    ) -> str:
        """
        Decode target element.
        
        Args:
            action_type: Action type
            element_idx: Predicted element index
            state: Current state
            
        Returns:
            Target selector string
        """
        # For CLICK, use element index to get selector
        if action_type == ActionType.CLICK:
            elements = state.interactive_elements or []
            
            # Validate index
            if 0 <= element_idx < len(elements):
                element = elements[element_idx]
                # Try to get selector, fallback to text
                target = element.get("selector", "") or element.get("text", "")
                if target:
                    return target
            
            # Invalid index or no selector -> fallback to first element
            if elements:
                first_elem = elements[0]
                return first_elem.get("selector", "") or first_elem.get("text", "")
        
        # For other actions, target is not critical
        return ""
    
    def _decode_value(self, value_chars: torch.Tensor) -> str:
        """
        Decode value text from character indices.
        
        Args:
            value_chars: (value_length,) tensor of character indices
            
        Returns:
            Decoded string
        """
        # Convert to list of indices
        char_indices = value_chars.cpu().tolist()
        
        # Decode characters
        chars = []
        idx_to_char = self.state_encoder.idx_to_char
        
        for idx in char_indices:
            if idx == 0:  # <PAD>
                break
            if idx == 3:  # <END>
                break
            if idx in idx_to_char:
                char = idx_to_char[idx]
                if char not in ["<PAD>", "<UNK>", "<START>", "<END>"]:
                    chars.append(char)
        
        return "".join(chars)
    
    @classmethod
    def from_checkpoint(
        cls,
        checkpoint_path: str,
        device: str = "cpu",
        temperature: float = 0.0,
        name: str = "slm"
    ) -> 'SLMAgent':
        """
        Load agent from a trained checkpoint.
        
        Args:
            checkpoint_path: Path to checkpoint file (.pt)
            device: Device to run on ("cpu" or "cuda")
            temperature: Sampling temperature (0.0 = greedy)
            name: Agent name
            
        Returns:
            Initialized SLMAgent
        """
        checkpoint_path = Path(checkpoint_path)
        
        if not checkpoint_path.exists():
            raise FileNotFoundError(f"Checkpoint not found: {checkpoint_path}")
        
        # Load checkpoint
        checkpoint = torch.load(checkpoint_path, map_location=device)
        
        # Create model
        model = WebAgentPolicy(
            vocab_size=checkpoint["vocab_size"],
            num_action_types=checkpoint["num_action_types"],
            max_elements=checkpoint["max_elements"],
            embedding_dim=checkpoint["embedding_dim"],
            hidden_dim=checkpoint["hidden_dim"]
        )
        model.load_state_dict(checkpoint["model_state_dict"])
        
        # Create encoders (must match training configuration)
        state_encoder = StateEncoder(
            vocab_size=checkpoint["vocab_size"],
            max_text_length=512,
            max_url_length=128,
            max_elements=checkpoint["max_elements"],
            max_element_text_length=32
        )
        
        action_encoder = ActionEncoder(
            max_elements=checkpoint["max_elements"],
            max_value_length=128
        )
        
        # Create agent
        agent = cls(
            model=model,
            state_encoder=state_encoder,
            action_encoder=action_encoder,
            device=device,
            temperature=temperature,
            name=name
        )
        
        print(f"Loaded SLM agent from checkpoint: {checkpoint_path}")
        print(f"  Epoch: {checkpoint.get('epoch', 'unknown')}")
        print(f"  Device: {device}")
        print(f"  Temperature: {temperature} {'(greedy)' if temperature == 0 else ''}")
        
        return agent


def create_slm_agent(
    checkpoint_path: str,
    device: str = "cpu",
    temperature: float = 0.0
) -> SLMAgent:
    """
    Convenience function to create SLM agent from checkpoint.
    
    Args:
        checkpoint_path: Path to trained checkpoint
        device: Device to run on
        temperature: Sampling temperature
        
    Returns:
        SLMAgent instance
    """
    return SLMAgent.from_checkpoint(
        checkpoint_path=checkpoint_path,
        device=device,
        temperature=temperature
    )
