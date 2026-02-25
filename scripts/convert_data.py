"""
Script to convert explorer logs to unified trajectories.

Uses adapters to convert explorer-specific formats to our standard format.
"""

import sys
from pathlib import Path
import argparse

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from adapters.webtactix_adapter import WebTactiXAdapter
from adapters.agenttrek_adapter import AgentTrekAdapter


def get_adapter(explorer_name: str):
    """Get appropriate adapter for explorer"""
    adapters = {
        "webtactix": WebTactiXAdapter(),
        "agenttrek": AgentTrekAdapter(),
    }
    
    adapter = adapters.get(explorer_name)
    if not adapter:
        raise ValueError(f"Unknown explorer: {explorer_name}")
    
    return adapter


def convert_data(explorer_name: str, input_dir: Path, output_dir: Path):
    """
    Convert explorer logs to unified trajectories.
    
    Args:
        explorer_name: Name of explorer
        input_dir: Directory containing raw logs
        output_dir: Directory to save unified trajectories
    """
    print(f"Converting {explorer_name} logs to trajectories")
    print(f"  Input: {input_dir}")
    print(f"  Output: {output_dir}")
    
    # Get adapter
    adapter = get_adapter(explorer_name)
    
    # Convert
    num_trajectories = adapter.convert_directory(input_dir, output_dir)
    
    print(f"\n✓ Conversion complete!")
    print(f"  Converted {num_trajectories} trajectories")
    print(f"\nNext step: Clean data with:")
    print(f"  python scripts/clean_data.py --input {output_dir}")


def main():
    parser = argparse.ArgumentParser(description="Convert explorer logs to unified trajectories")
    parser.add_argument(
        "--explorer",
        type=str,
        required=True,
        choices=["webtactix", "agenttrek"],
        help="Explorer name"
    )
    parser.add_argument(
        "--input",
        type=str,
        help="Input directory (default: data/raw/<explorer>)"
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Output directory (default: data/trajectories/<explorer>)"
    )
    
    args = parser.parse_args()
    
    # Set default paths
    input_dir = Path(args.input) if args.input else Path(f"data/raw/{args.explorer}")
    output_dir = Path(args.output) if args.output else Path(f"data/trajectories/{args.explorer}")
    
    if not input_dir.exists():
        print(f"ERROR: Input directory does not exist: {input_dir}")
        print(f"Run explorer first: python scripts/run_explorer.py --explorer {args.explorer} --task 'your task'")
        sys.exit(1)
    
    convert_data(args.explorer, input_dir, output_dir)


if __name__ == "__main__":
    main()
