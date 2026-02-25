"""
Training script for SLM web agent policy.

This script trains a Small Language Model to predict actions from observations
using unified trajectory data. It operates completely offline and has no
dependencies on explorers, adapters, or runtime components.

ARCHITECTURAL BOUNDARIES:
- Imports: training/, schema.py, torch, standard library ONLY
- No imports from: explorers, adapters, envs, browser, agents
- Pure offline training on trajectory data

Usage:
    python training/train.py --data_dir data/trajectories --epochs 10 --batch_size 32
    
    # Train on specific sources
    python training/train.py --data_dir data/trajectories --sources online offline
    
    # Resume from checkpoint
    python training/train.py --resume checkpoints/checkpoint_epoch_5.pt
"""

import sys
from pathlib import Path
import argparse

sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    print("ERROR: PyTorch not installed. Install with: pip install torch")
    sys.exit(1)

from training.dataset import TrajectoryDataset
from training.collate import StateEncoder, ActionEncoder
from training.model import WebAgentPolicy
from training.trainer import Trainer
from schema import ActionType


def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="Train SLM web agent policy on unified trajectories",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    # Data arguments
    parser.add_argument(
        "--data_dir",
        type=str,
        default="data/trajectories",
        help="Directory containing trajectory data"
    )
    parser.add_argument(
        "--sources",
        nargs="+",
        choices=["online", "offline"],
        default=["online", "offline"],
        help="Data sources to load from"
    )
    parser.add_argument(
        "--filter_failed",
        action="store_true",
        help="Filter out failed trajectories"
    )
    parser.add_argument(
        "--max_trajectories",
        type=int,
        default=None,
        help="Maximum number of trajectories to load (for debugging)"
    )
    parser.add_argument(
        "--train_split",
        type=float,
        default=0.8,
        help="Fraction of data for training (rest for validation)"
    )
    
    # Model arguments
    parser.add_argument(
        "--embedding_dim",
        type=int,
        default=128,
        help="Embedding dimension"
    )
    parser.add_argument(
        "--hidden_dim",
        type=int,
        default=256,
        help="Hidden dimension"
    )
    parser.add_argument(
        "--num_layers",
        type=int,
        default=2,
        help="Number of LSTM layers"
    )
    parser.add_argument(
        "--dropout",
        type=float,
        default=0.1,
        help="Dropout probability"
    )
    
    # Training arguments
    parser.add_argument(
        "--epochs",
        type=int,
        default=10,
        help="Number of training epochs"
    )
    parser.add_argument(
        "--batch_size",
        type=int,
        default=32,
        help="Batch size"
    )
    parser.add_argument(
        "--lr",
        type=float,
        default=1e-3,
        help="Learning rate"
    )
    parser.add_argument(
        "--weight_decay",
        type=float,
        default=1e-5,
        help="Weight decay"
    )
    parser.add_argument(
        "--grad_clip",
        type=float,
        default=1.0,
        help="Gradient clipping value"
    )
    parser.add_argument(
        "--device",
        type=str,
        default="auto",
        choices=["auto", "cpu", "cuda"],
        help="Device to use for training"
    )
    
    # Loss weights
    parser.add_argument(
        "--action_type_weight",
        type=float,
        default=1.0,
        help="Weight for action type loss"
    )
    parser.add_argument(
        "--target_element_weight",
        type=float,
        default=0.5,
        help="Weight for target element loss"
    )
    parser.add_argument(
        "--value_weight",
        type=float,
        default=0.5,
        help="Weight for value prediction loss"
    )
    
    # Logging arguments
    parser.add_argument(
        "--log_interval",
        type=int,
        default=100,
        help="Log every N batches"
    )
    parser.add_argument(
        "--save_interval",
        type=int,
        default=1,
        help="Save checkpoint every N epochs"
    )
    parser.add_argument(
        "--output_dir",
        type=str,
        default="checkpoints",
        help="Output directory for checkpoints"
    )
    
    # Resume training
    parser.add_argument(
        "--resume",
        type=str,
        default=None,
        help="Path to checkpoint to resume from"
    )
    
    # Other
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed"
    )
    
    return parser.parse_args()


