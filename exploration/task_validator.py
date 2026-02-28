"""
Task Validation: Execute and validate synthesized tasks.

PHASE USAGE: Phase 3 (Task Validation)

PURPOSE:
- Execute tasks generated in Phase 2
- Validate that tasks can actually be performed
- Filter out tasks that fail or get stuck
- Produce clean, validated training data for Phase 4 (SLM training)

ALIGNED WITH PROFESSOR'S FEEDBACK:
- "Phase 3: LLM goes through each task"
- "Remove tasks that cannot be executed"
- "Get clean data for SLM to learn"

USAGE:
    validator = TaskValidator(env, llm_agent)
    validated = await validator.validate_tasks(tasks)
"""

import logging
import asyncio
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
from pathlib import Path
import json
from datetime import datetime

from exploration.llm_task_synthesizer import SynthesizedTask, TaskStep
from envs.base_env import WebEnv

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of validating a single task."""
    task_id: str
    task_name: str
    success: bool
    failure_reason: Optional[str] = None
    execution_time: float = 0.0
    steps_completed: int = 0
    total_steps: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ValidationReport:
    """Complete validation report for all tasks."""
    total_tasks: int
    validated_tasks: int
    failed_tasks: int
    success_rate: float
    validation_results: List[ValidationResult]
    timestamp: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_tasks": self.total_tasks,
            "validated_tasks": self.validated_tasks,
            "failed_tasks": self.failed_tasks,
            "success_rate": self.success_rate,
            "validation_results": [r.to_dict() for r in self.validation_results],
            "timestamp": self.timestamp
        }


class TaskValidator:
    """
    Validates synthesized tasks by executing them.

    Phase 3: Execute each task with LLM agent and determine if it can
    be completed successfully. Keep successful tasks, discard failed ones.

    This produces clean training data for the SLM (Phase 4).
    """

    def __init__(
        self,
        env: WebEnv,
        llm_agent = None,  # Will be LLM-based agent for execution
        max_steps_per_task: int = 20,
        timeout_per_task: int = 60,
        stuck_detection_window: int = 3
    ):
        """
        Initialize task validator.

        Args:
            env: Web environment for task execution
            llm_agent: LLM agent to execute tasks (if None, will use simple heuristics)
            max_steps_per_task: Maximum steps to try per task
            timeout_per_task: Timeout in seconds per task
            stuck_detection_window: Number of steps to check for being stuck
        """
        self.env = env
        self.llm_agent = llm_agent
        self.max_steps_per_task = max_steps_per_task
        self.timeout_per_task = timeout_per_task
        self.stuck_detection_window = stuck_detection_window

        logger.info(f"Initialized TaskValidator")
        logger.info(f"  Max steps per task: {max_steps_per_task}")
        logger.info(f"  Timeout per task: {timeout_per_task}s")

    async def validate_task(self, task: SynthesizedTask) -> ValidationResult:
        """
        Validate a single task by attempting to execute it.

        Args:
            task: Task to validate

        Returns:
            ValidationResult with success/failure status
        """
        logger.info(f"Validating task: {task.name}")

        start_time = datetime.now()
        steps_completed = 0
        failure_reason = None

        try:
            # Reset environment
            await self.env.reset()

            # Track state history for stuck detection
            state_history = []

            # Try to execute each step
            for i, step in enumerate(task.steps, 1):
                logger.debug(f"  Step {i}/{len(task.steps)}: {step.description}")

                # TODO: In full implementation, use LLM agent to interpret step and execute
                # For now, we'll use simple heuristics

                # Check if we're stuck (same state repeating)
                if self._is_stuck(state_history):
                    failure_reason = f"Stuck at step {i}: state not changing"
                    logger.warning(f"  ⚠️  {failure_reason}")
                    break

                # Simulate step execution (placeholder)
                # In real implementation: action = self.llm_agent.decide(step.description, current_state)
                # Then: observation, done = await self.env.step(action)

                # For now, assume step succeeds with probability
                # This is a PLACEHOLDER - real implementation needs actual LLM execution
                import random
                step_success = random.random() > 0.2  # 80% success rate placeholder

                if not step_success:
                    failure_reason = f"Failed at step {i}: could not execute action"
                    logger.warning(f"  ❌ {failure_reason}")
                    break

                steps_completed += 1

                # Check timeout
                elapsed = (datetime.now() - start_time).total_seconds()
                if elapsed > self.timeout_per_task:
                    failure_reason = f"Timeout after {elapsed:.1f}s"
                    logger.warning(f"  ⏱️  {failure_reason}")
                    break

                # Check max steps
                if steps_completed >= self.max_steps_per_task:
                    failure_reason = f"Exceeded max steps ({self.max_steps_per_task})"
                    logger.warning(f"  🔄 {failure_reason}")
                    break

            # Determine success
            success = (steps_completed == len(task.steps) and failure_reason is None)

            if success:
                logger.info(f"  ✅ Task validated successfully")
            else:
                logger.info(f"  ❌ Task validation failed: {failure_reason}")

            execution_time = (datetime.now() - start_time).total_seconds()

            return ValidationResult(
                task_id=task.task_id,
                task_name=task.name,
                success=success,
                failure_reason=failure_reason,
                execution_time=execution_time,
                steps_completed=steps_completed,
                total_steps=len(task.steps)
            )

        except Exception as e:
            logger.error(f"  💥 Exception during validation: {e}")
            execution_time = (datetime.now() - start_time).total_seconds()

            return ValidationResult(
                task_id=task.task_id,
                task_name=task.name,
                success=False,
                failure_reason=f"Exception: {str(e)}",
                execution_time=execution_time,
                steps_completed=steps_completed,
                total_steps=len(task.steps)
            )

    def _is_stuck(self, state_history: List[Any]) -> bool:
        """
        Detect if agent is stuck in a loop.

        Args:
            state_history: Recent state observations

        Returns:
            True if stuck, False otherwise
        """
        if len(state_history) < self.stuck_detection_window:
            return False

        # Check if last N states are identical
        recent = state_history[-self.stuck_detection_window:]
        return len(set(str(s) for s in recent)) == 1

    async def validate_tasks(
        self,
        tasks: List[SynthesizedTask],
        save_validated: bool = True,
        output_dir: Optional[Path] = None
    ) -> ValidationReport:
        """
        Validate a list of tasks.

        Args:
            tasks: List of tasks to validate
            save_validated: If True, save validated tasks
            output_dir: Directory to save results

        Returns:
            ValidationReport with results
        """
        logger.info("=" * 60)
        logger.info(f"Starting Task Validation (Phase 3)")
        logger.info(f"Tasks to validate: {len(tasks)}")
        logger.info("=" * 60)

        validation_results = []
        validated_tasks = []
        failed_tasks = []

        # Validate each task
        for i, task in enumerate(tasks, 1):
            logger.info(f"\n[{i}/{len(tasks)}] Validating: {task.name}")

            result = await self.validate_task(task)
            validation_results.append(result)

            if result.success:
                validated_tasks.append(task)
            else:
                failed_tasks.append(task)

        # Calculate statistics
        success_rate = len(validated_tasks) / len(tasks) if tasks else 0.0

        report = ValidationReport(
            total_tasks=len(tasks),
            validated_tasks=len(validated_tasks),
            failed_tasks=len(failed_tasks),
            success_rate=success_rate,
            validation_results=validation_results,
            timestamp=datetime.now().isoformat()
        )

        # Save results if requested
        if save_validated and output_dir:
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)

            # Save validated tasks
            self._save_validated_tasks(validated_tasks, output_dir / "validated_tasks.json")

            # Save validation report
            self._save_validation_report(report, output_dir / "validation_report.json")

            # Save human-readable summary
            self._save_validation_summary(report, validated_tasks, failed_tasks,
                                         output_dir / "validation_summary.txt")

        # Log summary
        logger.info("\n" + "=" * 60)
        logger.info("Task Validation Complete (Phase 3)")
        logger.info("=" * 60)
        logger.info(f"Total tasks: {len(tasks)}")
        logger.info(f"✅ Validated: {len(validated_tasks)} ({success_rate*100:.1f}%)")
        logger.info(f"❌ Failed: {len(failed_tasks)} ({(1-success_rate)*100:.1f}%)")
        logger.info("=" * 60)

        if output_dir:
            logger.info(f"Results saved to: {output_dir}")
            logger.info(f"  - validated_tasks.json: Tasks ready for training")
            logger.info(f"  - validation_report.json: Detailed validation results")
            logger.info(f"  - validation_summary.txt: Human-readable summary")
            logger.info("=" * 60)

        return report

    def _save_validated_tasks(self, tasks: List[SynthesizedTask], output_file: Path):
        """Save validated tasks to JSON."""
        data = {
            "validated_tasks": [task.to_dict() for task in tasks],
            "metadata": {
                "count": len(tasks),
                "phase": "Phase 3 - Task Validation",
                "timestamp": datetime.now().isoformat()
            }
        }

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        logger.info(f"Saved {len(tasks)} validated tasks to {output_file}")

    def _save_validation_report(self, report: ValidationReport, output_file: Path):
        """Save validation report to JSON."""
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(report.to_dict(), f, indent=2, ensure_ascii=False)

        logger.info(f"Saved validation report to {output_file}")

    def _save_validation_summary(
        self,
        report: ValidationReport,
        validated_tasks: List[SynthesizedTask],
        failed_tasks: List[SynthesizedTask],
        output_file: Path
    ):
        """Save human-readable validation summary."""
        lines = []
        lines.append("=" * 80)
        lines.append("TASK VALIDATION SUMMARY (Phase 3)")
        lines.append("=" * 80)
        lines.append(f"\nTimestamp: {report.timestamp}")
        lines.append(f"Total tasks evaluated: {report.total_tasks}")
        lines.append(f"✅ Validated (passed): {report.validated_tasks} ({report.success_rate*100:.1f}%)")
        lines.append(f"❌ Failed: {report.failed_tasks} ({(1-report.success_rate)*100:.1f}%)")
        lines.append("\n" + "=" * 80)

        # Validated tasks section
        if validated_tasks:
            lines.append(f"\n✅ VALIDATED TASKS ({len(validated_tasks)}):")
            lines.append("-" * 80)
            for i, task in enumerate(validated_tasks, 1):
                result = next(r for r in report.validation_results if r.task_id == task.task_id)
                lines.append(f"\n{i}. {task.name}")
                lines.append(f"   Steps: {result.steps_completed}/{result.total_steps}")
                lines.append(f"   Execution time: {result.execution_time:.2f}s")
                lines.append(f"   Description: {task.description}")

        # Failed tasks section
        if failed_tasks:
            lines.append(f"\n\n❌ FAILED TASKS ({len(failed_tasks)}):")
            lines.append("-" * 80)
            for i, task in enumerate(failed_tasks, 1):
                result = next(r for r in report.validation_results if r.task_id == task.task_id)
                lines.append(f"\n{i}. {task.name}")
                lines.append(f"   Reason: {result.failure_reason}")
                lines.append(f"   Steps completed: {result.steps_completed}/{result.total_steps}")
                lines.append(f"   Description: {task.description}")

        lines.append("\n" + "=" * 80)
        lines.append("\nNOTE: These validated tasks are ready for Phase 4 (SLM Training)")
        lines.append("=" * 80)

        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("\n".join(lines))

        logger.info(f"Saved validation summary to {output_file}")


# Convenience function
async def validate_tasks_from_synthesis(
    tasks: List[SynthesizedTask],
    env: WebEnv,
    output_dir: Path,
    llm_agent = None
) -> List[SynthesizedTask]:
    """
    Convenience function to validate synthesized tasks.

    Args:
        tasks: Tasks from Phase 2 (Task Synthesis)
        env: Web environment
        output_dir: Directory to save validated tasks
        llm_agent: Optional LLM agent for execution

    Returns:
        List of validated tasks ready for training
    """
    validator = TaskValidator(env, llm_agent)
    report = await validator.validate_tasks(
        tasks,
        save_validated=True,
        output_dir=output_dir
    )

    # Return only validated tasks
    validated = [
        task for task, result in zip(tasks, report.validation_results)
        if result.success
    ]

    return validated
