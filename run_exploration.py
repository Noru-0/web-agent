#!/usr/bin/env python3
"""
Production exploration CLI.

Run exploration on any website to discover screens and semantic transitions.

Usage:
    python run_exploration.py --url https://example.com
    python run_exploration.py --url https://example.com --adapter agenttrek
    python run_exploration.py --url https://example.com --max-screens 100
"""

import asyncio
import argparse
import logging
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from workflows.explore import explore_website
from exploration.exploration_bridge import get_exploration_adapter
from envs.generic_env import GenericWebEnv
from exploration import TaskSynthesizer, LLMTaskSynthesizer, synthesize_tasks_with_llm
from exploration.storage import ExplorationStorage, url_to_folder_name
import json


def run_task_synthesis(
    explorer_name: str,
    output_base_dir: Path = None,
    use_llm: bool = False,
    llm_provider: str = "anthropic"
):
    """
    Automatically run task synthesis after exploration.

    Args:
        explorer_name: Name of the explorer (e.g., "agenttrek")
        output_base_dir: Base directory for output (defaults to data/tasks)
        use_llm: If True, use LLM-based synthesis (NEW); if False, use deterministic (OLD)
        llm_provider: LLM provider to use ("anthropic" or "openai")

    Returns:
        True if successful, False otherwise
    """
    logger = logging.getLogger(__name__)

    try:
        # Input directory
        input_dir = Path("data/raw") / explorer_name

        # Output directory
        if output_base_dir is None:
            output_base_dir = Path("data/tasks")
        output_dir = output_base_dir / explorer_name
        output_dir.mkdir(parents=True, exist_ok=True)

        logger.info("\n" + "=" * 60)
        logger.info(f"Running Task Synthesis (Phase 2)")
        logger.info(f"Method: {'LLM-based (NEW)' if use_llm else 'Deterministic (OLD)'}")
        logger.info("=" * 60)
        logger.info(f"Input: {input_dir}")
        logger.info(f"Output: {output_dir}")

        # Load exploration results
        storage = ExplorationStorage(explorer_name, auto_clean=False)
        screens = storage.load_screens()
        actions_map = {a.action_id: a for a in storage.load_actions()}

        logger.info(f"Loaded {len(screens)} screens")

        if use_llm:
            # NEW: LLM-based task synthesis (aligned with professor's feedback)
            logger.info(f"Using LLM-based synthesis with {llm_provider}")

            # Build ExplorationResult for LLM
            from exploration.schema import ExplorationResult
            exploration_result = ExplorationResult(
                screens={s.screen_id: s for s in screens},
                actions=actions_map,
                transitions=storage.load_transitions(),
                explorer_name=explorer_name,
                start_url=screens[0].url if screens else "",
                timestamp=""
            )

            # Synthesize with LLM
            try:
                synthesizer = LLMTaskSynthesizer(llm_provider=llm_provider)
                tasks = synthesizer.synthesize_tasks(exploration_result)

                logger.info(f"✅ Synthesized {len(tasks)} tasks with LLM")

                # Save results
                synthesizer.save_tasks(tasks, output_dir / "tasks_llm.json")
                synthesizer.save_summary(tasks, output_dir / "tasks_llm_summary.txt")

                logger.info("=" * 60)
                logger.info("LLM Task Synthesis Complete!")
                logger.info("=" * 60)
                logger.info(f"Results saved to: {output_dir}")
                logger.info(f"  - tasks_llm.json: Complete tasks")
                logger.info(f"  - tasks_llm_summary.txt: Human-readable summary")
                logger.info("=" * 60)

            except ImportError as e:
                logger.error(f"LLM library not installed: {e}")
                logger.error("Install with: pip install anthropic  or  pip install openai")
                return False
            except Exception as e:
                logger.error(f"LLM-based synthesis failed: {e}", exc_info=True)
                return False

        else:
            # OLD: Deterministic task synthesis
            logger.info("Using deterministic (algorithmic) synthesis")

            # Link actions to screens
            for screen in screens:
                action_ids = screen.meta.get('action_ids', [])
                screen_actions = []
                for action_id in action_ids:
                    if action_id in actions_map:
                        action = actions_map[action_id]
                        screen_actions.append(action.semantic)
                screen.actions = screen_actions

            # Create task synthesizer with auto-detection
            synthesizer = TaskSynthesizer()

            # Synthesize tasks
            task_graph = synthesizer.synthesize(screens)

            logger.info(f"Synthesized {len(task_graph.tasks)} tasks")
            logger.info(f"  - Initial tasks: {len(task_graph.get_tasks_by_priority('initial'))}")
            logger.info(f"  - Intermediate tasks: {len(task_graph.get_tasks_by_priority('intermediate'))}")
            logger.info(f"  - Terminal tasks: {len(task_graph.get_tasks_by_priority('terminal'))}")

            # Save results
            tasks_file = output_dir / "tasks.json"
            with open(tasks_file, 'w', encoding='utf-8') as f:
                json.dump(task_graph.to_dict(), f, indent=2, ensure_ascii=False)

            # Save summary
            summary_file = output_dir / "tasks_summary.txt"
            with open(summary_file, 'w', encoding='utf-8') as f:
                f.write("=" * 80 + "\n")
                f.write("TASK SYNTHESIS SUMMARY (Deterministic)\n")
                f.write("=" * 80 + "\n\n")
                f.write(f"Total tasks: {len(task_graph.tasks)}\n")
                f.write(f"Total screens: {task_graph.meta.get('total_screens', 0)}\n")
                f.write(f"Total actions: {task_graph.meta.get('total_actions', 0)}\n\n")

                from exploration import TaskPriority
                for priority in [TaskPriority.INITIAL, TaskPriority.INTERMEDIATE, TaskPriority.TERMINAL]:
                    priority_tasks = task_graph.get_tasks_by_priority(priority)
                    if priority_tasks:
                        f.write(f"\n{priority.value.upper()} TASKS ({len(priority_tasks)}):\n")
                        f.write("-" * 80 + "\n")
                        for task in priority_tasks:
                            f.write(f"\n  Task: {task.name}\n")
                            f.write(f"  Description: {task.description}\n")
                            f.write(f"  Actions: {len(task.related_actions)}\n")
                            f.write(f"  Screens: {len(task.entry_screens)}\n")

            logger.info("=" * 60)
            logger.info("Task Synthesis Complete!")
            logger.info("=" * 60)
            logger.info(f"Results saved to: {output_dir}")
            logger.info(f"  - tasks.json: Complete task graph")
            logger.info(f"  - tasks_summary.txt: Human-readable summary")
            logger.info("=" * 60)

        return True

    except Exception as e:
        logger.error(f"Task synthesis failed: {e}", exc_info=True)
        return False


