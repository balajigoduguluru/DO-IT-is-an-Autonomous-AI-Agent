"""Custom exceptions for the Agentic AI framework.

All framework exceptions inherit from :class:`AgentError` so that callers
can catch a single base type when needed.
"""

from __future__ import annotations

from typing import Any


# ===========================================================================
# Base exception
# ===========================================================================


class AgentError(Exception):
    """Base exception for all Agentic AI framework errors."""

    def __init__(
        self,
        message: str = "",
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.details = details or {}
        super().__init__(message)


# ===========================================================================
# Tool errors
# ===========================================================================


class ToolError(AgentError):
    """Generic error originating from the tool subsystem."""


class ToolNotFoundError(ToolError):
    """Raised when a requested tool has not been registered."""

    def __init__(self, tool_name: str) -> None:
        self.tool_name = tool_name
        super().__init__(f"Tool {tool_name!r} is not registered")


class ToolExecutionError(ToolError):
    """Raised when a tool call fails at runtime."""

    def __init__(
        self,
        tool_name: str,
        message: str = "",
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.tool_name = tool_name
        super().__init__(
            message or f"Execution of tool {tool_name!r} failed",
            details=details,
        )


# ===========================================================================
# Risk / approval errors
# ===========================================================================


class RiskRejectionError(AgentError):
    """Raised when a task is rejected due to exceeding risk thresholds."""

    def __init__(
        self,
        task_id: str,
        reason: str = "",
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.task_id = task_id
        super().__init__(
            reason or f"Task {task_id!r} was rejected by risk assessment",
            details=details,
        )


class ApprovalRequiredError(AgentError):
    """Raised when a task requires human approval before it can proceed."""

    def __init__(
        self,
        task_id: str,
        approval_id: str,
        reason: str = "",
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.task_id = task_id
        self.approval_id = approval_id
        super().__init__(
            reason or f"Task {task_id!r} requires human approval ({approval_id})",
            details=details,
        )


class ApprovalTimeoutError(AgentError):
    """Raised when human approval was not provided within the timeout window."""

    def __init__(
        self,
        approval_id: str,
        timeout_seconds: int,
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.approval_id = approval_id
        self.timeout_seconds = timeout_seconds
        super().__init__(
            f"Approval request {approval_id!r} timed out after "
            f"{timeout_seconds}s",
            details=details,
        )


# ===========================================================================
# Replanning errors
# ===========================================================================


class ReplanTriggeredError(AgentError):
    """Raised to signal that the agent should enter the replanning phase."""

    def __init__(
        self,
        reason: str = "",
        *,
        affected_task_ids: list[str] | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.affected_task_ids = affected_task_ids or []
        super().__init__(
            reason or "Replan triggered",
            details=details,
        )


class MaxReplanAttemptsError(AgentError):
    """Raised when the replan loop exceeds the maximum allowed attempts."""

    def __init__(
        self,
        attempts: int,
        max_attempts: int,
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.attempts = attempts
        self.max_attempts = max_attempts
        super().__init__(
            f"Replanning exceeded maximum {max_attempts} "
            f"attempt(s) after {attempts} tries",
            details=details,
        )


# ===========================================================================
# Graph errors
# ===========================================================================


class GraphCycleError(AgentError):
    """Raised when adding an edge would create a cycle in the execution DAG."""

    def __init__(
        self,
        from_id: str,
        to_id: str,
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.from_id = from_id
        self.to_id = to_id
        super().__init__(
            f"Adding edge {from_id!r} -> {to_id!r} would create a cycle",
            details=details,
        )


# ===========================================================================
# Model routing
# ===========================================================================


class ModelRoutingError(AgentError):
    """Raised when the model router cannot find a suitable model."""

    def __init__(
        self,
        agent_type: str = "",
        message: str = "",
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.agent_type = agent_type
        super().__init__(
            message or f"No model route found for agent type {agent_type!r}",
            details=details,
        )


# ===========================================================================
# Memory
# ===========================================================================


class MemoryStorageError(AgentError):
    """Raised when a memory read/write operation fails."""

    def __init__(
        self,
        operation: str,
        message: str = "",
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.operation = operation
        super().__init__(
            message or f"Memory storage operation {operation!r} failed",
            details=details,
        )
