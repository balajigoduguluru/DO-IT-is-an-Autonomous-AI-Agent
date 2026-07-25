"""Build a task-dependency DAG from a flat planner output.

The :class:`DependencyGraphBuilder` takes a dictionary of task definitions,
validates that all cross-references resolve, detects cycles via Kahn's
algorithm, assigns topological levels, and returns a ready-to-execute
:class:`ExecutionGraph`.
"""

from __future__ import annotations

from typing import Any

from src.core.constants import GraphStatus, RiskLevel, TaskStatus
from src.core.exceptions import AgentError, GraphCycleError
from src.core.models import ExecutionGraph, RiskAssessment, TaskNode


# ===========================================================================
# Custom exceptions for the builder
# ===========================================================================


class InvalidDependencyError(AgentError):
    """Raised when a task references a dependency that does not exist in the
    task collection passed to :meth:`DependencyGraphBuilder.build`."""

    def __init__(self, task_id: str, missing_dep: str) -> None:
        self.task_id = task_id
        self.missing_dep = missing_dep
        super().__init__(
            f"Task {task_id!r} references a dependency "
            f"({missing_dep!r}) that is not present in the task set"
        )


# ===========================================================================
# Builder
# ===========================================================================


# ===========================================================================
# Module-level helpers
# ===========================================================================


def compute_topological_levels(graph: ExecutionGraph) -> dict[str, int]:
    """Assign topological depth levels via memoised DFS.

    Level 0 = no dependencies (root nodes).
    Level N = max(level of all dependencies) + 1.

    This is a module-level function so it can be used by both
    :class:`DependencyGraphBuilder` and :class:`ParallelExecutor`.
    """
    levels: dict[str, int] = {}

    def _compute(tid: str) -> int:
        if tid in levels:
            return levels[tid]
        deps = graph.get_dependencies(tid)
        if not deps:
            levels[tid] = 0
            return 0
        levels[tid] = max(_compute(d) for d in deps) + 1
        return levels[tid]

    for tid in graph.nodes:
        _compute(tid)

    return levels


