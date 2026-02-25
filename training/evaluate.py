"""
Evaluation script for trained SLM web agent policy.

This script evaluates a trained policy model on held-out trajectory data.
It operates completely offline and measures action prediction accuracy.

ARCHITECTURAL BOUNDARIES:
- Imports: training/, schema.py, torch, standard library ONLY
- No imports from: explorers, adapters, envs, browser, agents
- Pure offline evaluation on trajectory data

Usage:
    python training/evaluate.py --checkpoint checkpoints/best_model.pt --data_dir data/trajectories
    
    # Evaluate on specific source
    python training/evaluate.py --checkpoint checkpoints/best_model.pt --sources offline
"""

import sys
from pathlib import Path
import argparse
from typing import Dict, Any
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import torch
    from torch.utils.data import DataLoader
    TORCH_AVAILABLE = True
except ImportError:
    print("ERROR: PyTorch not installed. Install with: pip install torch")
    sys.exit(1)

from training.dataset import TrajectoryDataset
from training.collate import StateEncoder, ActionEncoder, create_collate_fn
from training.model import WebAgentPolicy
from schema import ActionType


def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="Evaluate trained SLM web agent policy",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    # Model arguments
    parser.add_argument(
        "--checkpoint",
        type=str,
        required=True,
        help="Path to model checkpoint"
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
        default=["offline"],
        help="Data sources to evaluate on"
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
        help="Maximum number of trajectories to evaluate (for debugging)"
    )
    
    # Evaluation arguments
    parser.add_argument(
        "--batch_size",
        type=int,
        default=32,
        help="Batch size for evaluation"
    )
    parser.add_argument(
        "--device",
        type=str,
        default="auto",
        choices=["auto", "cpu", "cuda"],
        help="Device to use for evaluation"
    )
    
    return parser.parse_args()


def evaluate_model(
    model: WebAgentPolicy,
    dataset: TrajectoryDataset,
    state_encoder: StateEncoder,
    action_encoder: ActionEncoder,
    batch_size: int,
    device: str
) -> Dict[str, Any]:
    """
    Evaluate model on dataset.
    
    Args:
        model: Trained policy model
        dataset: Evaluation dataset
        state_encoder: State encoder
        action_encoder: Action encoder
        batch_size: Batch size
        device: Device to use
        
    Returns:
        Dictionary with evaluation metrics
    """
    model.to(device)
    model.eval()
    
    # Create data loader
    collate = create_collate_fn(state_encoder, action_encoder)
    loader = DataLoader(
        dataset,
        batch_size=batch_size,
        shuffle=False,
        collate_fn=collate,
        num_workers=0
    )
    
    # Metrics
    total_samples = 0
    correct_action_type = 0
    correct_target_element = 0
    
    # Per-action metrics
    action_type_counts = defaultdict(int)
    action_type_correct = defaultdict(int)
    
    print(f"\nEvaluating on {len(dataset)} samples...")
    
    with torch.no_grad():
        for batch_idx, batch in enumerate(loader):
            # Move batch to device
            states = {k: v.to(device) for k, v in batch["states"].items()}
            labels = {k: v.to(device) for k, v in batch["labels"].items()}
            
            # Forward pass (without teacher forcing for value)
            outputs = model(
                url=states["url"],
                text=states["text"],
                elements=states["elements"],
                element_mask=states["element_mask"],
                value_input=None
            )
            
            # Predict action type
            action_type_pred = torch.argmax(outputs["action_type_logits"], dim=-1)
            action_type_correct_batch = (action_type_pred == labels["action_type"])
            
            # Predict target element
            target_element_pred = torch.argmax(outputs["target_element_logits"], dim=-1)
            # Only evaluate for valid targets (not -1)
            valid_targets = labels["target_element"] != -1
            if valid_targets.any():
                target_correct_batch = (
                    target_element_pred[valid_targets] == labels["target_element"][valid_targets]
                )
                correct_target_element += target_correct_batch.sum().item()
            
            # Accumulate metrics
            correct_action_type += action_type_correct_batch.sum().item()
            total_samples += len(action_type_pred)
            
            # Per-action metrics
            for i in range(len(labels["action_type"])):
                action_idx = labels["action_type"][i].item()
                action_type = action_encoder.decode_action_type(action_idx)
                action_type_counts[action_type.value] += 1
                if action_type_correct_batch[i]:
                    action_type_correct[action_type.value] += 1
            
            # Progress
            if (batch_idx + 1) % 10 == 0:
                print(f"  Processed {(batch_idx + 1) * batch_size}/{len(dataset)} samples")
    
    # Compute final metrics
    action_acc = correct_action_type / total_samples if total_samples > 0 else 0
    target_acc = correct_target_element / sum(valid_targets.sum().item() for _ in [None]) if total_samples > 0 else 0
    
    # Per-action accuracies
    per_action_acc = {}
    for action_type, count in action_type_counts.items():
        acc = action_type_correct[action_type] / count if count > 0 else 0
        per_action_acc[action_type] = {
            "count": count,
            "correct": action_type_correct[action_type],
            "accuracy": acc
        }
    
    return {
        "total_samples": total_samples,
        "action_accuracy": action_acc,
        "target_accuracy": target_acc,
        "per_action_accuracy": per_action_acc
    }


