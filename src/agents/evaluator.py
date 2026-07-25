"""Evaluator agent — scores execution results and decides if replanning is needed.

The Evaluator is responsible for:

1. **Scoring** the current state against the original goal across three
   axes: correctness, completeness, and safety.
2. **Deciding** whether replanning is required — but only for failed or
   affected tasks, never the entire plan wholesale.

Replanning is bounded by :data:`MAX_REPLAN_ATTEMPTS <src.core.config.Settings.MAX_REPLAN_ATTEMPTS>`.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

from openai import AsyncOpenAI

from src.core.config import settings
from src.core.constants import MAX_RETRIES
from src.core.models import AgentState, EvalScore, ReplanDecision


class EvaluatorAgent:
    """Scores execution results and decides whether replanning is needed.

    The evaluator is purely observational — it **never** mutates state or
    executes tools.  It reads the current :class:`AgentState` and returns
    scores / decisions.
    """

    def __init__(
        self,
        model: str | None = None,
        api_key: str | None = None,
        base_url: str | None = None,
    ) -> None:
        """Configure the evaluator.

        Args:
            model: OpenAI-compatible model name (default uses the mini
                model from settings so it costs less than primary).
            api_key: API key (default: from settings).
            base_url: Custom OpenAI-compatible endpoint (optional).
        """
        self.model = model or settings.OPENAI_MODEL_MINI
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

    async def evaluate(self, state: AgentState) -> EvalScore:
        """Score the current execution against the original goal.

        Uses an LLM to evaluate correctness, completeness, and safety
        based on the original user goal, the interpreted goal, the task
        results, and any errors.

        Falls back to a heuristic score if the LLM call fails.

        Args:
            state: The current session state (typically after EXECUTE).

        Returns:
            An :class:`EvalScore` with scores in ``[0.0, 1.0]`` and a
            reasoning string.
        """
        tasks_summary = self._format_tasks_for_eval(state)

        system_prompt = (
            "You are an evaluator for an AI agent orchestration system. "
            "Score the execution results against the original goal. "
            "Return ONLY valid JSON."
        )

        user_message = (
            f"Original goal: {state.user_goal}\n"
            f"Constraints: {json.dumps(state.constraints, indent=2)}\n"
            f"Graph status: {state.execution_graph.status.value}\n"
            f"Phase: {state.current_phase.value}\n\n"
            f"Tasks:\n{tasks_summary}\n\n"
            f"Errors logged: {len(state.errors)}\n"
            f"{self._format_errors(state)}\n\n"
            "Return a JSON object with:\n"
            '- "correctness": float 0.0-1.0 (did the results address the goal?)\n'
            '- "completeness": float 0.0-1.0 (were all aspects covered?)\n'
            '- "safety": float 0.0-1.0 (were there harmful side effects?)\n'
            '- "overall": float 0.0-1.0 (overall quality)\n'
            '- "reasoning": string explaining the scores'
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

            return EvalScore(
                correctness=float(result.get("correctness", 0.0)),
                completeness=float(result.get("completeness", 0.0)),
                safety=float(result.get("safety", 1.0)),
                overall=float(result.get("overall", 0.0)),
                reasoning=result.get("reasoning", ""),
            )

        except RuntimeError:
            return self._heuristic_score(state)

        except (ValueError, TypeError) as exc:
            # Score validation failed (e.g. out of range) — fall back
            score = self._heuristic_score(state)
            score.reasoning = f"LLM returned invalid scores; using heuristic. ({exc})"
            return score

    async def decide_replan(
        self,
        state: AgentState,
        score: EvalScore,
    ) -> ReplanDecision:
        """Decide whether replanning is needed and which tasks to replan.

        Only tasks that have **failed** are candidates for replanning.
        The decision is bounded by :attr:`MAX_REPLAN_ATTEMPTS` from
        :class:`~src.core.config.Settings`.

        Args:
            state: The current session state.
            score: The :class:`EvalScore` returned by :meth:`evaluate`.

        Returns:
            A :class:`ReplanDecision` specifying whether replanning is
            needed and which task IDs are affected.
        """
        max_replan = settings.MAX_REPLAN_ATTEMPTS

        # ---- Bounded check ------------------------------------------------
        # Count replans that have already happened via the ledger.
        replan_count = sum(
            1 for entry in state.ledger if entry.action == "replan"
        )
        if replan_count >= max_replan:
            return ReplanDecision(
                needs_replan=False,
                affected_task_ids=[],
                reason=f"Maximum replan attempts ({max_replan}) reached.",
            )

        # ---- Identify failed tasks ----------------------------------------
        failed_task_ids = [
            node.id
            for node in state.execution_graph.nodes.values()
            if node.status.value == "FAILED"
        ]

        if not failed_task_ids:
            # Nothing failed — no replan needed regardless of score
            if score.overall < 0.5:
                return ReplanDecision(
                    needs_replan=False,
                    affected_task_ids=[],
                    reason=(
                        f"Overall score ({score.overall:.2f}) is low but no "
                        f"tasks failed; replanning would not help."
                    ),
                )
            return ReplanDecision(
                needs_replan=False,
                affected_task_ids=[],
                reason="No failed tasks; no replan needed.",
            )

        # ---- LLM-based decision -----------------------------------------
        # Give the LLM the scores and failed tasks, let it decide.
        system_prompt = (
            "You are a replanning decision agent. Determine if replanning "
            "is needed based on evaluation scores and failed tasks. "
            "Return ONLY valid JSON."
        )

        user_message = (
            f"Evaluation scores:\n"
            f"  correctness: {score.correctness:.2f}\n"
            f"  completeness: {score.completeness:.2f}\n"
            f"  safety: {score.safety:.2f}\n"
            f"  overall: {score.overall:.2f}\n"
            f"  reasoning: {score.reasoning}\n\n"
            f"Replan count: {replan_count}/{max_replan}\n\n"
            f"Failed task IDs: {failed_task_ids}\n\n"
            "Return JSON with:\n"
            '- "needs_replan": boolean\n'
            '- "affected_task_ids": list of strings (subset of the failed task IDs)\n'
            '- "reason": string explaining the decision'
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

            affected = result.get("affected_task_ids", failed_task_ids)
            # Ensure we only replan tasks that actually failed
            affected = [tid for tid in affected if tid in failed_task_ids]

            return ReplanDecision(
                needs_replan=bool(result.get("needs_replan", True)),
                affected_task_ids=affected,
                reason=result.get(
                    "reason",
                    f"Replanning {len(affected)} failed task(s).",
                ),
            )

        except RuntimeError:
            # Fallback: always replan failed tasks
            return ReplanDecision(
                needs_replan=True,
                affected_task_ids=failed_task_ids,
                reason=f"LLM unavailable; replanning {len(failed_task_ids)} failed task(s) by default.",
            )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _format_tasks_for_eval(state: AgentState) -> str:
        """Produce a compact task summary for the LLM."""
        lines: list[str] = []
        for task_id, node in state.execution_graph.nodes.items():
            output_preview = ""
            if node.output:
                try:
                    out = json.dumps(node.output, indent=2)
                    output_preview = out[:150]
                except (TypeError, ValueError):
                    output_preview = str(node.output)[:150]

            lines.append(
                f"  [{node.status.value}] {task_id}"
                f"  agent={node.agent_type}"
                f"  deps={node.dependencies}"
                f"{'  -> ' + output_preview if output_preview else ''}"
            )
        return "\n".join(lines)

    @staticmethod
    def _format_errors(state: AgentState) -> str:
        """Format errors for the LLM prompt."""
        if not state.errors:
            return "No errors recorded."
        lines: list[str] = []
        for err in state.errors[-5:]:  # last 5 only to keep prompt small
            lines.append(
                f"  [{err.error_type}] {err.message[:200]}"
            )
        return "Recent errors:\n" + "\n".join(lines)

    @staticmethod
    def _heuristic_score(state: AgentState) -> EvalScore:
        """Compute a simple heuristic score when LLM is unavailable."""
        nodes = state.execution_graph.nodes.values()
        if not nodes:
            return EvalScore(
                correctness=0.0,
                completeness=0.0,
                safety=1.0,
                overall=0.0,
                reasoning="No tasks to evaluate.",
            )

        total = len(nodes)
        completed = sum(1 for n in nodes if n.status.value == "COMPLETED")
        failed = sum(1 for n in nodes if n.status.value == "FAILED")
        has_output = sum(1 for n in nodes if n.output is not None)

        correctness = completed / total if total > 0 else 0.0
        completeness = has_output / total if total > 0 else 0.0
        safety = 1.0 - (failed / total) * 0.5  # penalty for failures
        overall = (correctness + completeness + safety) / 3.0

        return EvalScore(
            correctness=round(correctness, 4),
            completeness=round(completeness, 4),
            safety=round(max(safety, 0.0), 4),
            overall=round(overall, 4),
            reasoning=(
                f"Heuristic: {completed}/{total} completed, "
                f"{failed}/{total} failed, "
                f"{has_output}/{total} with output."
            ),
        )
