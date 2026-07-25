"""Enumerations and default constants for the Agentic AI framework."""

from __future__ import annotations

import enum


# ===========================================================================
# Enumerations
# ===========================================================================


class TaskStatus(enum.StrEnum):
    """Status of an individual task node within an execution graph."""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    REPLANNING = "REPLANNING"
    SKIPPED = "SKIPPED"


class GraphStatus(enum.StrEnum):
    """Status of the overall execution graph / DAG."""

    BUILDING = "BUILDING"
    READY = "READY"
    EXECUTING = "EXECUTING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    REPLANNING = "REPLANNING"


class StatePhase(enum.StrEnum):
    """High-level phase the agent is currently in during a session."""

    UNDERSTAND_GOAL = "UNDERSTAND_GOAL"
    CONSTRAIN = "CONSTRAIN"              # Constraint extraction
    PLANNING = "PLANNING"                # Task decomposition by Planner
    BUILD_DAG = "BUILD_DAG"
    SCHEDULE = "SCHEDULE"
    RISK_ANALYSIS = "RISK_ANALYSIS"      # Risk assessment
    TOOL_SELECT = "TOOL_SELECT"          # Tool marketplace selection
    EXECUTE = "EXECUTE"
    EVALUATE = "EVALUATE"
    REPLAN = "REPLAN"
    APPROVAL = "APPROVAL"
    SUMMARY = "SUMMARY"
    MEMORY_STORE = "MEMORY_STORE"        # Learning memory persistence
    END = "END"


class ToolCategory(enum.StrEnum):
    """Functional category a registered tool belongs to."""

    FLIGHT = "FLIGHT"
    HOTEL = "HOTEL"
    TRANSPORT = "TRANSPORT"
    WEATHER = "WEATHER"
    BUDGET = "BUDGET"
    EMAIL = "EMAIL"
    SEARCH = "SEARCH"
    GENERAL = "GENERAL"


class MemoryType(enum.StrEnum):
    """Kind of information stored in long-term memory."""

    TOOL_SUCCESS = "TOOL_SUCCESS"
    TOOL_FAILURE = "TOOL_FAILURE"
    RECOVERY_PATTERN = "RECOVERY_PATTERN"
    USER_PREFERENCE = "USER_PREFERENCE"
    FAILED_PLAN = "FAILED_PLAN"
    SUCCESSFUL_PLAN = "SUCCESSFUL_PLAN"


class RiskLevel(enum.StrEnum):
    """Severity of a risk assessment for a task or action."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


# ===========================================================================
# Default constants
# ===========================================================================

#: Maximum number of retries for a single task execution.
MAX_RETRIES: int = 3

#: Maximum API calls allowed within the rate-limit window.
RATE_LIMIT_CALLS: int = 100

#: Rate-limit window in seconds.
RATE_LIMIT_WINDOW: int = 60
