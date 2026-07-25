"""Planner agent — decomposes goals into a task dependency graph and execution order.

The Planner uses an LLM to:

1. Decompose a high-level goal into discrete subtasks.
2. Identify dependencies between those subtasks.
3. Organise them into groups that can execute in parallel.

It also supports replanning when a task fails, suggesting alternative
approaches (e.g. train instead of flight).
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

from openai import AsyncOpenAI

from src.core.config import settings
from src.core.constants import MAX_RETRIES
from src.core.models import AgentState


class PlannerAgent:
    """Creates and manages the task dependency graph and execution order.

    The planner does **not** execute tasks.  It only produces a plan
    (a set of :class:`TaskNode` definitions and an execution order) that
    the main loop uses to schedule work.
    """

    def __init__(
        self,
        model: str | None = None,
        api_key: str | None = None,
        base_url: str | None = None,
    ) -> None:
        """Configure the planner.

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

    async def create_plan(
        self,
        goal: dict[str, Any],
        available_tools: list[str],
        memory_context: dict[str, Any] | None = None,
    ) -> tuple[dict[str, Any], list[list[str]]]:
        """Decompose a goal into subtasks and produce an execution order.

        Uses an LLM to inspect the interpreted goal, available tool names,
        and any relevant memory context, then returns:

        - ``tasks``: A dict mapping task IDs to task definitions (each
          definition contains ``id``, ``agent_type``, ``dependencies``, and
          ``input`` fields).
        - ``execution_order``: A list of lists, where each inner list
          contains task IDs that can be executed in parallel.

        Args:
            goal: The interpreted goal dict from
                :meth:`SupervisorAgent.interpret_goal`.
            available_tools: List of tool names that can be used.
            memory_context: Optional dict from past session memory.

        Returns:
            A ``(tasks, execution_order)`` tuple.
        """
        system_prompt = (
            "You are a task planner for an AI agent orchestration system. "
            "Decompose the given goal into subtasks and organise them in a "
            "dependency graph for parallel execution. "
            "Return ONLY valid JSON."
        )

        tools_str = ", ".join(available_tools) if available_tools else (
            "No tools specified — assume generic capabilities"
        )
        memory_str = (
            json.dumps(memory_context, indent=2)
            if memory_context
            else "No prior context"
        )

        user_message = (
            f"Goal: {json.dumps(goal, indent=2)}\n"
            f"Available tools: [{tools_str}]\n"
            f"Memory context: {memory_str}\n\n"
            "Create a plan. Return a JSON object with exactly:\n"
            '- "tasks": object where keys are task IDs and values are objects with:\n'
            "    - id: string (same as key)\n"
            '    - agent_type: "worker"\n'
            "    - dependencies: list of task ID strings this task depends on\n"
            "    - input: object with tool name and parameters\n"
            "    - description: string\n"
            '- "execution_order": list of lists — each inner list holds task IDs that can run in parallel\n'
            '- "reasoning": string explaining the decomposition'
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ]

        result = await self._call_llm(
            messages,
            response_format={"type": "json_object"},
        )

        tasks: dict[str, Any] = result.get("tasks", {})
        execution_order: list[list[str]] = result.get("execution_order", [])

        # Validate format — if the LLM returned a flat list, wrap each
        # item so callers always get `list[list[str]]`.
        if execution_order and isinstance(execution_order[0], str):
            execution_order = [[tid] for tid in execution_order]

        # If LLM gave us nothing, build a minimal fallback
        if not tasks:
            tasks = {
                "default_task": {
                    "id": "default_task",
                    "agent_type": "worker",
                    "dependencies": [],
                    "input": goal,
                    "description": "Fallback single task from goal",
                }
            }
            execution_order = [["default_task"]]

        return tasks, execution_order

    async def replan(
        self,
        failed_task: dict[str, Any],
        error: str,
        state: AgentState,
    ) -> dict[str, Any]:
        """Suggest an alternative approach for a failed task.

        Examines the failed task definition, the error message, and the
        current state to produce a set of modified task definitions that
        replace or augment the affected subgraph.

        Args:
            failed_task: The original task definition that failed (dict).
            error: The error message from the failure.
            state: The current session state (read-only).

        Returns:
            A dict mapping task IDs to modified task definitions for the
            affected subgraph (same format as *tasks* from
            :meth:`create_plan`).
        """
        system_prompt = (
            "You are a replanning agent. A task has failed and you need "
            "to suggest alternative approaches. Think about what alternative "
            "tools or strategies could be used instead. Return ONLY valid JSON."
        )

        # Summarise the current graph for context
        existing_nodes = {
            tid: {
                "id": node.id,
                "agent_type": node.agent_type,
                "status": node.status.value,
                "dependencies": node.dependencies,
            }
            for tid, node in state.execution_graph.nodes.items()
        }

        user_message = (
            f"Failed task definition:\n{json.dumps(failed_task, indent=2)}\n"
            f"Error message: {error}\n\n"
            f"Existing tasks in graph:\n{json.dumps(existing_nodes, indent=2)}\n\n"
            "Suggest modifications. Return JSON with:\n"
            '- "modified_tasks": object of new/updated task definitions '
            "(same format as 'tasks' in create_plan)\n"
            '- "execution_order": list of lists (parallel groups) for the affected subgraph\n'
            '- "reasoning": string explaining what changed and why'
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ]

        try:
            result = await self._call_llm(
                messages,
                response_format={"type": "json_object"},
            )
        except RuntimeError:
            # Fallback: return an empty dict (caller should handle)
            return {}

        return result.get("modified_tasks", {})
