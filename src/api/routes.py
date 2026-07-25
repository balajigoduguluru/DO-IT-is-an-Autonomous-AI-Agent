"""REST API routes for the Agentic AI framework.

Every endpoint is mounted under the ``/api`` prefix defined in
:mod:`src.api.server`.
"""

from __future__ import annotations

import asyncio
import logging
import os
import shutil
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, UploadFile, File

from src.api.schemas import (
    ApprovalResponse,
    ApprovalResponseRequest,
    CreateSessionResponse,
    ErrorResponse,
    GraphResponse,
    LedgerResponse,
    SessionStatusResponse,
    SetGoalRequest,
    SetGoalResponse,
    StartExecutionResponse,
    ToolListResponse,
    ToolMetricsResponse,
)
from src.api.websocket_manager import EventStreamer, manager
from src.core.constants import GraphStatus, StatePhase, TaskStatus
from src.core.models import (
    AgentState,
    ApprovalRequest,
    ExecutionError,
    ExecutionGraph,
    LedgerEntry,
    RiskAssessment,
    TaskNode,
)
from src.core.state import (
    add_edge,
    add_error,
    add_ledger_entry,
    add_task,
    create_initial_state,
    mark_task_completed,
    set_final_summary,
    update_graph_status,
    update_phase,
)
from src.engine.dependency_graph import DependencyGraphBuilder
from src.engine.scheduler import TaskScheduler
from src.utils.helpers import generate_id

logger = logging.getLogger("agentic_ai.api")

router = APIRouter()

# ===========================================================================
# In-memory session stores
# ===========================================================================

#: Active agent states keyed by session ID.
sessions: dict[str, AgentState] = {}

# ===========================================================================
# Singleton accessors (used by routes and websocket_manager)
# ===========================================================================


_approval_gate: Optional["ApprovalGate"] = None  # noqa: F821


def get_approval_gate() -> "ApprovalGate":  # noqa: F821
    """Return the application-wide :class:`ApprovalGate` singleton.

    Initialises it on first access with a 5-minute default timeout.
    """
    global _approval_gate  # noqa: PLW0603
    if _approval_gate is None:
        from src.approval.approval_gate import ApprovalGate

        _approval_gate = ApprovalGate(timeout_seconds=300)
    return _approval_gate


def get_tool_registry():
    """Return the tool registry from the running app.

    Falls back to a fresh :class:`ToolRegistry` instance when the
    ``app`` context is unavailable (e.g. during tests).
    """
    try:
        from src.api.server import app

        return app.state.tool_registry
    except (AttributeError, RuntimeError, ImportError):
        from src.tools.registry import ToolRegistry

        return ToolRegistry()


# ===========================================================================
# Agentic State Machine
# ===========================================================================


# ===========================================================================
# Session endpoints
# ===========================================================================


@router.post("/session", response_model=CreateSessionResponse)
async def create_session() -> CreateSessionResponse:
    """Create a new execution session.

    Returns the ``session_id`` that must be used in subsequent requests.
    """
    session_id = generate_id("ses")

    sessions[session_id] = create_initial_state("", {})

    logger.info("Created session %s", session_id)
    return CreateSessionResponse(session_id=session_id)


@router.post(
    "/session/{session_id}/goal",
    response_model=SetGoalResponse,
    responses={404: {"model": ErrorResponse}},
)
async def set_goal(session_id: str, req: SetGoalRequest) -> SetGoalResponse:
    """Set the user's goal and constraints for a session.

    Stores the goal in the session state.  The full pipeline runs when
    ``POST /session/{id}/start`` is called.
    """
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    state = sessions[session_id]
    state.user_goal = req.goal
    state.constraints = req.constraints

    logger.info("Goal set for session %s: %s", session_id, req.goal[:60])

    return SetGoalResponse(
        session_id=session_id,
        goal=req.goal,
        status=state.current_phase.value,
    )


@router.post(
    "/session/{session_id}/upload",
    responses={404: {"model": ErrorResponse}},
)
async def upload_files(session_id: str, files: list[UploadFile] = File(...)):
    """Upload files to attach to a session."""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
        
    upload_dir = os.path.join(os.getcwd(), "data", "uploads", session_id)
    os.makedirs(upload_dir, exist_ok=True)
    
    uploaded_paths = []
    for file in files:
        if file.filename:
            file_path = os.path.join(upload_dir, file.filename)
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            uploaded_paths.append(file_path)
            
    logger.info("Uploaded %d files for session %s", len(uploaded_paths), session_id)
    return {"session_id": session_id, "uploaded": uploaded_paths}


@router.post(
    "/session/{session_id}/start",
    response_model=StartExecutionResponse,
    responses={404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}},
)
async def start_execution(session_id: str) -> StartExecutionResponse:
    """Start the full execution pipeline as a background task.

    Uses the compiled LangGraph state machine from the application state.
    Returns immediately; monitor progress via the WebSocket or poll endpoint.
    """
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    state = sessions[session_id]

    # Prevent duplicate starts
    if state.current_phase != StatePhase.UNDERSTAND_GOAL:
        raise HTTPException(
            status_code=409,
            detail=f"Session already in phase {state.current_phase.value}",
        )

    from src.api.server import app as _fastapi_app

    lg_app = getattr(_fastapi_app.state, "langraph_app", None)
    if lg_app is None:
        raise HTTPException(
            status_code=503,
            detail="State machine not initialised. Try restarting the server.",
        )

    async def run_pipeline() -> None:
        """Background task that runs the full LangGraph pipeline."""
        try:
            initial = create_initial_state(
                user_goal=state.user_goal,
                constraints=state.constraints,
            )
            final_state = await lg_app.ainvoke(initial)
            sessions[session_id] = final_state
            await EventStreamer.phase_change(session_id, StatePhase.END.value)
        except Exception as exc:
            logger.exception("Pipeline failed for session %s", session_id)
            sessions[session_id] = update_graph_status(
                sessions[session_id], GraphStatus.FAILED
            )
            await EventStreamer.error(session_id, "pipeline", str(exc), False)

    asyncio.create_task(run_pipeline())

    return StartExecutionResponse(
        session_id=session_id,
        status="started",
        message="Execution pipeline initiated. Monitor via WebSocket.",
    )