async def run_exploration_cli(args):
    """
    Run exploration from command line.
    """
    # Setup logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    logger = logging.getLogger(__name__)

    logger.info("=" * 60)
    logger.info("Web Exploration Pipeline")
    logger.info("=" * 60)
    logger.info(f"Target URL: {args.url}")
    logger.info(f"Adapter: {args.adapter}")
    logger.info(f"Max screens: {args.max_screens}")
    logger.info(f"Headless: {args.headless}")
    logger.info("=" * 60)

    # Create environment
    logger.info("Initializing web environment...")
    env = GenericWebEnv(
        start_url=args.url,
        headless=args.headless,
        max_steps=args.max_steps
    )

    try:
        # Get exploration adapter
        logger.info(f"Loading exploration adapter: {args.adapter}")
        adapter = get_exploration_adapter(args.adapter)

        # Create unique folder name from URL (e.g., localhost_9999)
        folder_name = url_to_folder_name(args.url)
        logger.info(f"Storage folder: data/raw/{folder_name}")

        # Create storage with URL-based folder name
        storage = ExplorationStorage(folder_name, auto_clean=False)

        # Run exploration
        logger.info("Starting exploration...")
        result = await explore_website(
            env=env,
            explorer_adapter=adapter,
            start_url=args.url,
            max_screens=args.max_screens,
            max_transitions=args.max_transitions,
            max_actions_per_screen=args.max_actions_per_screen,
            storage=storage
        )

        logger.info("\n" + "=" * 60)
        logger.info("Exploration Complete!")
        logger.info("=" * 60)
        logger.info(f"Unique screens discovered: {result.get_unique_screen_count()}")
        logger.info(f"Transitions recorded: {result.get_transition_count()}")
        logger.info(f"Start URL: {result.start_url}")
        logger.info(f"Timestamp: {result.timestamp}")
        logger.info("=" * 60)

        # Results are automatically saved by storage module
        logger.info(f"Results saved to: data/raw/{folder_name}/")

        # Automatically run task synthesis (Phase 2) unless disabled
        if not args.skip_task_synthesis:
            logger.info("\nAutomatically proceeding to Task Synthesis (Phase 2)...")
            task_synthesis_success = run_task_synthesis(
                explorer_name=folder_name,
                use_llm=args.use_llm_synthesis,
                llm_provider=args.llm_provider
            )
            if not task_synthesis_success:
                logger.warning("Task synthesis failed, but exploration completed successfully")
        else:
            logger.info("\nTask synthesis skipped (use without --skip-task-synthesis to enable)")

        return 0

    except KeyboardInterrupt:
        logger.warning("\nExploration interrupted by user")
        return 1

    except Exception as e:
        logger.error(f"\nExploration failed: {e}", exc_info=True)
        return 1

    finally:
        # Cleanup
        logger.info("Closing environment...")
        try:
            await env.close()
        except Exception as e:
            logger.error(f"Error closing environment: {e}")


