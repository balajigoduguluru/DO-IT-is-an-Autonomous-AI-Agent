"""Pydantic v2 models for the Agentic AI core framework."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from src.core.constants import (
    GraphStatus,
    MemoryType,
    RiskLevel,
    StatePhase,
    TaskStatus,
    ToolCategory,
)


# ===========================================================================
# Task & Graph models
# ===========================================================================


class RiskAssessment(BaseModel):
    """Assessment of risk associated with a task or action."""

    risk_level: RiskLevel = RiskLevel.LOW
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    failure_probability: float = Field(default=0.0, ge=0.0, le=1.0)
    cost_estimate: float = Field(default=0.0, ge=0.0)
    security_flags: list[str] = Field(default_factory=list)
    requires_approval: bool = False
    reasoning: str = ""

    @field_validator("failure_probability")
    @classmethod
    def _clamp_probability(cls, v: float) -> float:
        return max(0.0, min(1.0, v))


class TaskNode(BaseModel):
    """A single unit of work in the execution graph."""

    id: str = Field(default_factory=lambda: f"task_{uuid.uuid4().hex[:12]}")
    agent_type: Literal["supervisor", "planner", "worker", "evaluator"]
    status: TaskStatus = TaskStatus.PENDING
    input: dict[str, Any] = Field(default_factory=dict)
    output: dict[str, Any] | None = None
    dependencies: list[str] = Field(default_factory=list)
    risk_assessment: RiskAssessment | None = None
    model_assigned: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = None

    model_config = ConfigDict(arbitrary_types_allowed=True)


class ExecutionGraph(BaseModel):
    """Directed acyclic graph of task nodes representing an execution plan."""

    nodes: dict[str, TaskNode] = Field(default_factory=dict)
    edges: list[list[str]] = Field(default_factory=list)  # [[from_id, to_id], ...]
    status: GraphStatus = GraphStatus.BUILDING
    metadata: dict[str, Any] = Field(default_factory=dict)
    topological_levels: dict[str, int] = Field(
        default_factory=dict,
        description="Topological depth of each node computed by the builder.",
    )

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @field_validator("edges")
    @classmethod
    def _validate_edge_format(cls, v: list[list[str]]) -> list[list[str]]:
        for edge in v:
            if len(edge) != 2:
                raise ValueError(f"Each edge must be [from_id, to_id], got {edge!r}")
            if not edge[0] or not edge[1]:
                raise ValueError(f"Edge node IDs must be non-empty strings, got {edge!r}")
        return v

    def add_node(self, node: TaskNode) -> TaskNode:
        """Register a node in the graph.

        Returns the node so this method can be used chained with field
        initialisation.
        """
        self.nodes[node.id] = node
        return node

    def add_edge(self, from_id: str, to_id: str) -> None:
        """Add a directed edge between two nodes (by ID)."""
        if from_id not in self.nodes:
            raise KeyError(f"Source node {from_id!r} not found in graph")
        if to_id not in self.nodes:
            raise KeyError(f"Target node {to_id!r} not found in graph")
        self.edges.append([from_id, to_id])

    def get_dependents(self, task_id: str) -> list[str]:
        """Return all node IDs that directly depend on *task_id*."""
        return [to_id for from_id, to_id in self.edges if from_id == task_id]

    def get_dependencies(self, task_id: str) -> list[str]:
        """Return all node IDs that *task_id* directly depends on."""
        return [from_id for from_id, to_id in self.edges if to_id == task_id]

    def get_ready_nodes(self) -> list[TaskNode]:
        """Return all nodes whose dependencies are completed."""
        ready: list[TaskNode] = []
        for node in self.nodes.values():
            if node.status != TaskStatus.PENDING:
                continue
            deps = self.get_dependencies(node.id)
            if all(self.nodes[d].status == TaskStatus.COMPLETED for d in deps):
                ready.append(node)
        return ready


# ===========================================================================
# Session / Agent state
# ===========================================================================


class LedgerEntry(BaseModel):
    """An audit-log entry recording an action taken by an agent."""

    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    agent: str
    action: str
    task_id: str | None = None
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    latency_ms: float = Field(default=0.0, ge=0.0)
    risk_level: str | None = None
    details: dict[str, Any] | None = None


class ApprovalRequest(BaseModel):
    """A request for human approval of a high-risk action."""

    id: str = Field(default_factory=lambda: f"apr_{uuid.uuid4().hex[:12]}")
    session_id: str
    task_id: str
    action_description: str
    risk_assessment: RiskAssessment = Field(default_factory=RiskAssessment)
    status: Literal["pending", "approved", "rejected", "expired"] = "pending"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    responded_at: datetime | None = None
    model_config = ConfigDict(arbitrary_types_allowed=True)


class ExecutionError(BaseModel):
    """Details of an error encountered during task execution."""

    task_id: str
    error_type: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    recoverable: bool = True
    model_config = ConfigDict(arbitrary_types_allowed=True)


class AgentState(BaseModel):
    """Top-level state of the agentic loop for a single session."""

    session_id: str = Field(default_factory=lambda: f"ses_{uuid.uuid4().hex[:12]}")
    user_goal: str
    constraints: dict[str, Any] = Field(default_factory=dict)
    execution_graph: ExecutionGraph = Field(default_factory=ExecutionGraph)
    current_phase: StatePhase = StatePhase.UNDERSTAND_GOAL
    ledger: list[LedgerEntry] = Field(default_factory=list)
    approval_queue: list[ApprovalRequest] = Field(default_factory=list)
    memory_context: dict[str, Any] = Field(default_factory=dict)
    errors: list[ExecutionError] = Field(default_factory=list)
    final_summary: str | None = None
    needs_replan: bool = False

    model_config = ConfigDict(arbitrary_types_allowed=True)


# ===========================================================================
# Tool models
# ===========================================================================


class ToolMetrics(BaseModel):
    """Performance metrics tracked for a tool."""

    tool_name: str
    latency_ms: float = Field(default=0.0, ge=0.0)
    accuracy: float = Field(default=1.0, ge=0.0, le=1.0)
    failure_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    avg_cost: float = Field(default=0.0, ge=0.0)
    last_used: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    total_calls: int = Field(default=0, ge=0)

    model_config = ConfigDict(arbitrary_types_allowed=True)


class ToolRegistration(BaseModel):
    """Registration metadata for a tool that can be invoked by the agent."""

    name: str
    description: str
    category: ToolCategory
    provider: str
    metrics: ToolMetrics | None = None
    input_schema: dict[str, Any] = Field(default_factory=dict)
    output_schema: dict[str, Any] = Field(default_factory=dict)
    fallback_chain: list[str] = Field(default_factory=list)
    is_available: bool = True


class ToolCallResult(BaseModel):
    """Result of a single tool invocation."""

    tool_name: str
    success: bool
    output: dict[str, Any] | None = None
    error: str | None = None
    latency_ms: float = Field(default=0.0, ge=0.0)
    cost: float = Field(default=0.0, ge=0.0)


# ===========================================================================
# Evaluation & Replanning
# ===========================================================================


class EvalScore(BaseModel):
    """Evaluation scores for a task result."""

    correctness: float = Field(default=0.0, ge=0.0, le=1.0)
    completeness: float = Field(default=0.0, ge=0.0, le=1.0)
    safety: float = Field(default=0.0, ge=0.0, le=1.0)
    overall: float = Field(default=0.0, ge=0.0, le=1.0)
    reasoning: str = ""

    @model_validator(mode="after")
    def _compute_default_overall(self) -> "EvalScore":
        if self.overall == 0.0 and any(
            [self.correctness, self.completeness, self.safety]
        ):
            self.overall = (self.correctness + self.completeness + self.safety) / 3.0
        return self


class ReplanDecision(BaseModel):
    """Decision produced by the evaluator about whether to replan."""

    needs_replan: bool = False
    affected_task_ids: list[str] = Field(default_factory=list)
    reason: str = ""
    alternative_approach: str | None = None


# ===========================================================================
# Memory models
# ===========================================================================


class MemoryEntry(BaseModel):
    """A single entry in the long-term memory store."""

    id: str = Field(default_factory=lambda: f"mem_{uuid.uuid4().hex[:12]}")
    type: MemoryType
    key: str
    value: dict[str, Any] = Field(default_factory=dict)
    embedding: list[float] | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    session_id: str
    weight: float = Field(default=1.0, ge=0.0)

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @field_validator("embedding")
    @classmethod
    def _validate_embedding(cls, v: list[float] | None) -> list[float] | None:
        if v is not None and len(v) == 0:
            raise ValueError("Embedding vector must not be empty when provided")
        return v


class PlanMemory(BaseModel):
    """Record of a past plan for learning / retrieval."""

    id: str = Field(default_factory=lambda: f"plan_{uuid.uuid4().hex[:12]}")
    session_id: str
    goal: str
    graph_snapshot: dict[str, Any] = Field(default_factory=dict)
    success: bool = False
    score: float | None = Field(default=None, ge=0.0, le=1.0)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = ConfigDict(arbitrary_types_allowed=True)


# ===========================================================================
# Model routing
# ===========================================================================


class ModelRoute(BaseModel):
    """Configuration for routing a task to an LLM provider/model."""

    agent_type: str
    primary_model: str
    fallback_model: str = ""
    context_window: int = Field(default=128_000, ge=1_000)
    cost_per_token: float = Field(default=0.0, ge=0.0)
    priority: int = Field(default=0, ge=0)


# ===========================================================================
# Demo
# ===========================================================================


class DemoStep(BaseModel):
    """A single step in an interactive demo script."""

    name: str
    description: str
    expected_outcome: str
    delay_seconds: float = Field(default=1.0, ge=0.0)


class DemoScript(BaseModel):
    """A full demo script consisting of ordered steps."""

    steps: list[DemoStep] = Field(default_factory=list)

    def add_step(
        self,
        name: str,
        description: str,
        expected_outcome: str,
        delay_seconds: float = 1.0,
    ) -> DemoStep:
        step = DemoStep(
            name=name,
            description=description,
            expected_outcome=expected_outcome,
            delay_seconds=delay_seconds,
        )
        self.steps.append(step)
        return step
