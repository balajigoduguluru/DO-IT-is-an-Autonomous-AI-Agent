"""Supervisor agent — owns session state, orchestrates execution flow.

The Supervisor NEVER calls external tools directly.  It interprets user
goals, decides phase transitions, and generates summaries — all via LLM
calls.  Delegates task-level work to Planner, Worker, and Evaluator agents.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

from openai import AsyncOpenAI

from src.core.config import settings
from src.core.constants import MAX_RETRIES, StatePhase
from src.core.models import AgentState


class SupervisorAgent:
    """Orchestrator that owns the AgentState and drives the execution loop.

    The supervisor is the top-level agent.  It never invokes external tools
    (APIs, databases, etc.) directly; that responsibility belongs to the
    Worker.  Instead it focuses on:

    - Parsing the user's natural-language goal into a structured plan request.
    - Examining the current AgentState and deciding which phase to transition
      to next.
    - Producing a final human-readable summary once execution is complete.
    """

    def __init__(
        self,
        model: str | None = None,
        api_key: str | None = None,
        base_url: str | None = None,
    ) -> None:
        """Configure the supervisor.

        Args:
            model: OpenAI-compatible model name (default: from settings).
            api_key: API key (default: from settings).
            base_url: Custom OpenAI-compatible endpoint (optional).
        """
        self.model = model or settings.OPENAI_MODEL_PRIMARY
        self._client = AsyncOpenAI(
            api_key=api_key or settings.OPENAI_API_KEY,
            base_url=base_url,
        )

    # ------------------------------------------------------------------
    # LLM helper  (retry with exponential backoff)
    # ------------------------------------------------------------------

    async def _call_llm(
        self,
        messages: list[dict[str, Any]],
        response_format: dict[str, Any] | None = None,
        temperature: float = 0.1,
    ) -> dict[str, Any]:
        """Send a chat-completion request and parse the JSON response.

        Retries up to ``MAX_RETRIES`` times with exponential backoff.

        Raises:
            RuntimeError: If all retry attempts are exhausted.
        """
        last_error: Exception | None = None

        for attempt in range(MAX_RETRIES):
            try:
                kwargs: dict[str, Any] = {
                    "model": self.model,
                    "messages": messages,
                    "temperature": temperature,
                }
                if response_format is not None:
                    kwargs["response_format"] = response_format

                response = await self._client.chat.completions.create(**kwargs)
                content = response.choices[0].message.content
                if content is None or content.strip() == "":
                    return {}
                return json.loads(content)

            except json.JSONDecodeError as exc:
                last_error = exc
                if attempt < MAX_RETRIES - 1:
                    await asyncio.sleep(2**attempt)

            except Exception as exc:
                last_error = exc
                if attempt < MAX_RETRIES - 1:
                    await asyncio.sleep(2**attempt)

        raise RuntimeError(
            f"LLM call failed after {MAX_RETRIES} attempts"
        ) from last_error

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def interpret_goal(
        self,
        user_goal: str,
        constraints: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Parse the user's natural-language goal into a structured dict.

        Uses an LLM call to extract key parameters such as destination,
        budget, dates, and required capabilities.

        Args:
            user_goal: Raw natural-language goal from the user.
            constraints: Optional hard constraints (budget limit, date
                range, location, etc.).

        Returns:
            A dict with keys ``goal_summary``, ``required_capabilities``
            (list), ``constraints_dict``, ``suggested_plan_type``, and
            ``key_parameters``.
        """
        system_prompt = (
            "You are a goal interpreter for an AI agent orchestration system. "
            "Extract structured information from the user's natural language goal. "
            "Return ONLY valid JSON. Never include any additional text."
        )

        constraints_text = ""
        if constraints:
            constraints_text = (
                f"\nExplicit constraints: {json.dumps(constraints, indent=2)}"
            )

        user_message = (
            f"Parse this user goal and extract key information:\n\n"
            f"Goal: {user_goal}{constraints_text}\n\n"
            "Return a JSON object with exactly these fields:\n"
            '- "goal_summary": string\n'
            '- "required_capabilities": list of strings\n'
            '- "constraints_dict": object\n'
            '- "suggested_plan_type": "sequential" | "parallel" | "hybrid"\n'
            '- "key_parameters": object'
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ]

        return await self._call_llm(
            messages,
            response_format={"type": "json_object"},
        )

    async def decide_next_phase(self, state: AgentState) -> StatePhase:
        """Examine the current :class:`AgentState` and return the next phase.

        Uses an LLM to choose the appropriate :class:`StatePhase` based on
        the current phase, graph status, task counts, and errors.

        Falls back to a deterministic rule-based state machine if the LLM
        call fails.

        Args:
            state: The current session state snapshot.

        Returns:
            The next :class:`StatePhase` to transition to.
        """
        state_context = self._format_state_context(state)

        system_prompt = (
            "You are a phase transition manager for an AI agent orchestration system. "
            "Based on the current state context, decide the next phase. "
            "Return ONLY valid JSON."
        )

        user_message = (
            f"Current state:\n{state_context}\n\n"
            "Decide the next phase. Choose one from:\n"
            "UNDERSTAND_GOAL, BUILD_DAG, SCHEDULE, EXECUTE, EVALUATE, "
            "REPLAN, APPROVAL, SUMMARY, END\n\n"
            'Return JSON: {"next_phase": "<PHASE>", "reasoning": "<brief explanation>"}'
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ]

        # Try LLM first; fall back to rule-based if LLM unavailable
        try:
            result = await self._call_llm(
                messages,
                response_format={"type": "json_object"},
            )
            phase_str = result.get("next_phase", "")
            if phase_str:
                return StatePhase(phase_str)
        except (RuntimeError, ValueError, KeyError):
            pass

        return self._rule_based_phase(state)

    async def generate_summary(self, state: AgentState) -> str:
        """Generate a human-readable final summary from execution results.

        Uses an LLM to produce a concise summary of what was accomplished.
        Falls back to a template summary if the LLM call fails.

        Args:
            state: The (typically completed) session state.

        Returns:
            A plain-text summary string.
        """
        tasks_summary = self._format_tasks_summary(state)

        system_prompt = (
            "You are a summary generator for an AI agent orchestration system. "
            "Create a concise, human-readable summary of the execution results."
        )

        user_message = (
            f"Original goal: {state.user_goal}\n\n"
            f"Graph status: {state.execution_graph.status.value}\n"
            f"Total tasks: {len(state.execution_graph.nodes)}\n\n"
            f"Tasks:\n{tasks_summary}\n\n"
            "Create a brief, clear summary of what was accomplished. "
            "Highlight any failures or issues encountered."
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ]

        try:
            result = await self._call_llm(messages, temperature=0.3)
            if isinstance(result, dict):
                return result.get("summary", str(result))
            return str(result)
        except RuntimeError:
            return self._template_summary(state)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _format_state_context(state: AgentState) -> str:
        """Compact text representation of the state for the LLM."""
        task_count = len(state.execution_graph.nodes)
        completed = sum(
            1 for n in state.execution_graph.nodes.values()
            if n.status.value == "COMPLETED"
        )
        failed = sum(
            1 for n in state.execution_graph.nodes.values()
            if n.status.value == "FAILED"
        )
        running = sum(
            1 for n in state.execution_graph.nodes.values()
            if n.status.value == "RUNNING"
        )

        return (
            f"Current phase: {state.current_phase.value}\n"
            f"Graph status: {state.execution_graph.status.value}\n"
            f"Tasks: {task_count} total ({completed} completed, "
            f"{running} running, {failed} failed)\n"
            f"Errors logged: {len(state.errors)}\n"
            f"Summary already set: {'yes' if state.final_summary else 'no'}"
        )

    @staticmethod
    def _format_tasks_summary(state: AgentState) -> str:
        """Build a text summary of all tasks for the LLM."""
        lines: list[str] = []
        for task_id, node in state.execution_graph.nodes.items():
            status = node.status.value
            deps = ", ".join(node.dependencies) if node.dependencies else "none"
            output_preview = ""
            if node.output:
                try:
                    out = json.dumps(node.output, indent=2)
                    output_preview = out[:200]
                except (TypeError, ValueError):
                    output_preview = str(node.output)[:200]
            lines.append(
                f"  - [{status}] {task_id} (deps: {deps})"
                f"{'  Output: ' + output_preview if output_preview else ''}"
            )
        return "\n".join(lines)

    @staticmethod
    def _rule_based_phase(state: AgentState) -> StatePhase:
        """Deterministic fallback for phase transitions when LLM is down."""
        graph = state.execution_graph
        current = state.current_phase

        if current == StatePhase.UNDERSTAND_GOAL:
            return StatePhase.BUILD_DAG

        if current == StatePhase.BUILD_DAG:
            return StatePhase.SCHEDULE

        if current == StatePhase.SCHEDULE:
            return (
                StatePhase.EXECUTE
                if graph.nodes
                else StatePhase.END
            )

        if current == StatePhase.EXECUTE:
            statuses = {n.status for n in graph.nodes.values()}
            terminal = {"COMPLETED", "FAILED", "SKIPPED"}
            if statuses.issubset(terminal):
                return StatePhase.EVALUATE
            return StatePhase.EXECUTE

        if current == StatePhase.EVALUATE:
            has_failures = any(
                n.status.value == "FAILED" for n in graph.nodes.values()
            )
            if has_failures:
                return StatePhase.REPLAN
            return StatePhase.SUMMARY

        if current == StatePhase.REPLAN:
            return StatePhase.SCHEDULE

        if current == StatePhase.SUMMARY:
            return StatePhase.END

        return StatePhase.END

    @staticmethod
    def _template_summary(state: AgentState) -> str:
        """Fallback template when the LLM call fails."""
        completed = [
            tid for tid, n in state.execution_graph.nodes.items()
            if n.status.value == "COMPLETED"
        ]
        failed = [
            tid for tid, n in state.execution_graph.nodes.items()
            if n.status.value == "FAILED"
        ]

        parts = [f"Execution complete for goal: {state.user_goal}"]
        if completed:
            parts.append(f"Completed tasks: {', '.join(completed)}")
        if failed:
            parts.append(f"Failed tasks: {', '.join(failed)}")
        if state.errors:
            parts.append(f"Total errors: {len(state.errors)}")
        return ". ".join(parts) + "."
