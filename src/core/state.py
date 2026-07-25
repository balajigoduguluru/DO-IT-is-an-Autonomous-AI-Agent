"""State management helpers for the Agentic AI framework.

All mutation functions follow an **immutable** pattern — they return a *new*
:class:`AgentState` instance so the state history can be tracked and replayed
if needed.
"""

from __future__ import annotations

import copy
from typing import Any

from src.core.constants import GraphStatus, StatePhase, TaskStatus
from src.core.models import (
    AgentState,
    ExecutionError,
    ExecutionGraph,
    LedgerEntry,
    TaskNode,
)


# ===========================================================================
# Factory
# ===========================================================================


def create_initial_state(
    user_goal: str,
    constraints: dict[str, Any] | None = None,
) -> AgentState:
    """Create a fresh :class:`AgentState` for a new session.

    Parameters
    ----------
    user_goal:
        The user's stated objective for this session.
    constraints:
        Optional mapping of constraint names to values (budget limits,
        date ranges, location restrictions, etc.).
    """
    return AgentState(
        user_goal=user_goal,
        constraints=constraints or {},
        execution_graph=ExecutionGraph(status=GraphStatus.BUILDING),
        current_phase=StatePhase.UNDERSTAND_GOAL,
    )


# ===========================================================================
# Query helpers (read-only)
# ===========================================================================


def get_ready_tasks(state: AgentState) -> list[TaskNode]:
    """Return all tasks whose dependencies are satisfied and are ``PENDING``."""
    return state.execution_graph.get_ready_nodes()


def get_task_by_id(state: AgentState, task_id: str) -> TaskNode | None:
    """Look up a task by its ID, returning ``None`` if not found."""
    return state.execution_graph.nodes.get(task_id)


def get_tasks_by_status(
    state: AgentState, status: TaskStatus
) -> list[TaskNode]:
    """Return all tasks with a given status."""
    return [
        n for n in state.execution_graph.nodes.values() if n.status == status
    ]


def is_graph_complete(state: AgentState) -> bool:
    """Check whether every task in the graph has reached a terminal status."""
    statuses = {n.status for n in state.execution_graph.nodes.values()}
    terminal = {TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.SKIPPED}
    return statuses.issubset(terminal)


# ===========================================================================
# Mutation helpers (immutable — return new state)
# ===========================================================================


def _deep_copy(obj: Any) -> Any:
    """Deep-copy an object while preserving its type."""
    return copy.deepcopy(obj)


def update_phase(state: AgentState, phase: StatePhase) -> AgentState:
    """Transition to a new phase, returning an updated state."""
    new = _deep_copy(state)
    new.current_phase = phase
    return new


def update_graph_status(state: AgentState, status: GraphStatus) -> AgentState:
    """Update the execution graph's status, returning an updated state."""
    new = _deep_copy(state)
    new.execution_graph.status = status
    return new


def add_task(state: AgentState, task: TaskNode) -> AgentState:
    """Add a new task node to the execution graph."""
    new = _deep_copy(state)
    new.execution_graph.add_node(task)
    return new


def add_edge(state: AgentState, from_id: str, to_id: str) -> AgentState:
    """Add a directed dependency edge between two tasks."""
    new = _deep_copy(state)
    new.execution_graph.add_edge(from_id, to_id)
    return new


def mark_task_running(state: AgentState, task_id: str) -> AgentState:
    """Transition a task from ``PENDING`` to ``RUNNING``."""
    new = _deep_copy(state)
    node = new.execution_graph.nodes.get(task_id)
    if node is None:
        raise KeyError(f"Task {task_id!r} not found in graph")
    if node.status != TaskStatus.PENDING:
        raise ValueError(
            f"Cannot mark task {task_id!r} as RUNNING: "
            f"current status is {node.status}"
        )
    node.status = TaskStatus.RUNNING
    return new


def mark_task_completed(
    state: AgentState,
    task_id: str,
    output: dict[str, Any] | None = None,
) -> AgentState:
    """Mark a task as completed with the given output."""
    new = _deep_copy(state)
    node = new.execution_graph.nodes.get(task_id)
    if node is None:
        raise KeyError(f"Task {task_id!r} not found in graph")
    node.status = TaskStatus.COMPLETED
    node.output = output or {}
    from datetime import datetime, timezone

    node.completed_at = datetime.now(timezone.utc)
    return new


