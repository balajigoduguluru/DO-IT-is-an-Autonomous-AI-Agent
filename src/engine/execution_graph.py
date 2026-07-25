"""Adaptive execution graph — Innovation #1.

The :class:`AdaptiveExecutionGraph` wraps a standard :class:`ExecutionGraph`
and allows it to *mutate at runtime*.  When a task fails and the replanner
suggests alternative tasks, the adaptive graph can:

* remove the failed subgraph (failed task + all transitive dependents),
* insert new replacement tasks,
* reconnect their dependencies,
* recompute topological levels, and
* continue execution without restarting the entire plan.
"""

from __future__ import annotations

from typing import Any

from src.core.constants import GraphStatus, RiskLevel, TaskStatus
from src.core.exceptions import AgentError
from src.core.models import ExecutionGraph, RiskAssessment, TaskNode
from src.engine.dependency_graph import compute_topological_levels


class NoTasksToReplaceError(AgentError):
    """Raised when ``mutate_on_failure`` is called with an empty replacement
    task dict but the failed task still has dependents that need resolution."""


# ===========================================================================
# Adaptive Graph
# ===========================================================================


class AdaptiveExecutionGraph:
    """An execution graph that can be mutated while the engine is running.

    Wraps an :class:`ExecutionGraph` instance and provides safe mutation
    operations for the replanning loop.

    Parameters
    ----------
    graph:
        The initial execution graph to wrap.
    """

    def __init__(self, graph: ExecutionGraph) -> None:
        self.graph: ExecutionGraph = graph

    # ------------------------------------------------------------------
    # Mutation on failure
    # ------------------------------------------------------------------

    def mutate_on_failure(
        self,
        failed_task_id: str,
        new_tasks: dict[str, dict],
    ) -> ExecutionGraph:
        """Remove a failed subgraph and insert replacement tasks.

        Steps
        -----
        1. Compute the affected subgraph (failed task + all transitive
           dependents).
        2. Remove every node in the affected subgraph from *self.graph*.
        3. Insert the new tasks into the graph.
        4. Rebuild dependency edges for the new region.
        5. Recompute topological levels for the whole graph.
        6. Mark the graph status as ``READY``.

        Parameters
        ----------
        failed_task_id:
            The ID of the task that triggered the replan.
        new_tasks:
            A ``dict[str, dict]`` in the same format accepted by
            :meth:`DependencyGraphBuilder.build`.  Each entry becomes a
            new :class:`TaskNode`.

        Returns
        -------
        ExecutionGraph
            The (mutated) internal graph — same object as ``self.graph``.
        """
        # -- 1. Affected subgraph --------------------------------------------
        affected = self.get_affected_subgraph(failed_task_id)

        # -- 2. Remove affected nodes ----------------------------------------
        for tid in affected:
            self.graph.nodes.pop(tid, None)
            self.graph.edges = [
                e for e in self.graph.edges if e[0] != tid and e[1] != tid
            ]

        # -- 3. Insert new tasks ---------------------------------------------
        for task_id, data in new_tasks.items():
            if task_id in self.graph.nodes:
                continue  # avoid accidentally overwriting existing nodes

            node = TaskNode(
                id=task_id,
                agent_type=data.get("agent_type", "worker"),
                status=TaskStatus.PENDING,
                dependencies=list(data.get("dependencies", [])),
                input=data.get("input", {}),
                risk_assessment=self._build_risk_assessment(data),
                model_assigned=data.get("model_assigned"),
            )
            self.graph.add_node(node)

        # -- 4. Rebuild dependency edges for new tasks -----------------------
        for task_id, data in new_tasks.items():
            if task_id not in self.graph.nodes:
                continue
            for dep in data.get("dependencies", []):
                if dep in self.graph.nodes:
                    try:
                        self.graph.add_edge(dep, task_id)
                    except KeyError:
                        continue  # shouldn't happen after the guard above

        # -- 5. Recompute topological levels ---------------------------------
        self.graph.metadata["topological_levels"] = compute_topological_levels(
            self.graph,
        )
        self.graph.status = GraphStatus.READY

        return self.graph

    # ------------------------------------------------------------------
    # Affected-subgraph computation
    # ------------------------------------------------------------------

    def get_affected_subgraph(self, task_id: str) -> list[str]:
        """Return all task IDs that are transitively downstream of *task_id*.

        This is a BFS over outgoing edges (dependents).  The result
        *includes* ``task_id`` itself so callers can pass it directly to
        :meth:`remove_node`.
        """
        affected: set[str] = set()
        queue = [task_id]

        while queue:
            current = queue.pop(0)
            if current in affected:
                continue
            affected.add(current)
            queue.extend(self.graph.get_dependents(current))

        return list(affected)

    # ------------------------------------------------------------------
    # Serialisation (for the UI / monitoring)
    # ------------------------------------------------------------------

    def visualize(self) -> dict[str, Any]:
        """Return a serializable representation of the current graph.

        The result is suitable for JSON serialisation and can be consumed
        by a front-end or logging system.
        """
        return {
            "status": self.graph.status.value,
            "nodes": [
                {
                    "id": nid,
                    "agent_type": node.agent_type,
                    "status": node.status.value,
                    "level": self.graph.metadata.get("topological_levels", {}).get(nid, -1),
                    "dependencies": node.dependencies,
                    "model_assigned": node.model_assigned,
                }
                for nid, node in self.graph.nodes.items()
            ],
            "edges": [
                {"from": edge[0], "to": edge[1]}
                for edge in self.graph.edges
            ],
            "node_count": len(self.graph.nodes),
            "edge_count": len(self.graph.edges),
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _build_risk_assessment(
        data: dict[str, Any],
    ) -> RiskAssessment | None:
        rl = data.get("risk_level")
        if rl is not None:
            return RiskAssessment(risk_level=rl)
        return None
