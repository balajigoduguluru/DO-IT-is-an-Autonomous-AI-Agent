"""Task scheduler with topological ordering and adaptive scheduling.

The :class:`TaskScheduler` takes a validated :class:`ExecutionGraph`,
computes a topological execution order, queries the Tool Marketplace for
the best tool to assign to each task, and groups tasks into parallel
batches ready for the :class:`ParallelExecutor`.
"""

from __future__ import annotations

from typing import Any, Protocol

from src.core.constants import GraphStatus, StatePhase, TaskStatus
from src.core.exceptions import AgentError, ToolNotFoundError
from src.core.models import AgentState, ExecutionGraph, ToolRegistration
from src.engine.dependency_graph import DependencyGraphBuilder


# ===========================================================================
# Protocols
# ===========================================================================


class ToolMarketplace(Protocol):
    """Protocol for the Tool Marketplace component.

    The marketplace maintains a catalogue of registered tools, their
    success metrics, and alternative chains.  See
    ``src.marketplace.marketplace`` for the concrete implementation.
    """

    async def select_tool(
        self,
        task_id: str,
        metadata: dict[str, Any],
    ) -> ToolRegistration | None:
        """Return the best tool for *task_id* based on historical metrics,
        or ``None`` if no suitable tool exists."""
        ...

    async def find_alternatives(
        self,
        task_id: str,
        metadata: dict[str, Any],
    ) -> list[ToolRegistration]:
        """Return alternative tools ranked by expected success for a task
        whose primary tool has failed."""
        ...


# ===========================================================================
# Scheduler
# ===========================================================================


class TaskScheduler:
    """Schedules tasks based on the dependency graph.

    Integrates with the Tool Marketplace for optimal tool selection and
    with the Adaptive Router for model assignment.

    Parameters
    ----------
    tool_marketplace:
        The marketplace instance used to select tools for each task.
        Pass ``None`` to skip tool selection (tasks will execute without
        an assigned tool).
    """

    def __init__(self, tool_marketplace: ToolMarketplace | None = None) -> None:
        self.tool_marketplace = tool_marketplace
        self._builder = DependencyGraphBuilder()

    # ------------------------------------------------------------------
    # Scheduling
    # ------------------------------------------------------------------

    async def schedule(
        self,
        graph: ExecutionGraph,
        state: AgentState,
    ) -> list[list[str]]:
        """Compute a full execution schedule for the graph.

        Steps
        -----
        1. Compute parallel groups via topological ordering.
        2. For each task, query the Tool Marketplace for the best tool.
           When a tool is found the task's ``model_assigned`` field is
           set to the tool name so the executor can look it up.
        3. Set the graph status to ``EXECUTING``.

        Parameters
        ----------
        graph:
            The execution graph to schedule.
        state:
            The agent state (mutated in place for ledger entries).

        Returns
        -------
        list[list[str]]
            Groups of task IDs in topological order, where each inner
            list can be executed in parallel.
        """
        # -- 1. Compute topological order ------------------------------------
        groups = self._builder.compute_parallel_groups(graph)
        if not groups:
            state.ledger.append({
                "event": "schedule_empty",
                "message": "No tasks to schedule",
                "timestamp": __import__("datetime").datetime.now(
                    __import__("datetime").timezone.utc,
                ).isoformat(),
            })
            return groups

        # -- 2. Query Tool Marketplace for tool assignments ------------------
        if self.tool_marketplace is not None:
            for group in groups:
                for task_id in group:
                    node = graph.nodes.get(task_id)
                    if node is None:
                        continue
                    try:
                        best_tool = await self.tool_marketplace.select_tool(
                            task_id, node.input,
                        )
                    except Exception:
                        best_tool = None

                    if best_tool is not None:
                        node.model_assigned = best_tool.name

        # -- 3. Mark graph ready for execution -------------------------------
        graph.status = GraphStatus.EXECUTING
        state.ledger.append({
            "event": "schedule_complete",
            "group_count": len(groups),
            "task_count": len(graph.nodes),
            "timestamp": __import__("datetime").datetime.now(
                __import__("datetime").timezone.utc,
            ).isoformat(),
        })

        return groups

    # ------------------------------------------------------------------
    # Rescheduling after failure
    # ------------------------------------------------------------------

    async def reschedule_on_failure(
        self,
        failed_task_id: str,
        state: AgentState,
    ) -> list[list[str]]:
        """Recompute the schedule after a task failure.

        This is called during the replanning loop.  It:

        1. Queries the Tool Marketplace for alternative tools for the
           failed task (so the retry uses a different approach).
        2. Recomputes parallel groups from the (potentially mutated)
           graph.

        Parameters
        ----------
        failed_task_id:
            The task that failed and triggered replanning.
        state:
            The current agent state.

        Returns
        -------
        list[list[str]]
            The updated parallel groups.
        """
        graph = state.execution_graph

        # -- 1. Find alternative tools for the failed task -------------------
        if self.tool_marketplace is not None and failed_task_id in graph.nodes:
            node = graph.nodes[failed_task_id]
            try:
                alternatives = await self.tool_marketplace.find_alternatives(
                    failed_task_id, node.input,
                )
            except Exception:
                alternatives = []

            if alternatives:
                # Assign the best alternative tool.
                node.model_assigned = alternatives[0].name
                # Reset the task status so it can be retried.
                if node.status in (TaskStatus.FAILED, TaskStatus.REPLANNING):
                    node.status = TaskStatus.PENDING

        # -- 2. Recompute parallel groups ------------------------------------
        groups = self._builder.compute_parallel_groups(graph)

        state.ledger.append({
            "event": "reschedule_complete",
            "failed_task": failed_task_id,
            "group_count": len(groups),
            "timestamp": __import__("datetime").datetime.now(
                __import__("datetime").timezone.utc,
            ).isoformat(),
        })

        return groups
