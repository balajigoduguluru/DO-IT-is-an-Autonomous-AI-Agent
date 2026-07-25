"""Plan archiving and recall backed by LearningMemory."""

from __future__ import annotations

from typing import Any

from src.core.models import AgentState, PlanMemory
from src.memory.learning_memory import LearningMemory


class PlanMemoryStore:
    """Store and retrieve past plan executions for learning / retrieval."""

    def __init__(self, memory: LearningMemory) -> None:
        self.memory = memory

    # ------------------------------------------------------------------
    # Archive
    # ------------------------------------------------------------------

    async def archive_plan(
        self,
        state: AgentState,
        success: bool,
        score: float | None = None,
    ) -> None:
        """Persist the completed plan from an :class:`AgentState` for future recall.

        Args:
            state: The final agent state containing the goal and execution graph.
            success: Whether the plan ultimately succeeded.
            score: Optional evaluation score (0.0 - 1.0).
        """
        graph_snapshot = state.execution_graph.model_dump(mode="json")
        await self.memory.save_plan(
            goal=state.user_goal,
            graph_snapshot=graph_snapshot,
            success=success,
            score=score,
            session_id=state.session_id,
        )

    # ------------------------------------------------------------------
    # Recall
    # ------------------------------------------------------------------

    async def recall_similar(
        self, goal: str, top_k: int = 3
    ) -> list[PlanMemory]:
        """Retrieve past plans whose goals are semantically similar to *goal*.

        Args:
            goal: The user goal to match against archived plans.
            top_k: Maximum number of results to return.

        Returns:
            A list of ``PlanMemory`` objects, ordered by similarity
            (most similar first).  May be empty if nothing is found.
        """
        results: list[PlanMemory] = []
        # ChromaDB collection query is simpler via the LearningMemory method,
        # which returns at most one result.  For top_k > 1 we query the
        # collection directly.
        coll = self.memory._collection(  # pylint: disable=protected-access
            self.memory.COLLECTION_PLAN_HISTORY
        )

        goal_emb = self.memory._get_embedding(goal)  # pylint: disable=protected-access

        query = coll.query(
            query_embeddings=[goal_emb],
            n_results=min(top_k, 50),
        )

        ids = query.get("ids", [[]])[0]
        metadatas = query.get("metadatas", [[]])[0]
        documents = query.get("documents", [[]])[0]
        distances = query.get("distances", [[]])[0]

        for i, doc_id in enumerate(ids):
            meta = metadatas[i] if i < len(metadatas) else {}
            doc = documents[i] if i < len(documents) else ""
            dist = distances[i] if i < len(distances) else 1.0

            similarity = max(0.0, 1.0 - dist / 2.0)
            if similarity < 0.3:
                continue  # skip poor matches

            # Attempt to parse the stored plan JSON; fall back to empty.
            try:
                import json

                plan_data = json.loads(doc) if isinstance(doc, str) else {}
                graph_snapshot = plan_data.get("graph_snapshot", {})
                score_val = plan_data.get("score")
            except (json.JSONDecodeError, TypeError):
                graph_snapshot = {}
                score_val = None

            plan_mem = PlanMemory(
                id=doc_id,
                session_id=meta.get("session_id", ""),  # type: ignore[union-attr]
                goal=meta.get("goal", goal),  # type: ignore[union-attr]
                graph_snapshot=graph_snapshot,
                success=meta.get("success", "False") == "True",  # type: ignore[union-attr]
                score=(
                    float(meta["score"])  # type: ignore[union-attr]
                    if meta.get("score")
                    else None
                ),
            )
            results.append(plan_mem)

        return results

    # ------------------------------------------------------------------
    # Failure pattern analysis
    # ------------------------------------------------------------------

    async def get_failure_patterns(self) -> list[dict[str, Any]]:
        """Analyse archived plans to find recurring failure patterns.

        Examines failed plans and returns a list of descriptive dicts
        that can be fed to the planner so it avoids repeating mistakes.

        Returns:
            A list of dicts, each containing:
            - ``goal_snippet``: first 120 characters of the goal.
            - ``failure_count``: number of failed plans matching this pattern.
            - ``graph_summary``: high-level summary of the DAG structure.
        """
        coll = self.memory._collection(  # pylint: disable=protected-access
            self.memory.COLLECTION_PLAN_HISTORY
        )
        results = coll.get(
            where={"success": "False"},
        )

        metadatas = results.get("metadatas", []) or []
        documents = results.get("documents", []) or []

        if not metadatas:
            return []

        # Group failed plans by goal prefix (first 40 chars) so we can
        # spot repeated failures on similar goals.
        from collections import Counter

        goal_counter: Counter[str] = Counter()
        summaries: list[dict[str, Any]] = []

        for i, meta in enumerate(metadatas):
            goal_text = meta.get("goal", "") if meta else ""  # type: ignore[union-attr]
            prefix = goal_text[:40] if goal_text else "unknown"
            goal_counter[prefix] += 1

        for prefix, count in goal_counter.most_common(10):
            summaries.append(
                {
                    "goal_snippet": f"{prefix}..." if len(prefix) == 40 else prefix,
                    "failure_count": count,
                    "graph_summary": "failed_plan",
                }
            )

        return summaries
