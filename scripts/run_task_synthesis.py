"""
Script to run Task Synthesis (Phase 3) on exploration results.

Usage:
    python scripts/run_task_synthesis.py --input data/raw/agenttrek --output data/tasks
    
    # With specific domain
    python scripts/run_task_synthesis.py --input data/raw/agenttrek --output data/tasks --domain ecommerce
    
    # With auto-detection (default)
    python scripts/run_task_synthesis.py --input data/raw/agenttrek --output data/tasks
"""

import json
import argparse
from pathlib import Path
import sys
import logging

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from exploration import TaskSynthesizer, Screen, ActionSemantic, ScreenType
from exploration.schema import ExplorationResult

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_exploration_results(input_dir: Path) -> ExplorationResult:
    """
    Load exploration results from directory containing:
    - screens.jsonl (JSONL format - newline-delimited JSON)
    - actions.jsonl (optional, JSONL format)
    - transitions.jsonl (JSONL format)
    - metadata.json (regular JSON)
    
    Args:
        input_dir: Directory containing exploration result files
        
    Returns:
        ExplorationResult object
    """
    logger.info(f"Loading exploration results from: {input_dir}")
    
    screens_file = input_dir / "screens.jsonl"
    metadata_file = input_dir / "metadata.json"
    transitions_file = input_dir / "transitions.jsonl"
    actions_file = input_dir / "actions.jsonl"
    
    # Load screens (JSONL format)
    if not screens_file.exists():
        raise FileNotFoundError(f"screens.jsonl not found in {input_dir}")
    
    screens_data = []
    with open(screens_file, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                screens_data.append(json.loads(line))
    
    logger.info(f"Loaded {len(screens_data)} screens")
    
    # Load metadata (regular JSON)
    metadata = {}
    if metadata_file.exists():
        with open(metadata_file, 'r', encoding='utf-8') as f:
            metadata = json.load(f)
        logger.info(f"Loaded metadata: {metadata.get('explorer_name', 'unknown')} explorer")
    
    # Load transitions (JSONL format)
    transitions_data = []
    if transitions_file.exists():
        with open(transitions_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    transitions_data.append(json.loads(line))
        logger.info(f"Loaded {len(transitions_data)} transitions")
    
    # Load actions if available (JSONL format)
    # Build a lookup dictionary: action_id -> action data
    actions_lookup = {}
    if actions_file.exists():
        with open(actions_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    action_data = json.loads(line)
                    action_id = action_data.get('action_id')
                    if action_id:
                        actions_lookup[action_id] = action_data
        logger.info(f"Loaded {len(actions_lookup)} actions from actions.jsonl")
    
    # Convert to Screen objects
    screens = []
    for screen_data in screens_data:
        # Handle different screen formats
        screen_id = screen_data.get('screen_id', '')
        url = screen_data.get('url', '')
        
        # Get screen type
        screen_type_str = screen_data.get('screen_type', 'other')
        try:
            screen_type = ScreenType(screen_type_str.lower())
        except ValueError:
            screen_type = ScreenType.OTHER
        
        # Create screen
        screen = Screen(
            screen_id=screen_id,
            url=url,
            dom_snapshot=screen_data.get('dom_snapshot', ''),
            visible_text=screen_data.get('visible_text', ''),
            semantic_summary=screen_data.get('semantic_summary', screen_data.get('summary', '')),
            screen_type=screen_type,
            timestamp=screen_data.get('timestamp', ''),
            screenshot=screen_data.get('screenshot'),
            meta=screen_data.get('meta', {})
        )
        
        # Get actions for this screen
        action_objects = []
        
        # Method 1: Actions referenced by action_ids in meta (new format)
        action_ids = screen_data.get('meta', {}).get('action_ids', [])
        if action_ids and actions_lookup:
            for action_id in action_ids:
                if action_id in actions_lookup:
                    action_data = actions_lookup[action_id]
                    # Extract semantic part
                    semantic = action_data.get('semantic', {})
                    if semantic:
                        action = ActionSemantic(
                            intent=semantic.get('intent'),
                            object=semantic.get('object'),
                            context=semantic.get('context'),
                            description=semantic.get('description'),
                            confidence=semantic.get('confidence', 0.75),
                            action_id=semantic.get('action_id', action_id)
                        )
                        action_objects.append(action)
        
        # Method 2: Actions embedded in screen data (old format fallback)
        elif 'actions' in screen_data or 'semantic_actions' in screen_data or 'available_actions' in screen_data:
            screen_actions = screen_data.get('actions') or screen_data.get('semantic_actions') or screen_data.get('available_actions', [])
            for action_data in screen_actions:
                if isinstance(action_data, dict):
                    action = ActionSemantic(
                        intent=action_data.get('intent'),
                        object=action_data.get('object'),
                        context=action_data.get('context'),
                        description=action_data.get('description'),
                        confidence=action_data.get('confidence', 0.75),
                        action_id=action_data.get('action_id', '')
                    )
                    action_objects.append(action)
        
        screen.actions = action_objects
        screens.append(screen)
    
    logger.info(f"Converted {len(screens)} screens with semantic actions")
    
    return screens, metadata


def save_task_graph(task_graph, output_dir: Path, metadata: dict):
    """
    Save task graph to output directory.
    
    Creates:
    - tasks.json: All synthesized tasks
    - tasks_summary.txt: Human-readable summary
    
    Args:
        task_graph: TaskGraph object
        output_dir: Directory to save results
        metadata: Original exploration metadata
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Save tasks as JSON
    tasks_file = output_dir / "tasks.json"
    task_dict = task_graph.to_dict()
    
    # Add metadata
    task_dict['metadata'] = {
        'original_explorer': metadata.get('explorer', 'unknown'),
        'original_url': metadata.get('start_url', 'unknown'),
        'synthesis_timestamp': metadata.get('timestamp', ''),
    }
    
    with open(tasks_file, 'w', encoding='utf-8') as f:
        json.dump(task_dict, f, indent=2, ensure_ascii=False)
    
    logger.info(f"Saved tasks to: {tasks_file}")
    
    # Save summary
    summary_file = output_dir / "tasks_summary.txt"
    with open(summary_file, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("TASK SYNTHESIS SUMMARY\n")
        f.write("=" * 80 + "\n\n")
        
        f.write(f"Total tasks: {len(task_graph.tasks)}\n")
        f.write(f"Total screens: {task_dict['meta'].get('total_screens', 0)}\n")
        f.write(f"Total actions: {task_dict['meta'].get('total_actions', 0)}\n")
        f.write(f"Unique actions: {task_dict['meta'].get('unique_actions', 0)}\n\n")
        
        # Group by priority
        from exploration import TaskPriority
        
        for priority in [TaskPriority.INITIAL, TaskPriority.INTERMEDIATE, TaskPriority.TERMINAL]:
            priority_tasks = task_graph.get_tasks_by_priority(priority)
            if priority_tasks:
                f.write(f"\n{priority.value.upper()} TASKS ({len(priority_tasks)}):\n")
                f.write("-" * 80 + "\n")
                for task in priority_tasks:
                    f.write(f"\n  Task: {task.name}\n")
                    f.write(f"  ID: {task.task_id}\n")
                    f.write(f"  Description: {task.description}\n")
                    f.write(f"  Confidence: {task.confidence:.2f}\n")
                    f.write(f"  Related Actions: {len(task.related_actions)}\n")
                    f.write(f"  Entry Screens: {len(task.entry_screens)}\n")
    
    logger.info(f"Saved summary to: {summary_file}")


def main():
    parser = argparse.ArgumentParser(
        description="Run Task Synthesis (Phase 3) on exploration results"
    )
    parser.add_argument(
        '--input', '-i',
        type=str,
        required=True,
        help='Input directory containing exploration results (screens.json, etc.)'
    )
    parser.add_argument(
        '--output', '-o',
        type=str,
        required=True,
        help='Output directory for synthesized tasks'
    )
    parser.add_argument(
        '--domain', '-d',
        type=str,
        default=None,
        choices=['ecommerce', 'news', 'social', 'banking', 'streaming', 'generic'],
        help='Domain type for pattern matching (default: auto-detect)'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Convert paths
    input_dir = Path(args.input)
    output_dir = Path(args.output)
    
    if not input_dir.exists():
        logger.error(f"Input directory not found: {input_dir}")
        sys.exit(1)
    
    try:
        # Load exploration results
        screens, metadata = load_exploration_results(input_dir)
        
        if len(screens) == 0:
            logger.error("No screens found in exploration results")
            sys.exit(1)
        
        # Initialize task synthesizer
        if args.domain:
            logger.info(f"Using explicit domain: {args.domain}")
            synthesizer = TaskSynthesizer(domain=args.domain)
        else:
            logger.info("Using auto-detection for domain")
            synthesizer = TaskSynthesizer()
        
        # Synthesize tasks
        logger.info("Starting task synthesis...")
        task_graph = synthesizer.synthesize(screens)
        
        # Print summary
        logger.info(f"✓ Task synthesis complete!")
        logger.info(f"  Generated {len(task_graph.tasks)} tasks")
        logger.info(f"  From {len(screens)} screens")
        logger.info(f"  Total actions: {task_graph.meta.get('total_actions', 0)}")
        
        # Save results
        save_task_graph(task_graph, output_dir, metadata)
        
        logger.info(f"\n✓ Results saved to: {output_dir}")
        logger.info(f"  - tasks.json: Complete task graph")
        logger.info(f"  - tasks_summary.txt: Human-readable summary")
        
    except Exception as e:
        logger.error(f"Error during task synthesis: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