class DependencyGraphBuilder:
    """Constructs a validated, topologically-ordered :class:`ExecutionGraph`
    from a flat dictionary of task definitions.

    Input format
    ------------
    ``tasks`` is a ``dict[str, dict]`` where each key is a unique task ID and
    the value is a dictionary that may contain:

    .. code-block:: python

        {
            "agent_type": "worker",           # required
            "dependencies": ["task_a", ...],  # default []
            "description": "...",
            "input": {"key": "val"},          # default {}
            "risk_level": "LOW",              # default LOW
            "tool": "tool_name",
            "tool_category": "GENERAL",
            "metadata": {...},
        }

    The builder validates every dependency reference, checks for cycles,
    assigns topological depth levels, and returns an ``ExecutionGraph``
    whose ``status`` is ``GraphStatus.READY``.
    """

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def build(self, tasks: dict[str, dict]) -> ExecutionGraph:
        """Validate, detect cycles, build, and return an ``ExecutionGraph``.

        Parameters
        ----------
        tasks:
            Mapping of task ID → task definition (see class docstring).

        Returns
        -------
        ExecutionGraph
            A ready-to-execute graph with nodes, edges, and topological
            levels populated.

        Raises
        ------
        InvalidDependencyError
            If a task depends on a task ID that is not present in *tasks*.
        GraphCycleError
            If a cycle is detected in the dependency graph.
        """
        # -- 1. Validate all dependency references ---------------------------
        self._validate_dependencies(tasks)

        # -- 2. Detect cycles via Kahn's algorithm ---------------------------
        self._detect_cycles(tasks)

        # -- 3. Build graph --------------------------------------------------
        graph = ExecutionGraph(status=GraphStatus.BUILDING)

        for task_id, data in tasks.items():
            node = TaskNode(
                id=task_id,
                agent_type=data.get("agent_type", "worker"),
                status=TaskStatus.PENDING,
                dependencies=list(data.get("dependencies", [])),
                input=data.get("input", {}),
                risk_assessment=self._build_risk_assessment(data),
                model_assigned=data.get("model_assigned"),
            )
            graph.add_node(node)

        # -- 4. Add edges ----------------------------------------------------
        for task_id, data in tasks.items():
            for dep_id in data.get("dependencies", []):
                graph.add_edge(dep_id, task_id)

        # -- 5. Compute topological levels -----------------------------------
        graph.topological_levels = self._compute_topological_levels(
            graph,
        )
        graph.metadata["topological_levels"] = graph.topological_levels

        graph.status = GraphStatus.READY
        return graph

    def compute_parallel_groups(
        self, graph: ExecutionGraph,
    ) -> list[list[str]]:
        """Group task IDs by topological depth.

        Tasks at the same depth have no transitive dependency on each other
        and *may* be executed concurrently.

        Returns
        -------
        list[list[str]]
            ``[[level_0_tasks...], [level_1_tasks...], ...]``
        """
        levels: dict[str, int] = graph.topological_levels or graph.metadata.get("topological_levels", {})
        if not levels:
            # Fall back to on-the-fly computation for manually created graphs
            levels = compute_topological_levels(graph)
            if not levels:
                return []

        max_level = max(levels.values(), default=-1)
        if max_level < 0:
            return []

        groups: list[list[str]] = [[] for _ in range(max_level + 1)]
        for tid, level in levels.items():
            groups[level].append(tid)
        return groups

    def get_ready_tasks(
        self, graph: ExecutionGraph, completed_ids: set[str],
    ) -> list[str]:
        """Return task IDs whose dependencies are all satisfied.

        Only tasks that are still ``PENDING`` (or ``FAILED`` and therefore
        ready for a retry attempt) are considered.
        """
        ready: list[str] = []
        for tid, node in graph.nodes.items():
            if node.status not in (TaskStatus.PENDING, TaskStatus.FAILED):
                continue
            deps = graph.get_dependencies(tid)
            if all(d in completed_ids for d in deps):
                ready.append(tid)
        return ready

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _validate_dependencies(self, tasks: dict[str, dict]) -> None:
        """Ensure every dependency reference points to an existing task."""
        for task_id, data in tasks.items():
            for dep in data.get("dependencies", []):
                if dep not in tasks:
                    raise InvalidDependencyError(task_id, dep)

    def _detect_cycles(self, tasks: dict[str, dict]) -> None:
        """Kahn's algorithm for cycle detection.

        Raises :class:`GraphCycleError` if a cycle is found and includes
        the node IDs that remain in the cycle.
        """
        adj: dict[str, list[str]] = {tid: [] for tid in tasks}
        in_degree: dict[str, int] = {tid: 0 for tid in tasks}

        for tid, data in tasks.items():
            for dep in data.get("dependencies", []):
                if dep in tasks:  # already validated, but guard anyway
                    adj[dep].append(tid)
                    in_degree[tid] = in_degree.get(tid, 0) + 1

        queue = [tid for tid, deg in in_degree.items() if deg == 0]
        processed = 0

        while queue:
            current = queue.pop(0)
            processed += 1
            for dependent in adj[current]:
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    queue.append(dependent)

        if processed != len(tasks):
            cycle_nodes = [
                tid for tid, deg in in_degree.items() if deg > 0
            ]
            raise GraphCycleError(
                from_id=cycle_nodes[0] if cycle_nodes else "",
                to_id=cycle_nodes[-1] if cycle_nodes else "",
                details={
                    "cycle_nodes": cycle_nodes,
                    "processed": processed,
                    "total": len(tasks),
                },
            )

    def _compute_topological_levels(
        self, graph: ExecutionGraph,
    ) -> dict[str, int]:
        """Assign topological depth levels via memoised DFS.

        (Delegates to the module-level :func:`compute_topological_levels`.)
        """
        return compute_topological_levels(graph)

    @staticmethod
    def _build_risk_assessment(data: dict[str, Any]) -> RiskAssessment | None:
        """Construct a ``RiskAssessment`` from task data if risk info exists."""
        rl = data.get("risk_level")
        if rl is not None:
            return RiskAssessment(risk_level=rl)
        return None
