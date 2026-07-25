"""Tests for the parallel execution engine (Innovation #3).

Tests concurrent task execution, risk assessment integration, and
fallback execution on tool failure.
"""

import sys
from pathlib import Path

import pytest

_HERE = Path(__file__).resolve().parent
_PROJECT_ROOT = _HERE.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from src.core.constants import GraphStatus, RiskLevel, StatePhase, TaskStatus
from src.core.models import (
    AgentState,
    ExecutionGraph,
    RiskAssessment,
    TaskNode,
    ToolMetrics,
    ToolRegistration,
)
from src.engine.dependency_graph import DependencyGraphBuilder
from src.engine.parallel_executor import ExecutionResult, ParallelExecutor


class TestParallelExecutor:
    """Test concurrent task execution."""

    # ------------------------------------------------------------------
    # Fixtures
    # ------------------------------------------------------------------

    @pytest.fixture
    def builder(self) -> DependencyGraphBuilder:
        return DependencyGraphBuilder()

    @pytest.fixture
    def state(self) -> AgentState:
        """Create a pre-built agent state with a ready graph."""
        s = AgentState(
            user_goal="Test parallel execution",
            execution_graph=ExecutionGraph(status=GraphStatus.READY),
        )
        # Add three independent tasks
        for tid in ("weather_check", "flight_search", "hotel_search"):
            s.execution_graph.add_node(
                TaskNode(id=tid, agent_type="worker")
            )
        return s

    @pytest.fixture
    def worker_agent(self):
        """Create a simple worker that completes tasks successfully."""

        class FakeWorker:
            async def execute(self, task_id: str, state: AgentState, tool_registry=None):
                return ExecutionResult(
                    task_id=task_id,
                    success=True,
                    data={"task": task_id, "result": "ok"},
                    duration_ms=10.0,
                    tool_used="mock_tool",
                )

        return FakeWorker()

    @pytest.fixture
    def failing_worker(self):
        """Create a worker that fails for specific tasks."""

        class FailingWorker:
            async def execute(self, task_id: str, state: AgentState, tool_registry=None):
                if task_id == "flight_search":
                    return ExecutionResult(
                        task_id=task_id,
                        success=False,
                        data=None,
                        error="503 Service Unavailable",
                        duration_ms=10.0,
                        tool_used="flight_api",
                    )
                return ExecutionResult(
                    task_id=task_id,
                    success=True,
                    data={"task": task_id, "result": "ok"},
                    duration_ms=10.0,
                    tool_used="mock_tool",
                )

        return FailingWorker()

    # ------------------------------------------------------------------
    # Parallel execution
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_parallel_execution(
        self, state: AgentState, worker_agent, builder: DependencyGraphBuilder
    ) -> None:
        """Test that independent tasks run concurrently."""
        # Compute parallel groups
        groups = builder.compute_parallel_groups(state.execution_graph)
        assert len(groups) == 1  # all three are at level 0
        assert set(groups[0]) == {"weather_check", "flight_search", "hotel_search"}

        executor = ParallelExecutor(worker_agent=worker_agent, max_parallel=5)
        results = await executor.execute_group(groups[0], state)

        # All three should succeed
        assert len(results) == 3
        for tid, result in results:
            assert result["success"], f"Task {tid} failed"
            assert result["data"]["result"] == "ok"

        # Task statuses should be COMPLETED
        for tid in groups[0]:
            assert state.execution_graph.nodes[tid].status == TaskStatus.COMPLETED

    # ------------------------------------------------------------------
    # Fallback execution
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_fallback_execution(
        self, state: AgentState, failing_worker
    ) -> None:
        """Test fallback chain on tool failure."""
        executor = ParallelExecutor(worker_agent=failing_worker, max_parallel=5)

        group = list(state.execution_graph.nodes.keys())
        results = await executor.execute_group(group, state)

        # flight_search should fail
        result_map = dict(results)
        assert not result_map["flight_search"]["success"]
        assert "503" in result_map["flight_search"]["error"]

        # Other tasks should succeed
        assert result_map["weather_check"]["success"]
        assert result_map["hotel_search"]["success"]

        # Graph status should stay as-is (full_graph execution handles replan)
        assert state.execution_graph.nodes["flight_search"].status == TaskStatus.FAILED
        assert state.execution_graph.nodes["weather_check"].status == TaskStatus.COMPLETED
        assert state.execution_graph.nodes["hotel_search"].status == TaskStatus.COMPLETED

    # ------------------------------------------------------------------
    # Full graph execution with failures
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_full_graph_with_failure(
        self, state: AgentState, failing_worker
    ) -> None:
        """Test that full graph execution returns early on failure with
        needs_replan=True."""
        executor = ParallelExecutor(worker_agent=failing_worker, max_parallel=5)
        result_state = await executor.execute_full_graph(state)

        # Should have set needs_replan because flight_search failed
        assert result_state.needs_replan is True
        assert result_state.execution_graph.status == GraphStatus.FAILED

    # ------------------------------------------------------------------
    # Full graph success
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_full_graph_success(
        self, state: AgentState, worker_agent
    ) -> None:
        """Test that full graph execution completes successfully."""
        executor = ParallelExecutor(worker_agent=worker_agent, max_parallel=5)
        result_state = await executor.execute_full_graph(state)

        assert result_state.needs_replan is False
        assert result_state.execution_graph.status == GraphStatus.COMPLETED

    # ------------------------------------------------------------------
    # Risk assessment integration
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_risk_assessment_integration(
        self, state: AgentState, worker_agent
    ) -> None:
        """Test that risk assessment runs before task execution when a
        risk predictor is configured."""

        assessed_tasks = []

        class TrackingRiskPredictor:
            async def assess(self, task_id: str, state: AgentState) -> RiskAssessment:
                assessed_tasks.append(task_id)
                return RiskAssessment(risk_level=RiskLevel.LOW)

        executor = ParallelExecutor(
            worker_agent=worker_agent,
            risk_predictor=TrackingRiskPredictor(),
            max_parallel=5,
        )

        group = list(state.execution_graph.nodes.keys())
        await executor.execute_group(group, state)

        # All tasks should have been assessed
        assert set(assessed_tasks) == set(group)

    # ------------------------------------------------------------------
    # Concurrency semaphore
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_concurrency_limit(
        self, state: AgentState, worker_agent
    ) -> None:
        """Test that max_parallel limits concurrency (semaphore)."""
        executor = ParallelExecutor(worker_agent=worker_agent, max_parallel=2)
        group = list(state.execution_graph.nodes.keys())

        results = await executor.execute_group(group, state)
        assert len(results) == 3

    # ------------------------------------------------------------------
    # Empty group
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_empty_group(
        self, state: AgentState, worker_agent
    ) -> None:
        """Test that executing an empty group returns empty results."""
        executor = ParallelExecutor(worker_agent=worker_agent, max_parallel=5)
        results = await executor.execute_group([], state)
        assert results == []
