"""Parallel execution engine — Innovation #3.

Executes independent tasks concurrently using ``asyncio.gather`` with a
configurable concurrency semaphore.  Instead of running Flight → Hotel →
Weather sequentially, we run them in parallel when the dependency graph
allows it.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any, Protocol

from src.core.constants import GraphStatus, RiskLevel, StatePhase, TaskStatus
from src.core.models import (
    AgentState,
    ExecutionError,
    RiskAssessment,
    ToolRegistration,
)
from src.engine.dependency_graph import (
    DependencyGraphBuilder,
    compute_topological_levels,
)


# ===========================================================================
# Local data types
# ===========================================================================


class ExecutionResult:
    """Result of executing a single task.

    This is produced by the ``WorkerAgent`` and consumed by the
    :class:`ParallelExecutor`.  It is defined here rather than in
    ``src.core.models`` because it is an engine-level concern.
    """

    def __init__(
        self,
        task_id: str,
        success: bool,
        data: dict | None = None,
        error: str | None = None,
        duration_ms: float = 0.0,
        tool_used: str | None = None,
    ) -> None:
        self.task_id = task_id
        self.success = success
        self.data = data or {}
        self.error = error
        self.duration_ms = duration_ms
        self.tool_used = tool_used


# ===========================================================================
# Protocols for pluggable collaborators
# ===========================================================================


class WorkerAgent(Protocol):
    """Protocol for the agent that executes a single task."""

    async def execute(
        self,
        task_id: str,
        state: AgentState,
        tool_registry: ToolLookup,  # noqa: F821 — forward ref
    ) -> ExecutionResult:
        ...


class RiskPredictor(Protocol):
    """Protocol for the component that assesses task risk."""

    async def assess(
        self, task_id: str, state: AgentState,
    ) -> RiskAssessment:
        ...


class ToolLookup(Protocol):
    """Minimal tool lookup used during execution."""

    async def get_tool(self, name: str) -> ToolRegistration | None:
        ...

    async def list_tools(
        self, category: str | None = None,
    ) -> list[ToolRegistration]:
        ...


# ===========================================================================
# Parallel Executor
# ===========================================================================


class ParallelExecutor:
    """Executes groups of independent tasks concurrently.

    Parameters
    ----------
    worker_agent:
        Callable that runs a single task.
    risk_predictor:
        Optional component that assesses risk before execution.
        Pass ``None`` to skip risk assessment.
    tool_registry:
        Optional registry for looking up tool metadata during execution.
    max_parallel:
        Maximum number of tasks to run simultaneously within a single
        parallel group (back-pressure via ``asyncio.Semaphore``).
    """

    def __init__(
        self,
        worker_agent: WorkerAgent,
        risk_predictor: RiskPredictor | None = None,
        tool_registry: ToolLookup | None = None,
        max_parallel: int = 5,
    ) -> None:
        self.worker = worker_agent
        self.risk_predictor = risk_predictor
        self.tool_registry = tool_registry
        self.max_parallel = max_parallel

    # ------------------------------------------------------------------
    # Single-group execution
    # ------------------------------------------------------------------

    async def execute_group(
        self,
        task_ids: list[str],
        state: AgentState,
    ) -> list[tuple[str, dict[str, Any]]]:
        """Execute a group of independent tasks in parallel.

        Each task goes through:

        1. **Risk assessment** (if a ``RiskPredictor`` is configured).
        2. **Execution** via the ``WorkerAgent``.
        3. **Result collection** — the task's ``TaskNode`` status is updated
           in place on the graph, and results are written to ``state.results``.

        Parameters
        ----------
        task_ids:
            The tasks to execute (must be independent — no edges between them).
        state:
            The current agent state (mutated in place for audit entries
            and task-status updates).

        Returns
        -------
        list[tuple[str, dict]]
            ``[(task_id, {"success": bool, "data": ..., "error": ...}), ...]``
        """
        semaphore = asyncio.Semaphore(self.max_parallel)
        ledger = state.ledger  # mutable list on the Pydantic model

        async def _run_one(task_id: str) -> tuple[str, dict[str, Any]]:
            async with semaphore:
                node = state.execution_graph.nodes.get(task_id)
                if node is None:
                    return (
                        task_id,
                        {
                            "success": False,
                            "error": f"Task {task_id!r} not found in graph",
                        },
                    )

                # ---- 1. Risk assessment ----
                if self.risk_predictor is not None:
                    try:
                        assessment = await self.risk_predictor.assess(
                            task_id, state,
                        )
                        node.risk_assessment = assessment
                        if assessment.risk_level in (
                            RiskLevel.HIGH,
                            RiskLevel.CRITICAL,
                        ):
                            ledger.append(
                                {
                                    "event": "risk_assessment",
                                    "task_id": task_id,
                                    "level": assessment.risk_level.value,
                                    "factors": assessment.security_flags,
                                    "timestamp": datetime.now(
                                        timezone.utc,
                                    ).isoformat(),
                                }
                            )
                    except Exception as exc:
                        # Non-fatal — log and continue.
                        ledger.append(
                            {
                                "event": "risk_assessment_error",
                                "task_id": task_id,
                                "error": str(exc),
                                "timestamp": datetime.now(
                                    timezone.utc,
                                ).isoformat(),
                            }
                        )

                # ---- 2. Execute ----
                node.status = TaskStatus.RUNNING
                try:
                    result: ExecutionResult = await self.worker.execute(
                        task_id, state, self.tool_registry,
                    )
                except Exception as exc:
                    node.status = TaskStatus.FAILED
                    node.completed_at = datetime.now(timezone.utc)
                    error_msg = str(exc)
                    state.errors.append(
                        ExecutionError(
                            task_id=task_id,
                            error_type="UnexpectedError",
                            message=error_msg,
                            details={"exception_type": type(exc).__name__},
                        )
                    )
                    ledger.append(
                        {
                            "event": "task_failed",
                            "task_id": task_id,
                            "error": error_msg,
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                        }
                    )
                    return (task_id, {"success": False, "error": error_msg})

                # ---- 3. Collect result ----
                if result.success:
                    node.status = TaskStatus.COMPLETED
                    node.output = result.data
                else:
                    node.status = TaskStatus.FAILED
                    node.output = result.data
                    error_msg = result.error or "Unknown error"
                    state.errors.append(
                        ExecutionError(
                            task_id=task_id,
                            error_type="TaskExecutionError",
                            message=error_msg,
                            details={
                                "tool_used": result.tool_used,
                            },
                        )
                    )

                node.completed_at = datetime.now(timezone.utc)

                ledger.append(
                    {
                        "event": "task_completed" if result.success else "task_failed",
                        "task_id": task_id,
                        "success": result.success,
                        "duration_ms": result.duration_ms,
                        "tool_used": result.tool_used,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }
                )

                return (
                    task_id,
                    {
                        "success": result.success,
                        "data": result.data,
                        "error": result.error,
                    },
                )

        tasks = [_run_one(tid) for tid in task_ids]
        return await asyncio.gather(*tasks)

    # ------------------------------------------------------------------
    # Full-graph execution
    # ------------------------------------------------------------------

    async def execute_full_graph(
        self, state: AgentState,
    ) -> AgentState:
        """Execute the entire graph by iterating through parallel groups.

        Flow
        ----
        1. Compute parallel groups from the graph's topological levels
           (if not already computed).
        2. For each group:
           a. Execute all tasks in the group concurrently.
           b. If **any** task in the group fails, set
              ``memory_context["_needs_replan"] = True`` and return early.
        3. If all groups complete without failure, mark the graph as
           ``COMPLETED``.

        Parameters
        ----------
        state:
            Agent state whose ``execution_graph`` will be executed.
            Modified in place.

        Returns
        -------
        AgentState
            The updated state (same object).
        """
        graph = state.execution_graph
        if not graph.nodes:
            return state

        # -- Compute parallel groups if missing ------------------------------
        levels = graph.metadata.get("topological_levels", {})
        if not levels:
            graph.metadata["topological_levels"] = compute_topological_levels(
                graph,
            )

        groups = DependencyGraphBuilder().compute_parallel_groups(graph)
        if not groups:
            return state

        state.current_phase = StatePhase.EXECUTE
        graph.status = GraphStatus.EXECUTING

        # Track which task IDs are already completed (survives replan loops).
        completed_ids: set[str] = {
            tid
            for tid, n in graph.nodes.items()
            if n.status == TaskStatus.COMPLETED
        }

        for group_idx, task_group in enumerate(groups):
            # Skip groups whose tasks are all already done.
            pending = [t for t in task_group if t not in completed_ids]
            if not pending:
                continue

            state.ledger.append(
                {
                    "event": "group_start",
                    "group_index": group_idx,
                    "tasks": pending,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            )

            results = await self.execute_group(pending, state)

            # Mark successfully completed tasks for future-group skipping.
            for tid, result in results:
                if result.get("success", False):
                    completed_ids.add(tid)

            # If any task in this group failed — trigger replanning.
            failures = [
                (tid, r)
                for tid, r in results
                if not r.get("success", False)
            ]
            if failures:
                state.memory_context["_needs_replan"] = True
                state.needs_replan = True
                graph.status = GraphStatus.FAILED
                state.ledger.append(
                    {
                        "event": "group_failed",
                        "group_index": group_idx,
                        "failures": [
                            {"task_id": tid, "error": r.get("error")}
                            for tid, r in failures
                        ],
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }
                )
                return state

            state.ledger.append(
                {
                    "event": "group_complete",
                    "group_index": group_idx,
                    "tasks": pending,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            )

        # All groups completed successfully.
        graph.status = GraphStatus.COMPLETED
        state.memory_context["_needs_replan"] = False
        state.needs_replan = False
        return state