# ===========================================================================
# Status & data endpoints
# ===========================================================================


@router.get(
    "/session/{session_id}",
    response_model=SessionStatusResponse,
    responses={404: {"model": ErrorResponse}},
)
async def get_session(session_id: str) -> SessionStatusResponse:
    """Get the current status snapshot of a session."""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    state = sessions[session_id]
    tasks = state.execution_graph.nodes if state.execution_graph else {}

    return SessionStatusResponse(
        session_id=session_id,
        phase=state.current_phase,
        graph_status=state.execution_graph.status if state.execution_graph else GraphStatus.BUILDING,
        task_count=len(tasks),
        completed_count=sum(
            1 for t in tasks.values() if t.status == TaskStatus.COMPLETED
        ),
        failed_count=sum(
            1 for t in tasks.values() if t.status == TaskStatus.FAILED
        ),
        pending_approvals=len(state.approval_queue),
    )


@router.get(
    "/session/{session_id}/graph",
    response_model=GraphResponse,
    responses={404: {"model": ErrorResponse}},
)
async def get_graph(session_id: str) -> GraphResponse:
    """Get the current execution graph (nodes + edges)."""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    state = sessions[session_id]
    if not state.execution_graph:
        return GraphResponse(nodes={}, edges=[], status="building")

    return GraphResponse(
        nodes={
            k: v.model_dump() for k, v in state.execution_graph.nodes.items()
        },
        edges=state.execution_graph.edges,
        status=state.execution_graph.status.value,
    )


@router.get(
    "/session/{session_id}/ledger",
    response_model=LedgerResponse,
    responses={404: {"model": ErrorResponse}},
)
async def get_ledger(session_id: str) -> LedgerResponse:
    """Get all execution ledger entries for a session."""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    state = sessions[session_id]
    entries: list[dict[str, Any]] = []
    for entry in state.ledger:
        if isinstance(entry, LedgerEntry):
            entries.append(entry.model_dump())
        elif isinstance(entry, dict):
            entries.append(entry)
        else:
            entries.append({"raw": str(entry)})
    return LedgerResponse(entries=entries, total=len(entries))


# ===========================================================================
# Approval endpoints
# ===========================================================================


@router.post(
    "/approval/{session_id}/respond",
    response_model=ApprovalResponse,
    responses={404: {"model": ErrorResponse}},
)
async def respond_approval(
    session_id: str, req: ApprovalResponseRequest
) -> ApprovalResponse:
    """Respond to a pending approval request.

    Approve or reject a high-risk action.  The response unblocks the
    waiting coroutine in the state machine.
    """
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    gate = get_approval_gate()
    result = await gate.respond(req.approval_id, req.approved)

    if result is None:
        raise HTTPException(
            status_code=404,
            detail="Approval request not found or already processed",
        )

    return ApprovalResponse(success=True, new_status=result.status)


# ===========================================================================
# Tool marketplace endpoints
# ===========================================================================


@router.get("/tools", response_model=ToolListResponse)
async def list_tools() -> ToolListResponse:
    """List all registered tools in the marketplace."""
    registry = get_tool_registry()
    tools = registry.get_available_tools()
    return ToolListResponse(tools=tools)


@router.get("/tools/metrics", response_model=ToolMetricsResponse)
async def get_tool_metrics() -> ToolMetricsResponse:
    """Get performance metrics for all registered tools."""
    registry = get_tool_registry()
    metrics = registry.get_all_metrics()
    return ToolMetricsResponse(metrics=metrics)


# ===========================================================================
# Demo endpoint
# ===========================================================================


@router.post("/demo/run", response_model=CreateSessionResponse)
async def run_demo() -> CreateSessionResponse:
    """Run the full demo scenario.

    Creates a session with a predefined travel-planning goal, sets the goal,
    and starts execution.  Returns the ``session_id`` immediately.

    The demo goal is *"Plan a weekend trip to Bangalore under ₹30,000"*.
    """
    from src.api.server import app as _fastapi_app

    lg_app = getattr(_fastapi_app.state, "langraph_app", None)

    # 1. Create session
    session_id = generate_id("demo")
    sessions[session_id] = create_initial_state("", {})

    # 2. Set goal
    goal = "Plan a weekend trip to Bangalore under ₹30,000"
    constraints = {
        "budget": 30000,
        "currency": "INR",
        "destination": "Bangalore",
        "trip_type": "weekend",
    }

    # 3. Start execution in background using the compiled LangGraph
    async def run_demo_pipeline() -> None:
        try:
            initial = create_initial_state(
                user_goal=goal,
                constraints=constraints,
            )
            if lg_app is not None:
                final_state = await lg_app.ainvoke(initial)
                sessions[session_id] = final_state
            else:
                logger.warning("LangGraph not available for demo")
        except Exception as exc:
            logger.exception("Demo pipeline failed for session %s", session_id)
            sessions[session_id] = update_graph_status(
                sessions[session_id], GraphStatus.FAILED
            )

    asyncio.create_task(run_demo_pipeline())

    return CreateSessionResponse(session_id=session_id)


# ===========================================================================
# Health check endpoint
# ===========================================================================


@router.get("/health")
async def health_check():
    """Health check endpoint for monitoring and load balancers."""
    return {"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()}