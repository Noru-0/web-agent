"""
Script to clean and validate trajectory data.
"""

import sys
from pathlib import Path
import argparse
import json
from typing import List

sys.path.insert(0, str(Path(__file__).parent.parent))
from schema import Trajectory


def clean_trajectory(traj: Trajectory) -> bool:
    """
    Clean and validate trajectory.
    
    Returns:
        True if trajectory is valid, False otherwise
    """
    # Remove empty steps
    traj.steps = [s for s in traj.steps if s.state and s.action and s.next_state]
    
    if not traj.steps:
        return False
    
    # Validate URLs
    for step in traj.steps:
        if not step.state.url or not step.next_state.url:
            return False
    
    # Validate actions
    for step in traj.steps:
        if not step.action.target:
            return False
    
    return True


def clean_data(input_dir: Path, output_dir: Path, min_steps: int = 1):
    """
    Clean trajectory data.
    
    Args:
        input_dir: Directory with raw trajectories
        output_dir: Directory to save cleaned trajectories
        min_steps: Minimum number of steps required
    """
    print(f"Cleaning trajectory data")
    print(f"  Input: {input_dir}")
    print(f"  Output: {output_dir}")
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    trajectory_files = list(input_dir.glob("*.json"))
    print(f"\nFound {len(trajectory_files)} trajectory files")
    
    valid_count = 0
    invalid_count = 0
    
    for traj_file in trajectory_files:
        try:
            with open(traj_file, 'r') as f:
                traj_data = json.load(f)
            
            traj = Trajectory.from_dict(traj_data)
            
            # Clean trajectory
            if not clean_trajectory(traj):
                invalid_count += 1
                print(f"  ✗ Invalid: {traj_file.name}")
                continue
            
            # Check minimum steps
            if len(traj.steps) < min_steps:
                invalid_count += 1
                print(f"  ✗ Too few steps: {traj_file.name} ({len(traj.steps)} steps)")
                continue
            
            # Save cleaned trajectory
            output_file = output_dir / traj_file.name
            with open(output_file, 'w') as f:
                json.dump(traj.to_dict(), f, indent=2)
            
            valid_count += 1
            print(f"  ✓ Cleaned: {traj_file.name} ({len(traj.steps)} steps)")
        
        except Exception as e:
            invalid_count += 1
            print(f"  ✗ Error: {traj_file.name}: {e}")
    
    print(f"\n✓ Cleaning complete!")
    print(f"  Valid: {valid_count}")
    print(f"  Invalid: {invalid_count}")
    print(f"\nNext step: Train model with:")
    print(f"  python training/train.py --data-dir {output_dir}")


def main():
    parser = argparse.ArgumentParser(description="Clean and validate trajectory data")
    parser.add_argument(
        "--input",
        type=str,
        default="data/trajectories",
        help="Input directory with raw trajectories"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="data/cleaned",
        help="Output directory for cleaned trajectories"
    )
    parser.add_argument(
        "--min-steps",
        type=int,
        default=1,
        help="Minimum number of steps required"
    )
    
    args = parser.parse_args()
    
    input_dir = Path(args.input)
    output_dir = Path(args.output)
    
    if not input_dir.exists():
        print(f"ERROR: Input directory does not exist: {input_dir}")
        sys.exit(1)
    
    clean_data(input_dir, output_dir, args.min_steps)


if __name__ == "__main__":
    main()
