"""LangGraph-based state machine that orchestrates the full agent lifecycle.

This module implements the **execution engine** as a directed state graph
using LangGraph's :class:`StateGraph`.  Every node in the graph corresponds
to a phase in the agent's lifecycle and delegates to the appropriate
engine component.

State flow
----------
START ``understand_goal`` → ``build_dag`` → ``schedule_tasks`` →
    ``parallel_execute`` → ``evaluate`` → **conditional** → ``approval``
    → ``summary`` → ``end``

If the evaluator detects failures, the conditional edge routes through
the **replan loop** instead:

    ``evaluate`` → ``decide_replan`` → ``update_dag`` → ``schedule_tasks``
    → ``parallel_execute`` → ``evaluate`` → ...

The replan loop is bounded by ``MAX_REPLAN_ATTEMPTS`` (from settings),
after which the graph proceeds to ``approval`` regardless.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from src.core.config import Settings, settings as _settings
from src.core.constants import GraphStatus, StatePhase, TaskStatus
from src.core.exceptions import MaxReplanAttemptsError
from src.core.models import AgentState, ExecutionGraph, LedgerEntry, TaskNode
from src.engine.dependency_graph import DependencyGraphBuilder
from src.engine.execution_graph import AdaptiveExecutionGraph
from src.engine.parallel_executor import ParallelExecutor
from src.engine.scheduler import TaskScheduler
from src.agents.supervisor import SupervisorAgent
from src.agents.planner import PlannerAgent

try:
    from langgraph.graph import END, StateGraph
except ImportError:
    # Fallback for environments where LangGraph is not installed —
    # define just enough to let the module be imported for type-checking.
    END = "__end__"  # type: ignore[assignment]

    class StateGraph:  # type: ignore[no-redef]
        """Stub that raises on instantiation."""

        def __init__(self, *args: Any, **kwargs: Any) -> None:
            raise ImportError(
                "langgraph is required to run the AgenticStateMachine. "
                "Install it with: pip install langgraph"
            )

        def add_node(self, *args: Any, **kwargs: Any) -> None: ...
        def add_edge(self, *args: Any, **kwargs: Any) -> None: ...
        def add_conditional_edges(self, *args: Any, **kwargs: Any) -> None: ...
        def set_entry_point(self, *args: Any, **kwargs: Any) -> None: ...
        def set_finish_point(self, *args: Any, **kwargs: Any) -> None: ...
        def compile(self) -> "CompiledGraph": ...

    class CompiledGraph:  # type: ignore[no-redef]
        async def ainvoke(self, *args: Any, **kwargs: Any) -> Any:
            raise ImportError("langgraph is required to run the AgenticStateMachine.")


# ===========================================================================
# State Machine
# ===========================================================================


class AgenticStateMachine:
    """LangGraph-based orchestrator for the agent execution lifecycle.

    Parameters
    ----------
    parallel_executor:
        The executor used to run tasks concurrently.  If omitted a bare
        executor is constructed that raises ``NotImplementedError`` on use
        (useful for testing the graph topology without real agents).
    task_scheduler:
        The scheduler that assigns tools and computes parallel groups.
    dependency_builder:
        Builder that validates and topologically orders the task graph.
    settings:
        Application settings (reads ``MAX_REPLAN_ATTEMPTS`` from here).
    """

    def __init__(
        self,
        parallel_executor: ParallelExecutor | None = None,
        task_scheduler: TaskScheduler | None = None,
        dependency_builder: DependencyGraphBuilder | None = None,
        settings: Settings | None = None,
        tool_registry: Any = None,
        risk_predictor: Any = None,
        learning_memory: Any = None,
        evaluator: Any = None,
    ) -> None:
        self._settings = settings or _settings
        self._executor = parallel_executor or ParallelExecutor(
            worker_agent=_PlaceholderAgent(),
        )
        self._scheduler = task_scheduler or TaskScheduler()
        self._builder = dependency_builder or DependencyGraphBuilder()
        self._tool_registry = tool_registry
        self._risk_predictor = risk_predictor
        self._learning_memory = learning_memory
        self._evaluator = evaluator
        self._supervisor = SupervisorAgent(model=self._settings.OPENAI_MODEL_PRIMARY)
        self._planner = PlannerAgent(model=self._settings.OPENAI_MODEL_PRIMARY)
        self._session_id: str = ""

        self._compiled: CompiledGraph | None = None

    # ------------------------------------------------------------------
    # Build & compile the LangGraph
    # ------------------------------------------------------------------

    def build_graph(self) -> StateGraph:
        """Construct and return the ``StateGraph``.

        Nodes are added for each lifecycle phase.  Conditional edges are
        wired at the ``evaluate`` and ``decide_replan`` junctions.

        The graph is **not** compiled until :meth:`compile` or :meth:`run`
        is called.
        """
        graph = StateGraph(AgentState)

        # -- Add all nodes ---------------------------------------------------
        graph.add_node("understand_goal", self._node_understand_goal)
        graph.add_node("extract_constraints", self._node_extract_constraints)
        graph.add_node("plan_tasks", self._node_plan_tasks)
        graph.add_node("build_dag", self._node_build_dag)
        graph.add_node("schedule_tasks", self._node_schedule_tasks)
        graph.add_node("risk_analysis", self._node_risk_analysis)
        graph.add_node("select_tools", self._node_select_tools)
        graph.add_node("parallel_execute", self._node_parallel_execute)
        graph.add_node("evaluate", self._node_evaluate)
        graph.add_node("decide_replan", self._node_decide_replan)
        graph.add_node("update_dag", self._node_update_dag)
        graph.add_node("approval", self._node_approval)
        graph.add_node("summary", self._node_summary)
        graph.add_node("store_memory", self._node_store_memory)
        graph.add_node("end", self._node_end)

        # -- Straight-through edges ------------------------------------------
        graph.add_edge("understand_goal", "extract_constraints")
        graph.add_edge("extract_constraints", "plan_tasks")
        graph.add_edge("plan_tasks", "build_dag")
        graph.add_edge("build_dag", "schedule_tasks")
        graph.add_edge("schedule_tasks", "risk_analysis")
        graph.add_edge("risk_analysis", "select_tools")
        graph.add_edge("select_tools", "parallel_execute")
        graph.add_edge("parallel_execute", "evaluate")

        # -- Conditional: evaluate → replan or continue ----------------------
        graph.add_conditional_edges(
            "evaluate",
            self._route_after_evaluate,
            {
                "replan": "decide_replan",
                "continue": "approval",
            },
        )

        # -- Conditional: decide_replan → update_dag or skip to approval -----
        graph.add_conditional_edges(
            "decide_replan",
            self._route_after_replan_decision,
            {
                "update_dag": "update_dag",
                "approval": "approval",
            },
        )

        # -- Replan loop back to planner (not scheduler, for full replan) -----
        graph.add_edge("update_dag", "plan_tasks")

        # -- Terminal path ---------------------------------------------------
        graph.add_edge("approval", "summary")
        graph.add_edge("summary", "store_memory")
        graph.add_edge("store_memory", "end")

        graph.set_entry_point("understand_goal")
        graph.set_finish_point("end")

        return graph

    def compile(self) -> CompiledGraph:
        """Build (if needed) and compile the state graph.

        Returns the compiled LangGraph application.
        """
        if self._compiled is None:
            graph = self.build_graph()
            self._compiled = graph.compile()
        return self._compiled

    # ------------------------------------------------------------------
    # Public runner
    # ------------------------------------------------------------------

    async def run(
        self,
        user_goal: str,
        constraints: dict[str, Any] | None = None,
    ) -> AgentState:
        """Full pipeline: create initial state, run the state graph, return
        the final state.

        Parameters
        ----------
        user_goal:
            The user's stated objective.
        constraints:
            Optional mapping of constraint names to values.

        Returns
        -------
        AgentState
            The final state after execution completes, including the
            ``final_summary`` and audit ``ledger``.
        """
        from src.core.state import create_initial_state

        initial = create_initial_state(
            user_goal=user_goal,
            constraints=constraints or {},
        )

        app = self.compile()
        final: AgentState = await app.ainvoke(initial)
        return final

    # ------------------------------------------------------------------
    # Node implementations (spec-style delegates)
    # ------------------------------------------------------------------

    async def understand_goal(self, state: AgentState) -> AgentState:
        """Store raw goal and transition to constraint extraction."""
        state.memory_context["raw_goal"] = state.user_goal
        state.current_phase = StatePhase.CONSTRAIN
        state.ledger.append(
            LedgerEntry(
                agent="supervisor",
                action="goal_received",
                details={"goal": state.user_goal},
            )
        )
        return state

    async def extract_constraints(self, state: AgentState) -> AgentState:
        """Extract structured constraints using the SupervisorAgent."""
        if self._supervisor is not None:
            try:
                interpreted = await self._supervisor.interpret_goal(
                    state.user_goal, state.constraints
                )
                state.memory_context["interpreted_goal"] = interpreted
                extracted = interpreted.get("constraints_dict", {})
                if extracted:
                    state.constraints.update(extracted)
                state.memory_context["required_capabilities"] = interpreted.get(
                    "required_capabilities", []
                )
                state.memory_context["suggested_plan_type"] = interpreted.get(
                    "suggested_plan_type", "sequential"
                )
            except Exception:
                state.memory_context["interpreted_goal"] = {
                    "goal_summary": state.user_goal,
                }

        state.current_phase = StatePhase.PLANNING
        state.ledger.append(
            LedgerEntry(
                agent="supervisor",
                action="constraint_extraction",
                details={"constraints": state.constraints},
            )
        )
        return state

    async def plan_tasks(self, state: AgentState) -> AgentState:
        """Decompose the goal into task definitions using the PlannerAgent."""
        interpreted = state.memory_context.get("interpreted_goal", {})
        available_tools = []
        if self._tool_registry is not None:
            try:
                available_tools = self._tool_registry.discover_tools()
            except Exception:
                available_tools = []
        memory_ctx = state.memory_context.get("learning_context", {})

        tasks: dict[str, dict] = {}
        if self._planner is not None:
            try:
                planner_tasks, _ = await self._planner.create_plan(
                    goal=interpreted,
                    available_tools=available_tools,
                    memory_context=memory_ctx,
                )
                tasks = planner_tasks
            except Exception:
                tasks = {}

        if not tasks:
            tasks = {
                "default_task": {
                    "agent_type": "worker",
                    "dependencies": [],
                    "input": {"action": "process", "goal": state.user_goal},
                    "description": f"Process goal: {state.user_goal}",
                }
            }

        state.memory_context["planner_tasks"] = tasks
        state.current_phase = StatePhase.BUILD_DAG
        state.ledger.append(
            LedgerEntry(
                agent="planner",
                action="plan_created",
                details={"task_count": len(tasks)},
            )
        )
        return state

    async def build_dag(self, state: AgentState) -> AgentState:
        """Build the execution DAG from the planner's output.

        Delegates to :class:`DependencyGraphBuilder` and stores the result
        in ``state.execution_graph``.
        """
        # Consume planner_tasks if available; fall back to extracting from state.
        tasks: dict[str, dict] = state.memory_context.pop("planner_tasks", {})
        if not tasks:
            tasks = self._extract_tasks_from_state(state)
        if not tasks:
            tasks = {
                "root": {
                    "agent_type": "worker",
                    "description": f"Process goal: {state.user_goal}",
                    "dependencies": [],
                    "input": {"goal": state.user_goal},
                }
            }

        try:
            graph = self._builder.build(tasks)
        except Exception as exc:
            state.current_phase = StatePhase.END
            state.ledger.append(
                LedgerEntry(
                    agent="planner",
                    action="build_dag_failed",
                    details={"error": str(exc)},
                )
            )
            return state

        state.execution_graph = graph
        state.current_phase = StatePhase.SCHEDULE
        state.ledger.append(
            LedgerEntry(
                agent="planner",
                action="build_dag",
                details={
                    "node_count": len(graph.nodes),
                    "edge_count": len(graph.edges),
                },
            )
        )
        return state

    async def schedule_tasks(self, state: AgentState) -> AgentState:
        """Compute the execution schedule.

        Delegates to :class:`TaskScheduler.schedule`.
        """
        graph = state.execution_graph
        if not graph.nodes:
            state.current_phase = StatePhase.APPROVAL
            return state

        groups = await self._scheduler.schedule(graph, state)

        # Store groups in ``memory_context`` for the executor.
        state.memory_context["parallel_groups"] = groups
        state.current_phase = StatePhase.RISK_ANALYSIS
        state.ledger.append(
            LedgerEntry(
                agent="scheduler",
                action="schedule",
                details={
                    "group_count": len(groups),
                    "task_count": len(graph.nodes),
                },
            )
        )
        return state

    async def parallel_execute(self, state: AgentState) -> AgentState:
        """Execute all parallel groups.

        Delegates to :class:`ParallelExecutor.execute_full_graph`.
        """
        updated_state = await self._executor.execute_full_graph(state)
        state = updated_state
        state.current_phase = StatePhase.EVALUATE
        return state

    async def risk_analysis(self, state: AgentState) -> AgentState:
        """Assess risk for every task in the execution graph.

        Uses :class:`RiskPredictor` and stores ``risk_assessment`` on each
        :class:`TaskNode`.  Tasks with ``requires_approval`` get an
        :class:`ApprovalRequest` enqueued.
        """
        if self._risk_predictor is not None:
            for task_id, node in state.execution_graph.nodes.items():
                try:
                    assessment = await self._risk_predictor.assess_task(node)
                    node.risk_assessment = assessment
                except Exception:
                    continue

        state.current_phase = StatePhase.TOOL_SELECT
        state.ledger.append(
            LedgerEntry(
                agent="risk_predictor",
                action="risk_analysis_complete",
                details={"tasks_assessed": len(state.execution_graph.nodes)},
            )
        )
        return state

    async def select_tools(self, state: AgentState) -> AgentState:
        """Select the best tool for each task from the Tool Marketplace.

        Uses :class:`ToolRegistry` and sets ``model_assigned`` on each
        :class:`TaskNode`.
        """
        if self._tool_registry is not None:
            for task_id, node in state.execution_graph.nodes.items():
                action = (node.input.get("action") or node.input.get("tool") or "").lower()
                category = self._infer_tool_category(action)
                try:
                    best = self._tool_registry.get_best_tool(category)
                    node.model_assigned = best
                except (KeyError, ValueError):
                    node.model_assigned = None

        state.current_phase = StatePhase.EXECUTE
        state.ledger.append(
            LedgerEntry(
                agent="tool_marketplace",
                action="tool_selection_complete",
                details={
                    "assignments": {
                        tid: state.execution_graph.nodes[tid].model_assigned
                        for tid in state.execution_graph.nodes
                    },
                },
            )
        )
        return state

    @staticmethod
    def _infer_tool_category(action: str):
        """Map an action string to a :class:`ToolCategory`."""
        from src.core.constants import ToolCategory

        mapping = {
            "flight": ToolCategory.FLIGHT,
            "fly": ToolCategory.FLIGHT,
            "travel": ToolCategory.TRANSPORT,
            "train": ToolCategory.TRANSPORT,
            "hotel": ToolCategory.HOTEL,
            "stay": ToolCategory.HOTEL,
            "weather": ToolCategory.WEATHER,
            "budget": ToolCategory.BUDGET,
            "cost": ToolCategory.BUDGET,
            "email": ToolCategory.EMAIL,
            "mail": ToolCategory.EMAIL,
            "search": ToolCategory.SEARCH,
        }
        for keyword, cat in mapping.items():
            if keyword in action:
                return cat
        return ToolCategory.GENERAL

    async def evaluate(self, state: AgentState) -> AgentState:
        """Evaluate execution results and decide if replanning is needed.

        Uses :class:`EvaluatorAgent` when available; otherwise falls back
        to checking for ``FAILED`` tasks in the graph.
        """
        graph = state.execution_graph

        if self._evaluator is not None:
            try:
                score = await self._evaluator.evaluate(state)
                state.memory_context["_eval_score"] = score.overall
                decision = await self._evaluator.decide_replan(state, score)
                needs_replan = decision.needs_replan
                state.memory_context["_eval_reasoning"] = decision.reason
            except Exception:
                needs_replan = any(
                    node.status == TaskStatus.FAILED for node in graph.nodes.values()
                ) or len(state.errors) > 0
        else:
            needs_replan = any(
                node.status == TaskStatus.FAILED for node in graph.nodes.values()
            ) or len(state.errors) > 0

        state.memory_context["_needs_replan"] = needs_replan

        if needs_replan:
            state.current_phase = StatePhase.REPLAN
            state.ledger.append(
                LedgerEntry(
                    agent="evaluator",
                    action="replan_needed",
                    details={
                        "failed_tasks": [
                            tid
                            for tid, n in graph.nodes.items()
                            if n.status == TaskStatus.FAILED
                        ],
                        "error_count": len(state.errors),
                    },
                )
            )
        else:
            state.current_phase = StatePhase.APPROVAL
            state.ledger.append(
                LedgerEntry(
                    agent="evaluator",
                    action="evaluation_passed",
                    details={"task_count": len(graph.nodes)},
                )
            )

        return state

    async def decide_replan(self, state: AgentState) -> AgentState:
        """Check whether the replan limit has been reached.

        If ``_replan_count`` is below ``MAX_REPLAN_ATTEMPTS`` the counter
        is incremented and ``_needs_replan`` stays ``True``.
        Otherwise ``_needs_replan`` is forced to ``False`` and an error
        is logged.
        """
        max_attempts = self._settings.MAX_REPLAN_ATTEMPTS
        replan_count = state.memory_context.get("_replan_count", 0)

        if replan_count < max_attempts:
            state.memory_context["_replan_count"] = replan_count + 1
            state.current_phase = StatePhase.PLANNING
            state.ledger.append(
                LedgerEntry(
                    agent="orchestrator",
                    action="replan_accepted",
                    details={
                        "attempt": replan_count + 1,
                        "max_attempts": max_attempts,
                    },
                )
            )
        else:
            # Replan limit reached — bail out to approval.
            state.memory_context["_needs_replan"] = False
            state.current_phase = StatePhase.APPROVAL
            state.errors.append(
                MaxReplanAttemptsError(
                    attempts=replan_count,
                    max_attempts=max_attempts,
                )
            )
            state.ledger.append(
                LedgerEntry(
                    agent="orchestrator",
                    action="replan_limit_reached",
                    details={
                        "attempts": replan_count,
                        "max_attempts": max_attempts,
                    },
                )
            )

        return state

    async def update_dag(self, state: AgentState) -> AgentState:
        """Mutate the graph in response to a failure.

        Delegates to :class:`AdaptiveExecutionGraph.mutate_on_failure`.

        Uses the first ``FAILED`` task found in the graph as the
        ``failed_task_id`` and generates a simple retry task.
        """
        graph = state.execution_graph
        if not graph.nodes:
            state.current_phase = StatePhase.APPROVAL
            return state

        # Find the first FAILED task.
        failed_id: str | None = None
        for tid, node in graph.nodes.items():
            if node.status == TaskStatus.FAILED:
                failed_id = tid
                break

        if failed_id is None:
            # Nothing to replan — move on.
            state.memory_context["_needs_replan"] = False
            state.current_phase = StatePhase.APPROVAL
            return state

        adaptive = AdaptiveExecutionGraph(graph)

        # Build a replacement task.  In production the planner would be
        # consulted here.  For now we create a copy with ``PENDING`` status.
        failed_node = graph.nodes[failed_id]
        replacement_id = f"{failed_id}_retry_{state.memory_context.get('_replan_count', 1)}"
        new_tasks: dict[str, dict] = {
            replacement_id: {
                "agent_type": failed_node.agent_type,
                "description": f"Retry: {failed_node.input}",
                "dependencies": graph.get_dependencies(failed_id),
                "input": failed_node.input,
            },
        }

        adaptive.mutate_on_failure(failed_id, new_tasks)
        state.execution_graph = adaptive.graph
        state.current_phase = StatePhase.PLANNING

        state.ledger.append(
            LedgerEntry(
                agent="orchestrator",
                action="dag_mutated",
                details={
                    "removed_task": failed_id,
                    "added_task": replacement_id,
                    "node_count": len(graph.nodes),
                },
            )
        )

        return state

    async def approval(self, state: AgentState) -> AgentState:
        """Handle the human-approval gate.

        If any items are in ``approval_queue`` the machine pauses
        for human response.  Otherwise auto-approves.
        """
        pending = [a for a in state.approval_queue if a.status == "pending"]

        if pending:
            from src.approval.approval_gate import ApprovalGate

            gate = ApprovalGate(timeout_seconds=self._settings.APPROVAL_TIMEOUT_SECONDS)
            for req in pending:
                result = await gate.request_approval(
                    task_id=req.task_id,
                    action_description=req.action_description,
                    risk_assessment=req.risk_assessment,
                    session_id=state.session_id,
                    timeout_seconds=self._settings.APPROVAL_TIMEOUT_SECONDS,
                )
                req.status = result.status
                req.responded_at = result.responded_at

            state.ledger.append(
                LedgerEntry(
                    agent="orchestrator",
                    action="approval_processed",
                    details={
                        "count": len(pending),
                        "statuses": {r.id: r.status for r in pending},
                    },
                )
            )

        state.current_phase = StatePhase.SUMMARY
        return state

    async def summary(self, state: AgentState) -> AgentState:
        """Generate a final summary of the execution.

        Delegates to the Evaluator agent in production.
        """
        graph = state.execution_graph
        completed = sum(
            1 for n in graph.nodes.values() if n.status == TaskStatus.COMPLETED
        )
        failed = sum(
            1 for n in graph.nodes.values() if n.status == TaskStatus.FAILED
        )
        skipped = sum(
            1 for n in graph.nodes.values() if n.status == TaskStatus.SKIPPED
        )
        total = len(graph.nodes)

        summary_parts = [
            f"Goal: {state.user_goal}",
            f"Total tasks: {total}",
            f"Completed: {completed}",
            f"Failed: {failed}",
            f"Skipped: {skipped}",
        ]
        if state.errors:
            summary_parts.append(f"Errors: {len(state.errors)}")

        state.final_summary = " | ".join(summary_parts)
        state.current_phase = StatePhase.MEMORY_STORE

        state.ledger.append(
            LedgerEntry(
                agent="orchestrator",
                action="summary_generated",
                details={
                    "total_tasks": total,
                    "completed": completed,
                    "failed": failed,
                    "skipped": skipped,
                    "error_count": len(state.errors),
                    "summary": state.final_summary,
                },
            )
        )

        return state

    async def store_memory(self, state: AgentState) -> AgentState:
        """Store execution patterns in LearningMemory after successful completion."""
        if self._learning_memory is not None:
            try:
                success = state.execution_graph.status == GraphStatus.COMPLETED
                score = state.memory_context.get("_eval_score")
                await self._learning_memory.save_plan(
                    goal=state.user_goal,
                    graph_snapshot=state.execution_graph.model_dump(mode="json"),
                    success=success,
                    score=score,
                    session_id=state.session_id,
                )
            except Exception:
                pass

        state.current_phase = StatePhase.END
        state.ledger.append(
            LedgerEntry(
                agent="learning_memory",
                action="patterns_stored",
                details={"plan_saved": self._learning_memory is not None},
            )
        )
        return state

    async def end(self, state: AgentState) -> AgentState:
        """Terminal state.  Mark execution as complete."""
        state.current_phase = StatePhase.END
        state.ledger.append(
            LedgerEntry(
                agent="orchestrator",
                action="execution_complete",
                details={"final_summary": state.final_summary},
            )
        )
        return state

    # ------------------------------------------------------------------
    # LangGraph node adapters
    # ------------------------------------------------------------------

    async def _node_understand_goal(self, state: AgentState) -> dict[str, Any]:
        result = await self.understand_goal(state)
        return self._state_to_updates(result)

    async def _node_build_dag(self, state: AgentState) -> dict[str, Any]:
        result = await self.build_dag(state)
        return self._state_to_updates(result)

    async def _node_schedule_tasks(self, state: AgentState) -> dict[str, Any]:
        result = await self.schedule_tasks(state)
        return self._state_to_updates(result)

    async def _node_parallel_execute(self, state: AgentState) -> dict[str, Any]:
        result = await self.parallel_execute(state)
        return self._state_to_updates(result)

    async def _node_evaluate(self, state: AgentState) -> dict[str, Any]:
        result = await self.evaluate(state)
        return self._state_to_updates(result)

    async def _node_decide_replan(self, state: AgentState) -> dict[str, Any]:
        result = await self.decide_replan(state)
        return self._state_to_updates(result)

    async def _node_update_dag(self, state: AgentState) -> dict[str, Any]:
        result = await self.update_dag(state)
        return self._state_to_updates(result)

    async def _node_approval(self, state: AgentState) -> dict[str, Any]:
        result = await self.approval(state)
        return self._state_to_updates(result)

    async def _node_summary(self, state: AgentState) -> dict[str, Any]:
        result = await self.summary(state)
        return self._state_to_updates(result)

    async def _node_end(self, state: AgentState) -> dict[str, Any]:
        result = await self.end(state)
        return self._state_to_updates(result)

    # -- New node adapters -------------------------------------------------
    async def _node_extract_constraints(self, state: AgentState) -> dict[str, Any]:
        result = await self.extract_constraints(state)
        return self._state_to_updates(result)

    async def _node_plan_tasks(self, state: AgentState) -> dict[str, Any]:
        result = await self.plan_tasks(state)
        return self._state_to_updates(result)

    async def _node_risk_analysis(self, state: AgentState) -> dict[str, Any]:
        result = await self.risk_analysis(state)
        return self._state_to_updates(result)

    async def _node_select_tools(self, state: AgentState) -> dict[str, Any]:
        result = await self.select_tools(state)
        return self._state_to_updates(result)

    async def _node_store_memory(self, state: AgentState) -> dict[str, Any]:
        result = await self.store_memory(state)
        return self._state_to_updates(result)

    # ------------------------------------------------------------------
    # Conditional routing
    # ------------------------------------------------------------------

    @staticmethod
    def _route_after_evaluate(state: AgentState) -> str:
        """Return ``"replan"`` or ``"continue"`` based on evaluation."""
        if state.memory_context.get("_needs_replan", False):
            return "replan"
        return "continue"

    @staticmethod
    def _route_after_replan_decision(state: AgentState) -> str:
        """Return ``"update_dag"`` or ``"approval"``."""
        if state.memory_context.get("_needs_replan", False):
            return "update_dag"
        return "approval"

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _state_to_updates(state: AgentState) -> dict[str, Any]:
        """Convert an ``AgentState`` back to a dict of top-level field
        updates suitable for LangGraph's state-merge logic.

        This preserves the Pydantic model fields so the next node sees
        the mutations from the previous one.
        """
        return {
            "current_phase": state.current_phase,
            "execution_graph": state.execution_graph,
            "ledger": state.ledger,
            "approval_queue": state.approval_queue,
            "memory_context": state.memory_context,
            "errors": state.errors,
            "final_summary": state.final_summary,
        }

    @staticmethod
    def _extract_tasks_from_state(state: AgentState) -> dict[str, dict]:
        """Convert existing ``TaskNode`` objects inside
        ``state.execution_graph`` back to the raw ``dict[str, dict]``
        format expected by :meth:`DependencyGraphBuilder.build`.

        This is useful when the graph has already been partially
        populated (e.g. after a replan mutation).
        """
        tasks: dict[str, dict] = {}
        for tid, node in state.execution_graph.nodes.items():
            tasks[tid] = {
                "agent_type": node.agent_type,
                "dependencies": node.dependencies,
                "input": node.input,
                "model_assigned": node.model_assigned,
            }
        return tasks


# ===========================================================================
# Placeholder agent (used when no real worker is injected)
# ===========================================================================


class _PlaceholderAgent:
    """Minimal worker that returns a successful result with no data.

    Used as a default when the caller does not provide a ``ParallelExecutor``
    with a real agent.
    """

    async def execute(
        self,
        task_id: str,
        state: Any,
        tool_registry: Any = None,
    ) -> "ExecutionResult":
        from src.engine.parallel_executor import ExecutionResult

        return ExecutionResult(
            task_id=task_id,
            success=True,
            data={"message": f"Placeholder executed {task_id}"},
            tool_used=None,
        )