def main():
    """Main training function"""
    args = parse_args()
    
    # Load .env defaults (can be overridden by CLI args)
    from utils.env import env
    
    # Set random seed
    torch.manual_seed(args.seed)
    
    # Determine device (CLI arg > .env > auto-detect)
    if args.device == "auto":
        # Check .env first, then auto-detect
        env_device = env.get("SLM_DEVICE", "auto")
        if env_device != "auto":
            device = env_device
        else:
            device = "cuda" if torch.cuda.is_available() else "cpu"
    else:
        device = args.device
    
    print(f"\n{'='*60}")
    print(f"SLM Web Agent Training")
    print(f"{'='*60}")
    print(f"Device: {device}")
    print(f"Data directory: {args.data_dir}")
    print(f"Sources: {args.sources}")
    print(f"Output directory: {args.output_dir}")
    print(f"{'='*60}\n")
    
    # Load dataset
    print("Loading dataset...")
    dataset = TrajectoryDataset(
        data_dir=args.data_dir,
        sources=args.sources,
        filter_failed=args.filter_failed,
        filter_empty=True,
        max_trajectories=args.max_trajectories,
        verbose=True
    )
    
    # Split into train/val
    print(f"\nSplitting dataset (train: {args.train_split:.0%}, val: {1-args.train_split:.0%})...")
    train_dataset, val_dataset = dataset.split(
        train_ratio=args.train_split,
        shuffle=True,
        seed=args.seed
    )
    
    print(f"Train: {len(train_dataset)} steps from {len(train_dataset.trajectories)} trajectories")
    print(f"Val:   {len(val_dataset)} steps from {len(val_dataset.trajectories)} trajectories")
    
    # Create encoders
    print("\nCreating encoders...")
    state_encoder = StateEncoder(
        vocab_size=1000,
        max_text_length=512,
        max_url_length=128,
        max_elements=50,
        max_element_text_length=32
    )
    action_encoder = ActionEncoder(
        max_elements=50,
        max_value_length=128
    )
    
    print(f"State encoder vocab size: {state_encoder.vocab_size}")
    print(f"Action encoder: {action_encoder.num_action_types} action types")
    
    # Create model
    print("\nCreating model...")
    model = WebAgentPolicy(
        vocab_size=state_encoder.vocab_size,
        num_action_types=action_encoder.num_action_types,
        max_elements=state_encoder.max_elements,
        embedding_dim=args.embedding_dim,
        hidden_dim=args.hidden_dim,
        num_layers=args.num_layers,
        dropout=args.dropout
    )
    
    # Create training config
    config = {
        "device": device,
        "num_epochs": args.epochs,
        "batch_size": args.batch_size,
        "learning_rate": args.lr,
        "weight_decay": args.weight_decay,
        "grad_clip": args.grad_clip,
        "log_interval": args.log_interval,
        "save_interval": args.save_interval,
        "output_dir": args.output_dir,
        "action_type_weight": args.action_type_weight,
        "target_element_weight": args.target_element_weight,
        "value_weight": args.value_weight,
        # Data config
        "data_dir": args.data_dir,
        "sources": args.sources,
        "train_split": args.train_split,
        # Model config
        "embedding_dim": args.embedding_dim,
        "hidden_dim": args.hidden_dim,
        "num_layers": args.num_layers,
        "dropout": args.dropout,
        # Other
        "seed": args.seed
    }
    
    # Create trainer
    print("\nInitializing trainer...")
    trainer = Trainer(
        model=model,
        train_dataset=train_dataset,
        val_dataset=val_dataset,
        state_encoder=state_encoder,
        action_encoder=action_encoder,
        config=config
    )
    
    # Resume from checkpoint if specified
    if args.resume:
        print(f"\nResuming from checkpoint: {args.resume}")
        trainer.load_checkpoint(Path(args.resume))
    
    # Train
    trainer.train()
    
    print("\nTraining complete!")
    print(f"Final model saved to: {Path(args.output_dir) / 'final_model.pt'}")
    print(f"Best model saved to: {Path(args.output_dir) / 'best_model.pt'}")


if __name__ == "__main__":
    main()