def main():
    parser = argparse.ArgumentParser(
        description="Run exploration on a website",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic exploration with deterministic task synthesis (OLD method)
  python run_exploration.py --url https://example.com

  # NEW: LLM-based task synthesis (aligned with professor's feedback)
  python run_exploration.py --url https://example.com --use-llm-synthesis

  # Use OpenAI instead of Anthropic for LLM synthesis
  python run_exploration.py --url https://example.com --use-llm-synthesis --llm-provider openai

  # Use AgentTrek adapter
  python run_exploration.py --url https://shop.com --adapter agenttrek

  # Extensive exploration
  python run_exploration.py --url https://docs.site.com --max-screens 200

  # Non-headless for debugging
  python run_exploration.py --url https://example.com --no-headless --verbose

  # Skip task synthesis (only run Phase 1 exploration)
  python run_exploration.py --url https://example.com --skip-task-synthesis

Adapters:
  simple     - Simple exploration adapter (default)
  agenttrek  - AgentTrek-style LLM exploration
  webtactix  - WebTactiX exploration adapter

Task Synthesis Methods:
  Deterministic (OLD): Pattern-based algorithmic approach (default)
  LLM-based (NEW):     LLM reads paths and generates tasks (--use-llm-synthesis)
                       Aligned with Professor Vũ's feedback
"""
    )

    parser.add_argument(
        "--url",
        required=True,
        help="Target URL to explore"
    )

    parser.add_argument(
        "--adapter",
        default=None,
        choices=["simple", "agenttrek", "webtactix"],
        help="Exploration adapter to use (default: from .env EXPLORER_PROVIDER or 'simple')"
    )

    parser.add_argument(
        "--max-screens",
        type=int,
        default=50,
        help="Maximum unique screens to discover (default: 50)"
    )

    parser.add_argument(
        "--max-transitions",
        type=int,
        default=200,
        help="Maximum transitions to record (default: 200)"
    )

    parser.add_argument(
        "--max-actions-per-screen",
        type=int,
        default=10,
        help="Maximum actions to try per screen (default: 10)"
    )

    parser.add_argument(
        "--max-steps",
        type=int,
        default=50,
        help="Maximum steps per episode (default: 50)"
    )

    parser.add_argument(
        "--headless",
        action="store_true",
        default=True,
        help="Run browser in headless mode (default: True)"
    )

    parser.add_argument(
        "--no-headless",
        action="store_false",
        dest="headless",
        help="Run browser in visible mode (for debugging)"
    )

    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose logging (DEBUG level)"
    )

    parser.add_argument(
        "--skip-task-synthesis",
        action="store_true",
        help="Skip automatic task synthesis after exploration (Phase 2)"
    )

    parser.add_argument(
        "--use-llm-synthesis",
        action="store_true",
        help="Use LLM-based task synthesis (NEW, aligned with professor's feedback). Default: deterministic"
    )

    parser.add_argument(
        "--llm-provider",
        default="anthropic",
        choices=["anthropic", "openai"],
        help="LLM provider for task synthesis (default: anthropic). Requires --use-llm-synthesis"
    )

    args = parser.parse_args()

    # Run exploration
    exit_code = asyncio.run(run_exploration_cli(args))
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