def mark_task_failed(
    state: AgentState,
    task_id: str,
    error: str | ExecutionError,
) -> AgentState:
    """Mark a task as failed, recording the error."""
    new = _deep_copy(state)
    node = new.execution_graph.nodes.get(task_id)
    if node is None:
        raise KeyError(f"Task {task_id!r} not found in graph")
    node.status = TaskStatus.FAILED
    from datetime import datetime, timezone

    node.completed_at = datetime.now(timezone.utc)

    if isinstance(error, ExecutionError):
        exc = error
    else:
        exc = ExecutionError(
            task_id=task_id,
            error_type="TaskExecutionError",
            message=str(error),
            details={},
        )
    new.errors.append(exc)
    return new


def mark_task_skipped(state: AgentState, task_id: str) -> AgentState:
    """Mark a dependant task as skipped (e.g. after an upstream failure)."""
    new = _deep_copy(state)
    node = new.execution_graph.nodes.get(task_id)
    if node is None:
        raise KeyError(f"Task {task_id!r} not found in graph")
    node.status = TaskStatus.SKIPPED
    return new


def add_ledger_entry(state: AgentState, entry: LedgerEntry) -> AgentState:
    """Append an audit-log entry to the ledger."""
    new = _deep_copy(state)
    new.ledger.append(entry)
    return new


def add_error(state: AgentState, error: ExecutionError) -> AgentState:
    """Record an execution error."""
    new = _deep_copy(state)
    new.errors.append(error)
    return new


def add_approval_request(
    state: AgentState,
    request: "ApprovalRequest",  # noqa: F821 — forward-ref handled at runtime below
) -> AgentState:
    """Append an approval request to the queue."""
    from src.core.models import ApprovalRequest

    new = _deep_copy(state)
    if not isinstance(request, ApprovalRequest):
        raise TypeError("Expected an ApprovalRequest instance")
    new.approval_queue.append(request)
    return new


def set_final_summary(state: AgentState, summary: str) -> AgentState:
    """Store the final summary produced by the agent."""
    new = _deep_copy(state)
    new.final_summary = summary
    return new


def cascade_skip(state: AgentState, failed_task_id: str) -> AgentState:
    """Mark all transitive dependents of *failed_task_id* as skipped.

    This is a convenience helper for when an upstream failure should abort
    downstream work rather than attempt recovery.
    """
    new = _deep_copy(state)
    graph = new.execution_graph

    # Build an adjacency list for faster traversal.
    dependents: dict[str, list[str]] = {}
    for from_id, to_id in graph.edges:
        dependents.setdefault(from_id, []).append(to_id)

    visited: set[str] = set()
    stack = [failed_task_id]
    while stack:
        node_id = stack.pop()
        if node_id in visited:
            continue
        visited.add(node_id)

        if node_id != failed_task_id:
            node = graph.nodes.get(node_id)
            if node is not None and node.status == TaskStatus.PENDING:
                node.status = TaskStatus.SKIPPED

        # Only follow edges that originate from the current node.
        for to_id in dependents.get(node_id, []):
            stack.append(to_id)

    return new


def transition_graph_on_completion(state: AgentState) -> AgentState:
    """Automatically transition graph status when appropriate.

    - If all tasks are terminal -> ``COMPLETED`` (or ``FAILED`` if any failed).
    - Otherwise stays ``EXECUTING``.
    """
    new = _deep_copy(state)
    graph = new.execution_graph

    if not graph.nodes:
        return new

    all_terminal = all(
        n.status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.SKIPPED)
        for n in graph.nodes.values()
    )
    if not all_terminal:
        return new

    any_failed = any(n.status == TaskStatus.FAILED for n in graph.nodes.values())
    if any_failed:
        graph.status = GraphStatus.FAILED
    else:
        graph.status = GraphStatus.COMPLETED
        if new.current_phase not in (StatePhase.END,):
            new.current_phase = StatePhase.EVALUATE

    return new
