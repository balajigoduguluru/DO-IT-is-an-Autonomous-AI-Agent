"""Pydantic v2 schemas for API request/response models.

These schemas define the wire format for every REST endpoint and serve as
the single source of truth for the API contract.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from src.core.constants import GraphStatus, StatePhase
from src.core.models import LedgerEntry, ToolMetrics, ToolRegistration


# ===========================================================================
# Session
# ===========================================================================


class CreateSessionResponse(BaseModel):
    """Returned after creating a new execution session."""

    session_id: str


class SetGoalRequest(BaseModel):
    """Payload for setting the user's goal on a session."""

    goal: str
    constraints: dict[str, Any] = Field(default_factory=dict)


class SetGoalResponse(BaseModel):
    """Returned after setting the goal for a session."""

    session_id: str
    goal: str
    status: str


class StartExecutionResponse(BaseModel):
    """Returned after initiating the execution pipeline."""

    session_id: str
    status: str
    message: str


class SessionStatusResponse(BaseModel):
    """Snapshot of the current session state."""

    session_id: str
    phase: StatePhase
    graph_status: GraphStatus
    task_count: int
    completed_count: int
    failed_count: int
    pending_approvals: int


# ===========================================================================
# Graph
# ===========================================================================


class GraphResponse(BaseModel):
    """Serialised representation of the execution graph."""

    nodes: dict[str, Any]
    edges: list[list[str]]
    status: str


# ===========================================================================
# Ledger
# ===========================================================================


class LedgerResponse(BaseModel):
    """Paginated ledger entries for a session."""

    entries: list[dict[str, Any]]
    total: int


# ===========================================================================
# Approval
# ===========================================================================


class ApprovalResponseRequest(BaseModel):
    """Payload for responding to an approval request."""

    approval_id: str
    approved: bool


class ApprovalResponse(BaseModel):
    """Returned after responding to an approval request."""

    success: bool
    new_status: str


# ===========================================================================
# Tools
# ===========================================================================


class ToolListResponse(BaseModel):
    """Returned when listing all registered tools."""

    tools: list[ToolRegistration]


class ToolMetricsResponse(BaseModel):
    """Returned when fetching all tool metrics."""

    metrics: dict[str, ToolMetrics]


# ===========================================================================
# Error
# ===========================================================================


class ErrorResponse(BaseModel):
    """Standard error envelope returned by the API."""

    detail: str
    error_code: str | None = None
