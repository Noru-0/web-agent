"""
Trainer for SLM policy model.

This module implements the training loop, loss computation, checkpointing,
and logging for the web agent policy model.

ARCHITECTURAL BOUNDARIES:
- Imports: model.py, dataset.py, collate.py, torch, standard library ONLY
- No imports from: explorers, adapters, envs, browser, agents
- Pure training logic, no environment interaction
"""

import sys
from pathlib import Path
from typing import Dict, Any, Optional
import time
import json

sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import torch
    import torch.nn as nn
    import torch.optim as optim
    from torch.utils.data import DataLoader
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    raise ImportError("PyTorch required for training. Install with: pip install torch")

from training.model import WebAgentPolicy, count_parameters
from training.dataset import TrajectoryDataset
from training.collate import StateEncoder, ActionEncoder, create_collate_fn


class Trainer:
    """
    Trainer for web agent policy model.
    
    Handles:
    - Training loop
    - Loss computation (action type + target + value)
    - Optimization
    - Checkpointing
    - Logging
    - Validation
    
    Usage:
        trainer = Trainer(
            model=model,
            train_dataset=train_ds,
            val_dataset=val_ds,
            config=config
        )
        trainer.train()
    """
    
    def __init__(
        self,
        model: WebAgentPolicy,
        train_dataset: TrajectoryDataset,
        val_dataset: TrajectoryDataset,
        state_encoder: StateEncoder,
        action_encoder: ActionEncoder,
        config: Dict[str, Any]
    ):
        """
        Initialize trainer.
        
        Args:
            model: WebAgentPolicy model
            train_dataset: Training dataset
            val_dataset: Validation dataset
            state_encoder: State encoder
            action_encoder: Action encoder
            config: Training configuration
        """
        self.model = model
        self.train_dataset = train_dataset
        self.val_dataset = val_dataset
        self.state_encoder = state_encoder
        self.action_encoder = action_encoder
        self.config = config
        
        # Training config
        self.device = config.get("device", "cuda" if torch.cuda.is_available() else "cpu")
        self.num_epochs = config.get("num_epochs", 10)
        self.batch_size = config.get("batch_size", 32)
        self.learning_rate = config.get("learning_rate", 1e-3)
        self.weight_decay = config.get("weight_decay", 1e-5)
        self.grad_clip = config.get("grad_clip", 1.0)
        self.log_interval = config.get("log_interval", 100)
        self.save_interval = config.get("save_interval", 1)  # Save every N epochs
        self.output_dir = Path(config.get("output_dir", "checkpoints"))
        
        # Loss weights
        self.action_type_weight = config.get("action_type_weight", 1.0)
        self.target_element_weight = config.get("target_element_weight", 0.5)
        self.value_weight = config.get("value_weight", 0.5)
        
        # Move model to device
        self.model.to(self.device)
        
        # Optimizer
        self.optimizer = optim.AdamW(
            self.model.parameters(),
            lr=self.learning_rate,
            weight_decay=self.weight_decay
        )
        
        # Learning rate scheduler
        self.scheduler = optim.lr_scheduler.ReduceLROnPlateau(
            self.optimizer,
            mode='min',
            factor=0.5,
            patience=2,
            verbose=True
        )
        
        # Loss functions
        self.action_type_criterion = nn.CrossEntropyLoss()
        self.target_element_criterion = nn.CrossEntropyLoss(ignore_index=-1)  # Ignore -1 (no target)
        self.value_criterion = nn.CrossEntropyLoss(ignore_index=0)  # Ignore padding
        
        # Create data loaders
        collate = create_collate_fn(self.state_encoder, self.action_encoder)
        self.train_loader = DataLoader(
            self.train_dataset,
            batch_size=self.batch_size,
            shuffle=True,
            collate_fn=collate,
            num_workers=0  # Use 0 to avoid multiprocessing issues
        )
        self.val_loader = DataLoader(
            self.val_dataset,
            batch_size=self.batch_size,
            shuffle=False,
            collate_fn=collate,
            num_workers=0
        )
        
        # Training state
        self.epoch = 0
        self.global_step = 0
        self.best_val_loss = float('inf')
        self.train_history = []
        self.val_history = []
        
        # Create output directory
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Log model info
        num_params = count_parameters(self.model)
        print(f"\nModel initialized with {num_params:,} parameters")
        print(f"Device: {self.device}")
        print(f"Training steps per epoch: {len(self.train_loader)}")
        print(f"Validation steps per epoch: {len(self.val_loader)}")
    
    def train(self):
        """Run training loop"""
        print(f"\n{'='*60}")
        print(f"Starting training for {self.num_epochs} epochs")
        print(f"{'='*60}\n")
        
        for epoch in range(self.num_epochs):
            self.epoch = epoch
            
            # Train epoch
            train_metrics = self._train_epoch()
            self.train_history.append(train_metrics)
            
            # Validate epoch
            val_metrics = self._validate_epoch()
            self.val_history.append(val_metrics)
            
            # Update learning rate
            self.scheduler.step(val_metrics['loss'])
            
            # Print epoch summary
            self._print_epoch_summary(train_metrics, val_metrics)
            
            # Save checkpoint
            if (epoch + 1) % self.save_interval == 0:
                self._save_checkpoint(f"checkpoint_epoch_{epoch+1}.pt")
            
            # Save best model
            if val_metrics['loss'] < self.best_val_loss:
                self.best_val_loss = val_metrics['loss']
                self._save_checkpoint("best_model.pt")
                print(f"  → Saved best model (val_loss: {self.best_val_loss:.4f})")
        
        # Save final model
        self._save_checkpoint("final_model.pt")
        
        # Save training history
        self._save_history()
        
        print(f"\n{'='*60}")
        print(f"Training complete!")
        print(f"Best validation loss: {self.best_val_loss:.4f}")
        print(f"Models saved to: {self.output_dir}")
        print(f"{'='*60}\n")
    
    def _train_epoch(self) -> Dict[str, float]:
        """Train for one epoch"""
        self.model.train()
        
        total_loss = 0.0
        total_action_loss = 0.0
        total_target_loss = 0.0
        total_value_loss = 0.0
        num_batches = 0
        
        epoch_start = time.time()
        
        for batch_idx, batch in enumerate(self.train_loader):
            # Move batch to device
            states = {k: v.to(self.device) for k, v in batch["states"].items()}
            labels = {k: v.to(self.device) for k, v in batch["labels"].items()}
            
            # Forward pass
            self.optimizer.zero_grad()
            outputs = self.model(
                url=states["url"],
                text=states["text"],
                elements=states["elements"],
                element_mask=states["element_mask"],
                value_input=labels["value"]
            )
            
            # Compute losses
            action_loss = self.action_type_criterion(
                outputs["action_type_logits"],
                labels["action_type"]
            )
            
            # Target loss (only compute for valid targets)
            target_loss = self.target_element_criterion(
                outputs["target_element_logits"],
                labels["target_element"]
            )
            
            # Value loss (only compute when value_logits exist)
            if outputs["value_logits"] is not None:
                value_logits = outputs["value_logits"].reshape(-1, self.model.vocab_size)
                value_labels = labels["value"].reshape(-1)
                value_loss = self.value_criterion(value_logits, value_labels)
            else:
                value_loss = torch.tensor(0.0, device=self.device)
            
            # Combined loss
            loss = (
                self.action_type_weight * action_loss +
                self.target_element_weight * target_loss +
                self.value_weight * value_loss
            )
            
            # Backward pass
            loss.backward()
            
            # Gradient clipping
            if self.grad_clip > 0:
                torch.nn.utils.clip_grad_norm_(self.model.parameters(), self.grad_clip)
            
            self.optimizer.step()
            
            # Accumulate losses
            total_loss += loss.item()
            total_action_loss += action_loss.item()
            total_target_loss += target_loss.item()
            total_value_loss += value_loss.item()
            num_batches += 1
            self.global_step += 1
            
            # Log progress
            if (batch_idx + 1) % self.log_interval == 0:
                avg_loss = total_loss / num_batches
                print(f"  Epoch {self.epoch+1} [{batch_idx+1}/{len(self.train_loader)}] "
                      f"Loss: {avg_loss:.4f} "
                      f"(action: {action_loss.item():.4f}, "
                      f"target: {target_loss.item():.4f}, "
                      f"value: {value_loss.item():.4f})")
        
        epoch_time = time.time() - epoch_start
        
        return {
            "loss": total_loss / num_batches,
            "action_loss": total_action_loss / num_batches,
            "target_loss": total_target_loss / num_batches,
            "value_loss": total_value_loss / num_batches,
            "time": epoch_time
        }
    
    def _validate_epoch(self) -> Dict[str, float]:
        """Validate for one epoch"""
        self.model.eval()
        
        total_loss = 0.0
        total_action_acc = 0.0
        total_target_acc = 0.0
        num_batches = 0
        
        with torch.no_grad():
            for batch in self.val_loader:
                # Move batch to device
                states = {k: v.to(self.device) for k, v in batch["states"].items()}
                labels = {k: v.to(self.device) for k, v in batch["labels"].items()}
                
                # Forward pass
                outputs = self.model(
                    url=states["url"],
                    text=states["text"],
                    elements=states["elements"],
                    element_mask=states["element_mask"],
                    value_input=labels["value"]
                )
                
                # Compute losses
                action_loss = self.action_type_criterion(
                    outputs["action_type_logits"],
                    labels["action_type"]
                )
                
                target_loss = self.target_element_criterion(
                    outputs["target_element_logits"],
                    labels["target_element"]
                )
                
                if outputs["value_logits"] is not None:
                    value_logits = outputs["value_logits"].reshape(-1, self.model.vocab_size)
                    value_labels = labels["value"].reshape(-1)
                    value_loss = self.value_criterion(value_logits, value_labels)
                else:
                    value_loss = torch.tensor(0.0, device=self.device)
                
                loss = (
                    self.action_type_weight * action_loss +
                    self.target_element_weight * target_loss +
                    self.value_weight * value_loss
                )
                
                # Compute accuracies
                action_pred = torch.argmax(outputs["action_type_logits"], dim=-1)
                action_acc = (action_pred == labels["action_type"]).float().mean()
                
                target_pred = torch.argmax(outputs["target_element_logits"], dim=-1)
                # Only compute accuracy for valid targets (not -1)
                valid_targets = labels["target_element"] != -1
                if valid_targets.any():
                    target_acc = (target_pred[valid_targets] == labels["target_element"][valid_targets]).float().mean()
                else:
                    target_acc = torch.tensor(0.0)
                
                # Accumulate
                total_loss += loss.item()
                total_action_acc += action_acc.item()
                total_target_acc += target_acc.item()
                num_batches += 1
        
        return {
            "loss": total_loss / num_batches,
            "action_acc": total_action_acc / num_batches,
            "target_acc": total_target_acc / num_batches
        }
    
    def _print_epoch_summary(self, train_metrics: Dict, val_metrics: Dict):
        """Print epoch summary"""
        print(f"\nEpoch {self.epoch+1}/{self.num_epochs} Summary:")
        print(f"  Train - Loss: {train_metrics['loss']:.4f}, Time: {train_metrics['time']:.1f}s")
        print(f"  Val   - Loss: {val_metrics['loss']:.4f}, "
              f"Action Acc: {val_metrics['action_acc']:.2%}, "
              f"Target Acc: {val_metrics['target_acc']:.2%}")
    
    def _save_checkpoint(self, filename: str):
        """Save training checkpoint"""
        checkpoint_path = self.output_dir / filename
        
        checkpoint = {
            "epoch": self.epoch,
            "global_step": self.global_step,
            "model_state_dict": self.model.state_dict(),
            "optimizer_state_dict": self.optimizer.state_dict(),
            "scheduler_state_dict": self.scheduler.state_dict(),
            "best_val_loss": self.best_val_loss,
            "config": self.config,
            # Model config
            "vocab_size": self.model.vocab_size,
            "num_action_types": self.model.num_action_types,
            "max_elements": self.model.max_elements,
            "embedding_dim": self.model.embedding_dim,
            "hidden_dim": self.model.hidden_dim
        }
        
        torch.save(checkpoint, checkpoint_path)
    
    def _save_history(self):
        """Save training history to JSON"""
        history = {
            "train": self.train_history,
            "val": self.val_history,
            "config": self.config
        }
        
        history_path = self.output_dir / "training_history.json"
        with open(history_path, 'w') as f:
            json.dump(history, f, indent=2)
        
        print(f"Training history saved to: {history_path}")
    
    def load_checkpoint(self, checkpoint_path: Path):
        """Load checkpoint to resume training"""
        checkpoint = torch.load(checkpoint_path, map_location=self.device)
        
        self.model.load_state_dict(checkpoint["model_state_dict"])
        self.optimizer.load_state_dict(checkpoint["optimizer_state_dict"])
        self.scheduler.load_state_dict(checkpoint["scheduler_state_dict"])
        self.epoch = checkpoint["epoch"]
        self.global_step = checkpoint["global_step"]
        self.best_val_loss = checkpoint["best_val_loss"]
        
        print(f"Loaded checkpoint from epoch {self.epoch+1}")
