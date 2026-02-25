#!/usr/bin/env python3
"""
Explorer output conversion script.

This script converts external LLM explorer outputs (WebTactix, AgentTrek, etc.)
into the unified trajectory format used by the training pipeline.

Usage:
    python scripts/convert_explorer_output.py --adapter webtactix --input explorer_log.json
    python scripts/convert_explorer_output.py --adapter agenttrek --input trace.json --output data/trajectories/offline/
    
This script is the ONLY way to bring external explorer data into the system.
All explorer outputs must go through adapters to maintain architectural boundaries.
"""

import argparse
import sys
from pathlib import Path
import json

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from adapters.registry import create_adapter, list_adapters, print_available_adapters
from adapters.base_adapter import AdapterError


def convert_single_file(adapter_name: str, input_path: Path, output_path: Path, verbose: bool = True):
    """
    Convert a single explorer output file to trajectory.
    
    Args:
        adapter_name: Name of adapter to use
        input_path: Path to explorer output file
        output_path: Path to save trajectory JSON
        verbose: Print progress messages
    """
    if verbose:
        print(f"Converting {input_path.name} using {adapter_name} adapter...")
    
    try:
        # Create adapter
        adapter = create_adapter(adapter_name)
        
        # Convert
        trajectory = adapter.convert(input_path, output_path)
        
        # Print summary
        if verbose:
            print(f"\n✓ Conversion successful!")
            print(f"  Task: {trajectory.task}")
            print(f"  Steps: {len(trajectory.steps)}")
            print(f"  Success: {trajectory.success}")
            print(f"  Explorer: {trajectory.meta.get('explorer', 'unknown')}")
            if output_path:
                print(f"  Saved to: {output_path}")
        
        return trajectory
        
    except AdapterError as e:
        print(f"\n✗ Adapter error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


def convert_directory(adapter_name: str, input_dir: Path, output_dir: Path, verbose: bool = True):
    """
    Convert all explorer output files in a directory.
    
    Args:
        adapter_name: Name of adapter to use
        input_dir: Directory containing explorer outputs
        output_dir: Directory to save trajectories
        verbose: Print progress messages
    """
    # Find all JSON files in input directory
    json_files = list(input_dir.glob("*.json"))
    
    if not json_files:
        print(f"No JSON files found in {input_dir}", file=sys.stderr)
        sys.exit(1)
    
    if verbose:
        print(f"Found {len(json_files)} files to convert\n")
    
    # Convert each file
    success_count = 0
    failed_files = []
    
    for i, input_path in enumerate(json_files, 1):
        if verbose:
            print(f"[{i}/{len(json_files)}] {input_path.name}...")
        
        # Generate output filename
        output_path = output_dir / f"{input_path.stem}_trajectory.json"
        
        try:
            adapter = create_adapter(adapter_name)
            trajectory = adapter.convert(input_path, output_path)
            
            if verbose:
                print(f"  ✓ {len(trajectory.steps)} steps, success={trajectory.success}")
            
            success_count += 1
            
        except Exception as e:
            if verbose:
                print(f"  ✗ Failed: {e}")
            failed_files.append(input_path.name)
    
    # Print summary
    if verbose:
        print(f"\n{'='*60}")
        print(f"Conversion Summary")
        print(f"{'='*60}")
        print(f"Total files: {len(json_files)}")
        print(f"Successful: {success_count}")
        print(f"Failed: {len(failed_files)}")
        
        if failed_files:
            print(f"\nFailed files:")
            for filename in failed_files:
                print(f"  - {filename}")


def main():
    parser = argparse.ArgumentParser(
        description="Convert explorer outputs to unified trajectory format",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Convert single file
  python scripts/convert_explorer_output.py --adapter webtactix --input log.json --output data/trajectories/offline/traj.json
  
  # Convert all files in directory
  python scripts/convert_explorer_output.py --adapter agenttrek --input data/raw/agenttrek/ --output data/trajectories/offline/
  
  # List available adapters
  python scripts/convert_explorer_output.py --list-adapters
        """
    )
    
    parser.add_argument(
        "--adapter",
        type=str,
        help="Adapter to use (webtactix, agenttrek, etc.)"
    )
    
    parser.add_argument(
        "--input",
        type=str,
        help="Input file or directory containing explorer outputs"
    )
    
    parser.add_argument(
        "--output",
        type=str,
        help="Output file or directory for trajectories (default: data/trajectories/offline/)"
    )
    
    parser.add_argument(
        "--list-adapters",
        action="store_true",
        help="List available adapters and exit"
    )
    
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress progress messages"
    )
    
    args = parser.parse_args()
    
    # List adapters if requested
    if args.list_adapters:
        print_available_adapters()
        return
    
    # Validate arguments
    if not args.adapter or not args.input:
        parser.print_help()
        print("\nError: --adapter and --input are required", file=sys.stderr)
        sys.exit(1)
    
    # Verify adapter exists
    available_adapters = list_adapters()
    if args.adapter not in available_adapters:
        print(f"Error: Unknown adapter '{args.adapter}'", file=sys.stderr)
        print(f"Available adapters: {', '.join(available_adapters)}", file=sys.stderr)
        sys.exit(1)
    
    # Parse paths
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: Input path does not exist: {input_path}", file=sys.stderr)
        sys.exit(1)
    
    # Determine output path
    if args.output:
        output_path = Path(args.output)
    else:
        # Default output directory
        output_path = Path("data/trajectories/offline")
    
    verbose = not args.quiet
    
    # Convert single file or directory
    if input_path.is_file():
        # Single file conversion
        if output_path.is_dir() or not output_path.suffix:
            # Output is directory, generate filename
            output_path = output_path / f"{input_path.stem}_trajectory.json"
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        convert_single_file(args.adapter, input_path, output_path, verbose)
        
    elif input_path.is_dir():
        # Directory conversion
        output_path.mkdir(parents=True, exist_ok=True)
        convert_directory(args.adapter, input_path, output_path, verbose)
        
    else:
        print(f"Error: Invalid input path: {input_path}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