def print_results(metrics: Dict[str, Any]):
    """Print evaluation results"""
    print(f"\n{'='*60}")
    print(f"Evaluation Results")
    print(f"{'='*60}")
    print(f"Total samples: {metrics['total_samples']}")
    print(f"Action type accuracy: {metrics['action_accuracy']:.2%}")
    print(f"Target element accuracy: {metrics['target_accuracy']:.2%}")
    
    print(f"\nPer-Action Breakdown:")
    print(f"{'Action Type':<15} {'Count':<8} {'Correct':<8} {'Accuracy':<10}")
    print(f"{'-'*50}")
    
    for action_type, stats in sorted(metrics['per_action_accuracy'].items()):
        print(f"{action_type:<15} {stats['count']:<8} {stats['correct']:<8} {stats['accuracy']:<10.2%}")
    
    print(f"{'='*60}\n")


def main():
    """Main evaluation function"""
    args = parse_args()
    
    # Determine device
    if args.device == "auto":
        device = "cuda" if torch.cuda.is_available() else "cpu"
    else:
        device = args.device
    
    print(f"\n{'='*60}")
    print(f"SLM Web Agent Evaluation")
    print(f"{'='*60}")
    print(f"Checkpoint: {args.checkpoint}")
    print(f"Device: {device}")
    print(f"Data directory: {args.data_dir}")
    print(f"Sources: {args.sources}")
    print(f"{'='*60}\n")
    
    # Load checkpoint
    print("Loading checkpoint...")
    checkpoint_path = Path(args.checkpoint)
    if not checkpoint_path.exists():
        print(f"ERROR: Checkpoint not found: {checkpoint_path}")
        sys.exit(1)
    
    checkpoint = torch.load(checkpoint_path, map_location=device)
    
    # Create model
    print("Creating model...")
    model = WebAgentPolicy(
        vocab_size=checkpoint["vocab_size"],
        num_action_types=checkpoint["num_action_types"],
        max_elements=checkpoint["max_elements"],
        embedding_dim=checkpoint["embedding_dim"],
        hidden_dim=checkpoint["hidden_dim"]
    )
    model.load_state_dict(checkpoint["model_state_dict"])
    model.to(device)
    
    print(f"Loaded model from epoch {checkpoint.get('epoch', 'unknown')}")
    
    # Create encoders (must match training)
    print("\nCreating encoders...")
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
    
    # Load evaluation dataset
    print("\nLoading evaluation dataset...")
    dataset = TrajectoryDataset(
        data_dir=args.data_dir,
        sources=args.sources,
        filter_failed=args.filter_failed,
        filter_empty=True,
        max_trajectories=args.max_trajectories,
        verbose=True
    )
    
    # Evaluate
    metrics = evaluate_model(
        model=model,
        dataset=dataset,
        state_encoder=state_encoder,
        action_encoder=action_encoder,
        batch_size=args.batch_size,
        device=device
    )
    
    # Print results
    print_results(metrics)
    
    # Save results
    output_dir = Path(args.checkpoint).parent
    results_path = output_dir / "evaluation_results.json"
    
    # Convert per_action_accuracy to serializable format
    serializable_metrics = {
        "total_samples": metrics["total_samples"],
        "action_accuracy": metrics["action_accuracy"],
        "target_accuracy": metrics["target_accuracy"],
        "per_action_accuracy": metrics["per_action_accuracy"]
    }
    
    import json
    with open(results_path, 'w') as f:
        json.dump(serializable_metrics, f, indent=2)
    
    print(f"Results saved to: {results_path}")


if __name__ == "__main__":
    main()
