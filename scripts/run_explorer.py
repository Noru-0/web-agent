"""
Script to run external explorers (offline data collection).

This script interfaces with explorers but is separate from core agent.
"""

import sys
from pathlib import Path
import argparse
import json

# NOTE: This script CAN import from explorers/ since it's part of the data collection pipeline
# The core agent and training code will NEVER run this script or import from explorers/


def run_explorer(explorer_name: str, task: str, config: dict):
    """
    Run an external explorer to generate training data.
    
    Args:
        explorer_name: Name of explorer (webtactix, agenttrek, etc.)
        task: Task description
        config: Explorer-specific configuration
    """
    print(f"Running explorer: {explorer_name}")
    print(f"Task: {task}")
    print(f"Config: {json.dumps(config, indent=2)}")
    
    # Create output directory
    output_dir = Path(f"data/raw/{explorer_name}")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    if explorer_name == "webtactix":
        # Example: Run WebTactiX
        # In reality, this would interface with the actual explorer
        print("\nWebTactiX explorer would run here...")
        print("This would generate logs in explorer's own format")
        
        # Placeholder: Create dummy log
        dummy_log = {
            "task": task,
            "steps": [
                {
                    "observation": {"url": "https://example.com", "html": "<html>...</html>"},
                    "action": {"type": "click", "element": "button#submit"},
                    "next_observation": {"url": "https://example.com/success", "html": "<html>...</html>"},
                    "success": True
                }
            ],
            "final_success": True
        }
        
        output_file = output_dir / f"{task.replace(' ', '_')}.json"
        with open(output_file, 'w') as f:
            json.dump(dummy_log, f, indent=2)
        
        print(f"\nLog saved to: {output_file}")
    
    elif explorer_name == "agenttrek":
        # Example: Run AgentTrek
        print("\nAgentTrek explorer would run here...")
        
        dummy_log = {
            "mission": task,
            "episodes": [
                {
                    "state": {"current_url": "https://example.com", "dom": "<html>...</html>"},
                    "act": {"action": "tap", "selector": "button"},
                    "next": {"current_url": "https://example.com/done", "dom": "<html>...</html>"},
                    "r": 1.0,
                    "done": True
                }
            ],
            "success": True
        }
        
        output_file = output_dir / f"{task.replace(' ', '_')}.json"
        with open(output_file, 'w') as f:
            json.dump(dummy_log, f, indent=2)
        
        print(f"\nLog saved to: {output_file}")
    
    else:
        print(f"ERROR: Unknown explorer: {explorer_name}")
        sys.exit(1)
    
    print(f"\n✓ Explorer run complete!")
    print(f"Next step: Convert logs to trajectories with:")
    print(f"  python scripts/convert_data.py --explorer {explorer_name}")


def main():
    parser = argparse.ArgumentParser(description="Run external explorer for data collection")
    parser.add_argument(
        "--explorer",
        type=str,
        default=None,  # Will use .env default if not specified
        choices=["webtactix", "agenttrek"],
        help="Explorer to run (defaults from .env: EXPLORER_PROVIDER)"
    )
    parser.add_argument(
        "--task",
        type=str,
        required=True,
        help="Task description"
    )
    parser.add_argument(
        "--model",
        type=str,
        default=None,  # Will use .env default
        help="Model to use (defaults from .env: EXPLORER_MODEL)"
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=None,  # Will use .env default
        help="Temperature for model (defaults from .env: EXPLORER_TEMPERATURE)"
    )
    parser.add_argument(
        "--max_steps",
        type=int,
        default=None,  # Will use .env default
        help="Maximum steps (defaults from .env: EXPLORER_MAX_STEPS)"
    )
    parser.add_argument(
        "--config",
        type=str,
        help="Path to explorer config file (optional, overrides other settings)"
    )
    
    args = parser.parse_args()
    
    # Load .env defaults
    from utils.env import env
    
    # Config file takes precedence over everything
    if args.config:
        with open(args.config, 'r') as f:
            config = json.load(f)
        explorer = args.explorer or config.get("explorer", env.get("EXPLORER_PROVIDER", "agenttrek"))
    else:
        # Use CLI args or .env defaults
        explorer = args.explorer or env.get("EXPLORER_PROVIDER", "agenttrek")
        model = args.model or env.get("EXPLORER_MODEL", "meta-llama/Llama-3.1-8B-Instruct")
        temperature = args.temperature if args.temperature is not None else env.get_float("EXPLORER_TEMPERATURE", 0.2)
        max_steps = args.max_steps if args.max_steps is not None else env.get_int("EXPLORER_MAX_STEPS", 50)
        
        config = {
            "model": model,
            "temperature": temperature,
            "max_steps": max_steps
        }
    
    run_explorer(explorer, args.task, config)


if __name__ == "__main__":
    main()
