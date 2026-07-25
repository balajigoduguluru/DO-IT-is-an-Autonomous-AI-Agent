"""Tests for the dependency graph builder (Innovation #2).

Tests DAG building, topological ordering, cycle detection, and adaptive
mutation on failure.
"""

import sys
from pathlib import Path

import pytest

_HERE = Path(__file__).resolve().parent
_PROJECT_ROOT = _HERE.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from src.core.constants import GraphStatus, TaskStatus
from src.core.exceptions import GraphCycleError
from src.core.models import ExecutionGraph
from src.engine.dependency_graph import DependencyGraphBuilder, InvalidDependencyError
from src.engine.execution_graph import AdaptiveExecutionGraph


class TestDependencyGraph:
    """Test DAG building and topological ordering."""

    # ------------------------------------------------------------------
    # Fixtures
    # ------------------------------------------------------------------

    @pytest.fixture
    def builder(self) -> DependencyGraphBuilder:
        return DependencyGraphBuilder()

    @pytest.fixture
    def simple_tasks(self) -> dict[str, dict]:
        """A simple three-task set with one dependency chain."""
        return {
            "weather_check": {
                "agent_type": "worker",
                "dependencies": [],
                "input": {"action": "check_weather", "destination": "Bangalore"},
                "risk_level": "LOW",
            },
            "flight_search": {
                "agent_type": "worker",
                "dependencies": [],
                "input": {"action": "search_flight", "origin": "Mumbai"},
                "risk_level": "MEDIUM",
            },
            "budget_calc": {
                "agent_type": "worker",
                "dependencies": ["flight_search"],
                "input": {"action": "calculate_budget", "budget": 30000},
                "risk_level": "HIGH",
            },
        }

    # ------------------------------------------------------------------
    # Simple DAG
    # ------------------------------------------------------------------

    def test_simple_dag(self, builder: DependencyGraphBuilder, simple_tasks: dict) -> None:
        """Test building a simple dependency graph."""
        graph = builder.build(simple_tasks)

        # Graph should have correct node count
        assert len(graph.nodes) == 3
        assert graph.status == GraphStatus.READY

        # Edge count: budget_calc depends on flight_search
        assert len(graph.edges) == 1

        # Verify specific nodes exist
        for tid in ("weather_check", "flight_search", "budget_calc"):
            assert tid in graph.nodes
            assert graph.nodes[tid].status == TaskStatus.PENDING

        # Verify edges
        assert graph.edges == [["flight_search", "budget_calc"]]

        # Verify topological levels
        assert graph.topological_levels["weather_check"] == 0
        assert graph.topological_levels["flight_search"] == 0
        assert graph.topological_levels["budget_calc"] == 1

    # ------------------------------------------------------------------
    # Parallel groups
    # ------------------------------------------------------------------

    def test_parallel_groups(self, builder: DependencyGraphBuilder, simple_tasks: dict) -> None:
        """Test that independent tasks are grouped for parallel execution."""
        graph = builder.build(simple_tasks)
        groups = builder.compute_parallel_groups(graph)

        # Should have 2 groups: [weather, flight] at level 0, [budget] at level 1
        assert len(groups) == 2
        assert set(groups[0]) == {"weather_check", "flight_search"}
        assert groups[1] == ["budget_calc"]

    def test_complex_parallel_groups(self, builder: DependencyGraphBuilder) -> None:
        """Test parallel grouping with a more complex DAG."""
        tasks = {
            "task_a": {"agent_type": "worker"},
            "task_b": {"agent_type": "worker", "dependencies": ["task_a"]},
            "task_c": {"agent_type": "worker"},
            "task_d": {"agent_type": "worker", "dependencies": ["task_b", "task_c"]},
            "task_e": {"agent_type": "worker", "dependencies": ["task_d"]},
        }
        graph = builder.build(tasks)
        groups = builder.compute_parallel_groups(graph)

        # Level 0: a, c
        # Level 1: b
        # Level 2: d
        # Level 3: e
        assert len(groups) == 4
        assert set(groups[0]) == {"task_a", "task_c"}
        assert groups[1] == ["task_b"]
        assert groups[2] == ["task_d"]
        assert groups[3] == ["task_e"]

    # ------------------------------------------------------------------
    # Cycle detection
    # ------------------------------------------------------------------

    def test_cycle_detection(self, builder: DependencyGraphBuilder) -> None:
        """Test that cycles raise GraphCycleError."""
        cyclic_tasks = {
            "task_a": {"agent_type": "worker", "dependencies": ["task_b"]},
            "task_b": {"agent_type": "worker", "dependencies": ["task_c"]},
            "task_c": {"agent_type": "worker", "dependencies": ["task_a"]},
        }
        with pytest.raises(GraphCycleError) as exc_info:
            builder.build(cyclic_tasks)
        assert "cycle" in str(exc_info.value).lower()

    def test_self_loop_detection(self, builder: DependencyGraphBuilder) -> None:
        """Test that a self-loop raises GraphCycleError."""
        tasks = {
            "task_a": {"agent_type": "worker", "dependencies": ["task_a"]},
        }
        with pytest.raises(GraphCycleError):
            builder.build(tasks)

    # ------------------------------------------------------------------
    # Invalid dependencies
    # ------------------------------------------------------------------

    def test_invalid_dependency(self, builder: DependencyGraphBuilder) -> None:
        """Test that invalid dependency references raise an error."""
        tasks = {
            "task_a": {"agent_type": "worker", "dependencies": ["nonexistent_task"]},
        }
        with pytest.raises(InvalidDependencyError) as exc_info:
            builder.build(tasks)
        assert "nonexistent_task" in str(exc_info.value)

    # ------------------------------------------------------------------
    # Adaptive mutation
    # ------------------------------------------------------------------

    def test_adaptive_mutation(self) -> None:
        """Test that graph mutates correctly on failure (Innovation #1)."""
        # Build initial graph
        from src.core.models import TaskNode as TN

        graph = ExecutionGraph(status=GraphStatus.BUILDING)
        graph.add_node(TN(id="flight_search", agent_type="worker"))
        graph.add_node(TN(id="hotel_search", agent_type="worker"))
        graph.add_node(TN(id="budget_calc", agent_type="worker"))
        graph.add_edge("flight_search", "budget_calc")
        graph.add_edge("hotel_search", "budget_calc")
        graph.status = GraphStatus.READY

        adaptive = AdaptiveExecutionGraph(graph)

        # Get affected subgraph for flight_search
        affected = adaptive.get_affected_subgraph("flight_search")
        assert "flight_search" in affected
        assert "budget_calc" in affected  # transitively dependent
        assert "hotel_search" not in affected  # independent

        # Mutate: replace flight_search with train_search
        new_tasks = {
            "train_search": {
                "agent_type": "worker",
                "dependencies": [],
                "input": {"action": "search_train", "origin": "Mumbai", "destination": "Bangalore"},
                "risk_level": "LOW",
            },
        }
        mutated = adaptive.mutate_on_failure("flight_search", new_tasks)

        # flight_search and budget_calc should be removed
        assert "flight_search" not in mutated.nodes
        # hotel_search should remain
        assert "hotel_search" in mutated.nodes
        # train_search should be added
        assert "train_search" in mutated.nodes

        # Graph should be READY after mutation
        assert mutated.status == GraphStatus.READY

    def test_affected_subgraph_chain(self) -> None:
        """Test that get_affected_subgraph handles deep transitive chains."""
        from src.core.models import TaskNode as TN

        graph = ExecutionGraph(status=GraphStatus.READY)
        for i in range(5):
            graph.add_node(TN(id=f"task_{i}", agent_type="worker"))
        for i in range(4):
            graph.add_edge(f"task_{i}", f"task_{i + 1}")

        adaptive = AdaptiveExecutionGraph(graph)

        # Failure at task_1 should affect task_1, task_2, task_3, task_4
        affected = adaptive.get_affected_subgraph("task_1")
        assert set(affected) == {"task_1", "task_2", "task_3", "task_4"}

    # ------------------------------------------------------------------
    # Empty graph
    # ------------------------------------------------------------------

    def test_empty_graph(self, builder: DependencyGraphBuilder) -> None:
        """Test that an empty task dict builds an empty graph."""
        graph = builder.build({})
        assert len(graph.nodes) == 0
        assert len(graph.edges) == 0
        assert graph.status == GraphStatus.READY

    # ------------------------------------------------------------------
    # Ready tasks after completion
    # ------------------------------------------------------------------

    def test_get_ready_tasks(self, builder: DependencyGraphBuilder, simple_tasks: dict) -> None:
        """Test get_ready_tasks returns correct tasks after partial completion."""
        graph = builder.build(simple_tasks)

        # Initially, root tasks (no deps) should be ready
        ready = builder.get_ready_tasks(graph, set())
        assert set(ready) == {"weather_check", "flight_search"}

        # After flight_search is completed, budget_calc should also be ready
        graph.nodes["flight_search"].status = TaskStatus.COMPLETED
        ready = builder.get_ready_tasks(graph, {"flight_search"})
        assert "budget_calc" in ready
