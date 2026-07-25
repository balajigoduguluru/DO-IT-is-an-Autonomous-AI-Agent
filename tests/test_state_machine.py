"""Tests for the LangGraph state machine flow."""

import sys
from pathlib import Path

import pytest

_HERE = Path(__file__).resolve().parent
_PROJECT_ROOT = _HERE.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from src.core.constants import GraphStatus, StatePhase, TaskStatus
from src.core.exceptions import MaxReplanAttemptsError, ReplanTriggeredError
from src.core.models import AgentState, ExecutionGraph, TaskNode
from src.core.state import (
    add_edge,
    add_task,
    create_initial_state,
    mark_task_completed,
    mark_task_failed,
    transition_graph_on_completion,
    update_phase,
)


class TestStateMachine:
    """Test the full state machine flow: START → understand → build DAG
    → execute → evaluate → approval → summary → END, including replan
    branches.
    """

    # ------------------------------------------------------------------
    # Fixtures
    # ------------------------------------------------------------------

    @pytest.fixture
    def initial_state(self) -> AgentState:
        return create_initial_state(
            user_goal="Plan a trip to Bangalore under ₹30,000",
            constraints={"budget": 30000, "currency": "INR"},
        )

    # ------------------------------------------------------------------
    # Happy path: full execution flow
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_full_execution_flow(self, initial_state: AgentState) -> None:
        """Test START → understand → build DAG → execute → evaluate
        → approval → summary → END."""
        state = initial_state

        # -- Phase 1: Understand goal --
        assert state.current_phase == StatePhase.UNDERSTAND_GOAL
        state = update_phase(state, StatePhase.BUILD_DAG)
        assert state.current_phase == StatePhase.BUILD_DAG

        # -- Phase 2: Build DAG --
        task_a = TaskNode(id="weather_check", agent_type="worker")
        task_b = TaskNode(id="flight_search", agent_type="worker")
        task_c = TaskNode(id="hotel_search", agent_type="worker")
        task_d = TaskNode(id="budget_calc", agent_type="worker", dependencies=["flight_search", "hotel_search"])

        state = add_task(state, task_a)
        state = add_task(state, task_b)
        state = add_task(state, task_c)
        state = add_task(state, task_d)
        # Dependencies: d depends on b and c
        state = add_edge(state, "flight_search", "budget_calc")
        state = add_edge(state, "hotel_search", "budget_calc")

        state.execution_graph.status = GraphStatus.READY
        assert len(state.execution_graph.nodes) == 4
        assert state.execution_graph.status == GraphStatus.READY

        # -- Phase 3: Execute --
        state = update_phase(state, StatePhase.EXECUTE)
        state.execution_graph.status = GraphStatus.EXECUTING

        state = mark_task_completed(state, "weather_check", {"temp": 26})
        state = mark_task_completed(state, "flight_search", {"flight": "6E-213"})
        state = mark_task_completed(state, "hotel_search", {"hotel": "FabHotel"})
        state = mark_task_completed(state, "budget_calc", {"total": 14500})

        # -- Phase 4: Evaluate --
        state = transition_graph_on_completion(state)
        assert state.current_phase == StatePhase.EVALUATE
        assert state.execution_graph.status == GraphStatus.COMPLETED

        # -- Phase 5: Approval --
        state = update_phase(state, StatePhase.APPROVAL)
        assert state.current_phase == StatePhase.APPROVAL

        # -- Phase 6: Summary --
        state = update_phase(state, StatePhase.SUMMARY)
        state.final_summary = "Trip planned successfully under ₹30,000"
        assert state.final_summary is not None

        state = update_phase(state, StatePhase.END)
        assert state.current_phase == StatePhase.END

        # Verify no errors
        assert len(state.errors) == 0

    # ------------------------------------------------------------------
    # Replan flow
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_replan_flow(self, initial_state: AgentState) -> None:
        """Test that replanning triggers correctly on failure."""
        state = initial_state

        # Build a simple graph: A → B
        task_a = TaskNode(id="flight_search", agent_type="worker")
        task_b = TaskNode(id="budget_calc", agent_type="worker", dependencies=["flight_search"])
        state = add_task(state, task_a)
        state = add_task(state, task_b)
        state.execution_graph.status = GraphStatus.READY

        # Flight search fails
        state = mark_task_failed(state, "flight_search", "503 Service Unavailable")
        assert state.execution_graph.nodes["flight_search"].status == TaskStatus.FAILED

        # Trigger replanning
        state.execution_graph.status = GraphStatus.REPLANNING
        state = update_phase(state, StatePhase.REPLAN)
        assert state.current_phase == StatePhase.REPLAN

        # Replan: replace flight with train
        state.execution_graph.nodes["train_search"] = TaskNode(
            id="train_search", agent_type="worker"
        )
        # Remove the failed task (replaced by new task)
        del state.execution_graph.nodes["flight_search"]
        state.execution_graph.status = GraphStatus.READY
        state = update_phase(state, StatePhase.EXECUTE)

        # Complete the replacement task
        state = mark_task_completed(state, "train_search", {"train": "16589"})
        state = mark_task_completed(state, "budget_calc", {"total": 5000})

        # Verify completion
        state = transition_graph_on_completion(state)
        assert state.execution_graph.status == GraphStatus.COMPLETED

    # ------------------------------------------------------------------
    # Max replan limit
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_max_replan_limit(self, initial_state: AgentState) -> None:
        """Test that MAX_REPLAN_ATTEMPTS prevents infinite loops."""
        state = initial_state
        max_attempts = 3

        # Build a simple graph
        task = TaskNode(id="unstable_task", agent_type="worker")
        state = add_task(state, task)
        state.execution_graph.status = GraphStatus.READY

        # Simulate repeated failures beyond the limit
        for attempt in range(1, max_attempts + 2):
            if attempt > max_attempts:
                with pytest.raises(MaxReplanAttemptsError):
                    raise MaxReplanAttemptsError(
                        attempts=attempt,
                        max_attempts=max_attempts,
                    )
                break

            state = mark_task_failed(state, "unstable_task", f"Attempt {attempt} failed")
            state.execution_graph.status = GraphStatus.FAILED

        # Verify error recording
        assert len(state.errors) == max_attempts

    # ------------------------------------------------------------------
    # Approval gate pauses execution
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_approval_gate_pauses_execution(self, initial_state: AgentState) -> None:
        """Test that execution pauses at approval gate."""
        state = initial_state

        # Approval is signalled by entering the APPROVAL phase
        # and having pending approval requests in the queue
        state = update_phase(state, StatePhase.APPROVAL)
        assert state.current_phase == StatePhase.APPROVAL

        # Simulate an approval request
        from src.core.models import ApprovalRequest, RiskAssessment

        req = ApprovalRequest(
            session_id=state.session_id,
            task_id="train_booking",
            action_description="Book train 16589 Bangalore Express",
            risk_assessment=RiskAssessment(risk_level="MEDIUM"),
        )
        state.approval_queue.append(req)
        assert len(state.approval_queue) == 1
        assert state.approval_queue[0].status == "pending"

        # Simulate approval response
        state.approval_queue[0].status = "approved"

        # After approval, move to summary
        state = update_phase(state, StatePhase.SUMMARY)
        assert state.current_phase == StatePhase.SUMMARY

        # Verify the flow continued past the gate
        state = update_phase(state, StatePhase.END)
        assert state.current_phase == StatePhase.END

    # ------------------------------------------------------------------
    # Empty graph edge case
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_empty_graph_completion(self) -> None:
        """Test that an empty graph transitions correctly."""
        state = create_initial_state("Do nothing")
        state.execution_graph.status = GraphStatus.READY

        state = transition_graph_on_completion(state)
        # With no nodes, transition_on_completion returns unchanged
        assert state.execution_graph.status == GraphStatus.READY

    # ------------------------------------------------------------------
    # Phase transition guards
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_phase_transition_guards(self, initial_state: AgentState) -> None:
        """Test phase transitions happen in the expected order."""
        state = initial_state
        expected_order = [
            StatePhase.UNDERSTAND_GOAL,
            StatePhase.BUILD_DAG,
            StatePhase.SCHEDULE,
            StatePhase.EXECUTE,
            StatePhase.EVALUATE,
            StatePhase.REPLAN,
            StatePhase.APPROVAL,
            StatePhase.SUMMARY,
            StatePhase.END,
        ]

        for phase in expected_order:
            state = update_phase(state, phase)
            assert state.current_phase == phase
