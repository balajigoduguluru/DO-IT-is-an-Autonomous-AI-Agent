"""INNOVATION #6: Learning Memory using ChromaDB.

Stores and retrieves structured memory so the agent improves over time.
Explicitly provides hash-based embeddings to avoid ChromaDB's default
ONNX model download (which requires network access).
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import chromadb
    from chromadb.config import Settings as ChromaSettings
    _CHROMADB_AVAILABLE = True
except ImportError:
    _CHROMADB_AVAILABLE = False

    class ChromaSettings:  # type: ignore[no-redef]
        """Stub so the module can be imported without chromadb."""

        def __init__(self, anonymized_telemetry: bool = True) -> None:  # noqa: FBT001,FBT002
            pass

from src.core.config import settings
from src.core.constants import MemoryType
from src.core.models import MemoryEntry, PlanMemory


# ---------------------------------------------------------------------------
# Embedding helpers
# ---------------------------------------------------------------------------

_EMBEDDING_DIM = 384


def _make_embedding(text: str, dim: int = _EMBEDDING_DIM) -> list[float]:
    """Deterministic hash-based embedding.

    Produces a unit vector of *dim* dimensions from the input text.
    This is a lightweight stand-in until a real embedding model is plugged in.
    """
    raw = text.encode("utf-8")
    vec = [0.0] * dim
    for i in range(dim):
        h = hashlib.sha256(raw + str(i).encode()).digest()
        # interpret first 8 bytes as a double in [0, 1)
        val = int.from_bytes(h[:8], "little") / (2**64)
        vec[i] = val
    # L2-normalise
    norm = math.sqrt(sum(v * v for v in vec))
    if norm > 0:
        vec = [v / norm for v in vec]
    return vec


def _get_chroma_path(persist_directory: str | Path | None) -> Path:
    """Get a writable path for ChromaDB, using /tmp on Vercel/serverless."""
    if persist_directory:
        return Path(persist_directory)
    
    # Check if running on Vercel (read-only FS except /tmp)
    if os.environ.get("VERCEL") == "1":
        # Use /tmp for Vercel serverless functions
        return Path(tempfile.gettempdir()) / "chroma_db"
    
    # Default to settings path
    return Path(settings.CHROMA_DB_PATH)


# ---------------------------------------------------------------------------
# Learning Memory
# ---------------------------------------------------------------------------


class LearningMemory:
    """INNOVATION #6: Learning Memory.

    Instead of storing chat history, store:
    - Tool Success (did this tool work for this task?)
    - Average Response Time (how fast was it?)
    - Recovery Patterns (what worked when something failed?)
    - User Preferences (what does the user like?)
    - Failed Plans (what didn't work before?)

    Next execution improves using this data.
    That's actual learning, not just context accumulation.
    """

    COLLECTION_TOOL_METRICS = "tool_metrics"
    COLLECTION_RECOVERY_PATTERNS = "recovery_patterns"
    COLLECTION_USER_PREFERENCES = "user_preferences"
    COLLECTION_PLAN_HISTORY = "plan_history"

def __init__(self, persist_directory: str | Path | None = None) -> None:
        """Initialise ChromaDB client and ensure collections exist.

        Args:
            persist_directory: Where ChromaDB stores its data on disk.
                               Defaults to ``settings.CHROMA_DB_PATH``.
                               On Vercel serverless, uses /tmp/chroma_db.
        """
        if not _CHROMADB_AVAILABLE:
            raise RuntimeError(
                "The 'chromadb' package is required for LearningMemory. "
                "Install it with: pip install chromadb"
            )

        # Use /tmp on Vercel (read-only FS except /tmp)
        import os
        is_vercel = os.environ.get("VERCEL") == "1"
        if is_vercel and persist_directory is None:
            persist_path = Path("/tmp/chroma_db")
        else:
            persist_path = Path(persist_directory or settings.CHROMA_DB_PATH)
        
        persist_path.mkdir(parents=True, exist_ok=True)

        self.client = chromadb.PersistentClient(
            path=str(persist_path),
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        self._init_collections()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _init_collections(self) -> None:
        """Create or retrieve the known collections."""
        for name in (
            self.COLLECTION_TOOL_METRICS,
            self.COLLECTION_RECOVERY_PATTERNS,
            self.COLLECTION_USER_PREFERENCES,
            self.COLLECTION_PLAN_HISTORY,
        ):
            try:
                self.client.get_collection(name=name)
            except (ValueError, chromadb.errors.NotFoundError):
                self.client.create_collection(
                    name=name,
                    metadata={"description": f"Learning memory: {name}"},
                )

    def _collection(self, name: str):
        """Return the collection handle by name, creating if necessary."""
        try:
            return self.client.get_collection(name=name)
        except (ValueError, chromadb.errors.NotFoundError):
            return self.client.create_collection(
                name=name,
                metadata={"description": f"Learning memory: {name}"},
            )

    # ------------------------------------------------------------------
    # Tool Success / Failure
    # ------------------------------------------------------------------

    async def record_tool_result(
        self,
        tool_name: str,
        success: bool,
        latency_ms: float,
        input_data: dict[str, Any],
        output_data: dict[str, Any],
        session_id: str,
    ) -> None:
        """Record a tool execution result in learning memory.

        Args:
            tool_name: Name of the tool that was invoked.
            success: Whether the tool completed successfully.
            latency_ms: Execution time in milliseconds.
            input_data: Input payload for the invocation.
            output_data: Output payload returned by the tool.
            session_id: The session this result belongs to.
        """
        now = datetime.now(timezone.utc)
        doc_id = f"{tool_name}_{now.isoformat()}"
        document = json.dumps(
            {
                "tool_name": tool_name,
                "success": success,
                "latency_ms": latency_ms,
                "input_data": input_data,
                "output_data": output_data,
                "session_id": session_id,
            }
        )
        metadata = {
            "tool_name": tool_name,
            "success": str(success),
            "session_id": session_id,
            "timestamp": now.isoformat(),
            "latency_ms": str(latency_ms),
            "type": MemoryType.TOOL_SUCCESS if success else MemoryType.TOOL_FAILURE,
        }
        coll = self._collection(self.COLLECTION_TOOL_METRICS)
        coll.add(
            ids=[doc_id],
            documents=[document],
            metadatas=[metadata],
            embeddings=[_make_embedding(document)],
        )

    async def get_tool_history(
        self, tool_name: str, limit: int = 20
    ) -> list[MemoryEntry]:
        """Return the most recent *limit* records for a specific tool.

        Results are ordered newest-first (by the stored timestamp metadata).
        """
        coll = self._collection(self.COLLECTION_TOOL_METRICS)
        results = coll.get(where={"tool_name": tool_name}, limit=limit)

        entries: list[MemoryEntry] = []
        for i, doc_id in enumerate(results.get("ids", [])):
            meta = results["metadatas"][i] if results["metadatas"] else {}
            doc = results["documents"][i] if results["documents"] else ""
            entry = MemoryEntry(
                id=doc_id,
                type=MemoryType(meta.get("type", MemoryType.TOOL_SUCCESS)),
                key=tool_name,
                value=_safe_json_loads(doc),
                embedding=(
                    results["embeddings"][i] if results.get("embeddings") else None
                ),
                timestamp=datetime.fromisoformat(
                    meta.get("timestamp", now_iso())
                ),
                session_id=meta.get("session_id", ""),
                weight=1.0,
            )
            entries.append(entry)

        # sort newest-first by timestamp
        entries.sort(key=lambda e: e.timestamp, reverse=True)
        return entries

    async def get_tool_success_rate(self, tool_name: str) -> float:
        """Calculate the success rate (0.0 - 1.0) for a tool from history.

        Returns 0.5 if no records exist yet (neutral prior).
        """
        coll = self._collection(self.COLLECTION_TOOL_METRICS)
        results = coll.get(where={"tool_name": tool_name})

        metadatas = results.get("metadatas", [])
        if not metadatas:
            return 0.5

        successes = sum(
            1 for m in metadatas if m.get("success") == "True"  # type: ignore[union-attr]
        )
        return successes / len(metadatas)

    # ------------------------------------------------------------------
    # Recovery Patterns
    # ------------------------------------------------------------------

    async def record_recovery(
        self,
        failed_tool: str,
        successful_fallback: str,
        context: dict[str, Any],
        session_id: str,
    ) -> None:
        """Record a successful recovery pattern for future reference.

        Args:
            failed_tool: Name of the tool that failed.
            successful_fallback: Name of the tool that worked as a fallback.
            context: Descriptors of the situation (task type, parameters, etc.).
            session_id: The session where this recovery occurred.
        """
        now = datetime.now(timezone.utc)
        doc_id = f"rec_{failed_tool}_{successful_fallback}_{now.isoformat()}"
        document = json.dumps(
            {
                "failed_tool": failed_tool,
                "successful_fallback": successful_fallback,
                "context": context,
                "session_id": session_id,
            }
        )
        metadata = {
            "failed_tool": failed_tool,
            "successful_fallback": successful_fallback,
            "session_id": session_id,
            "timestamp": now.isoformat(),
            "type": MemoryType.RECOVERY_PATTERN,
        }
        coll = self._collection(self.COLLECTION_RECOVERY_PATTERNS)
        coll.add(
            ids=[doc_id],
            documents=[document],
            metadatas=[metadata],
            embeddings=[_make_embedding(document)],
        )

    async def find_recovery_pattern(
        self, failed_tool: str, context: dict[str, Any] | None = None
    ) -> str | None:
        """Search for a recovery pattern that worked in a similar situation.

        Args:
            failed_tool: The tool that just failed.
            context: Optional situational context to improve matching.

        Returns:
            The fallback tool name if a matching pattern is found, else ``None``.
        """
        coll = self._collection(self.COLLECTION_RECOVERY_PATTERNS)
        where: dict[str, Any] = {"failed_tool": failed_tool}

        # If context is provided, attempt embedding similarity.
        if context is not None:
            context_emb = _make_embedding(json.dumps(context))
            query_results = coll.query(
                query_embeddings=[context_emb],
                where=where,
                n_results=1,
            )
            ids = query_results.get("ids", [[]])[0]
            metadatas_q = query_results.get("metadatas", [[]])[0]
            if ids and metadatas_q:
                return str(metadatas_q[0].get("successful_fallback", ""))

        # Fall back to most recent metadata match
        results = coll.get(where=where, limit=10)
        metadatas = results.get("metadatas", [])

        if not metadatas:
            return None

        best: str | None = None
        latest_ts = ""
        for m in metadatas:
            ts = m.get("timestamp", "")  # type: ignore[union-attr]
            if ts > latest_ts:
                latest_ts = ts
                best = m.get("successful_fallback", None)  # type: ignore[union-attr]
        return best

    # ------------------------------------------------------------------
    # User Preferences
    # ------------------------------------------------------------------

    async def record_preference(
        self, key: str, value: dict[str, Any], session_id: str
    ) -> None:
        """Record (or overwrite) a user preference.

        Args:
            key: Preference key (e.g. ``"transport"``, ``"budget_style"``).
            value: Preference value as a dict.
            session_id: The session where this preference was expressed.
        """
        now = datetime.now(timezone.utc)
        document = json.dumps(value)
        metadata = {
            "key": key,
            "session_id": session_id,
            "timestamp": now.isoformat(),
            "type": MemoryType.USER_PREFERENCE,
        }
        coll = self._collection(self.COLLECTION_USER_PREFERENCES)

        # Upsert: delete old entry for the same key then add the new one.
        existing = coll.get(where={"key": key})
        existing_ids = existing.get("ids", [])
        if existing_ids:
            coll.delete(ids=existing_ids)

        coll.add(
            ids=[f"pref_{key}"],
            documents=[document],
            metadatas=[metadata],
            embeddings=[_make_embedding(document)],
        )

    async def get_preference(self, key: str) -> dict[str, Any] | None:
        """Return the stored value for a preference key, or ``None``."""
        coll = self._collection(self.COLLECTION_USER_PREFERENCES)
        results = coll.get(where={"key": key})
        documents = results.get("documents", [])
        if not documents:
            return None
        return _safe_json_loads(documents[0])

    async def get_all_preferences(self) -> dict[str, dict[str, Any]]:
        """Return every stored user preference as ``{key: value}``."""
        coll = self._collection(self.COLLECTION_USER_PREFERENCES)
        results = coll.get()
        metadatas = results.get("metadatas", [])
        documents = results.get("documents", [])
        prefs: dict[str, dict[str, Any]] = {}
        for i, meta in enumerate(metadatas or []):
            key = meta.get("key", "")  # type: ignore[union-attr]
            doc = documents[i] if documents else "{}"
            prefs[key] = _safe_json_loads(doc)
        return prefs

    # ------------------------------------------------------------------
    # Plan History
    # ------------------------------------------------------------------

    async def save_plan(
        self,
        goal: str,
        graph_snapshot: dict[str, Any],
        success: bool,
        score: float | None,
        session_id: str,
    ) -> None:
        """Persist a plan execution for future similarity-based retrieval.

        Args:
            goal: The original user goal.
            graph_snapshot: Serialised execution graph / DAG.
            success: Whether the plan ultimately succeeded.
            score: Evaluation score (0.0 - 1.0), if available.
            session_id: The session that executed this plan.
        """
        now = datetime.now(timezone.utc)
        doc_id = f"plan_{session_id}_{now.isoformat()}"
        document = json.dumps(
            {
                "goal": goal,
                "graph_snapshot": graph_snapshot,
                "success": success,
                "score": score,
                "session_id": session_id,
            }
        )
        embedding = _make_embedding(goal)
        metadata = {
            "goal": goal,
            "success": str(success),
            "score": str(score) if score is not None else "",
            "session_id": session_id,
            "timestamp": now.isoformat(),
            "type": (
                MemoryType.SUCCESSFUL_PLAN
                if success
                else MemoryType.FAILED_PLAN
            ),
        }
        coll = self._collection(self.COLLECTION_PLAN_HISTORY)
        coll.add(
            ids=[doc_id],
            documents=[document],
            metadatas=[metadata],
            embeddings=[embedding],
        )

    async def find_similar_plan(
        self, goal: str, threshold: float = 0.7
    ) -> PlanMemory | None:
        """Search for a past plan with a similar goal using embedding similarity.

        Args:
            goal: The user goal to match against past plans.
            threshold: Minimum distance-based similarity threshold. ChromaDB
                       returns results sorted by distance; we accept the top
                       result if ``1 - distance / 2 >= threshold``.

        Returns:
            A ``PlanMemory`` instance, or ``None`` if nothing is close enough.
        """
        coll = self._collection(self.COLLECTION_PLAN_HISTORY)
        goal_emb = _make_embedding(goal)
        results = coll.query(query_embeddings=[goal_emb], n_results=1)

        ids = results.get("ids", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        documents = results.get("documents", [[]])[0]
        distances = results.get("distances", [[]])[0]

        if not ids:
            return None

        # ChromaDB distances are L2 by default.  Convert to a similarity
        # score in [0, 1] and compare against the threshold.
        dist = distances[0] if distances else 1.0
        similarity = max(0.0, 1.0 - dist / 2.0)

        if similarity < threshold:
            return None

        meta = metadatas[0] if metadatas else {}
        doc_str = documents[0] if documents else "{}"
        plan_data = _safe_json_loads(doc_str)

        graph_snapshot = plan_data.get("graph_snapshot", {})
        score_raw = plan_data.get("score") or meta.get("score")

        try:
            score_val = float(score_raw) if score_raw is not None else None  # type: ignore[arg-type]
        except (ValueError, TypeError):
            score_val = None

        return PlanMemory(
            id=ids[0],
            session_id=meta.get("session_id", ""),  # type: ignore[union-attr]
            goal=meta.get("goal", goal),  # type: ignore[union-attr]
            graph_snapshot=graph_snapshot,
            success=meta.get("success", "False") == "True",  # type: ignore[union-attr]
            score=score_val,
            timestamp=datetime.fromisoformat(
                meta.get("timestamp", now_iso())  # type: ignore[union-attr]
            ),
        )

    # ------------------------------------------------------------------
    # Context assembly
    # ------------------------------------------------------------------

    async def get_context_for_goal(self, goal: str) -> dict[str, Any]:
        """Gather all relevant context from memory for a given goal.

        Combines:
        - Similar past plans (top-3)
        - Relevant tool metrics (all tools that have been used)
        - User preferences

        Returns a structured dict suitable for the planner.
        """
        similar_plan = await self.find_similar_plan(goal, threshold=0.5)

        # Collect metrics for all tools that have history.
        coll = self._collection(self.COLLECTION_TOOL_METRICS)
        all_tool_results = coll.get()
        tool_names = set()
        for m in (all_tool_results.get("metadatas") or []):
            tn = m.get("tool_name")  # type: ignore[union-attr]
            if tn:
                tool_names.add(tn)

        tool_metrics: dict[str, dict[str, Any]] = {}
        for tn in sorted(tool_names):
            try:
                rate = await self.get_tool_success_rate(tn)
                hist = await self.get_tool_history(tn, limit=5)
                avg_latency = (
                    sum(
                        float(
                            json.loads(h.value).get("latency_ms", 0)
                            if isinstance(h.value, str)
                            else h.value.get("latency_ms", 0)
                        )
                        for h in hist
                    )
                    / len(hist)
                    if hist
                    else 0.0
                )
                tool_metrics[tn] = {
                    "success_rate": rate,
                    "avg_latency_ms": avg_latency,
                    "recent_calls": len(hist),
                }
            except Exception:
                continue

        preferences = await self.get_all_preferences()

        return {
            "goal": goal,
            "similar_past_plan": (
                similar_plan.model_dump(mode="json") if similar_plan else None
            ),
            "tool_metrics": tool_metrics,
            "preferences": preferences,
        }

    # ------------------------------------------------------------------
    # Embedding (public for external use)
    # ------------------------------------------------------------------

    @staticmethod
    def _get_embedding(text: str) -> list[float]:
        """Generate an embedding vector for the given text.

        Uses a deterministic hash-based approach to produce a unit-norm
        vector of 384 dimensions.  Replace with a real embedding model
        (e.g. OpenAI ``text-embedding-3-small``) for production use.
        """
        return _make_embedding(text)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def now_iso() -> str:
    """Return the current UTC timestamp as an ISO-formatted string."""
    return datetime.now(timezone.utc).isoformat()


def _safe_json_loads(value: Any) -> dict[str, Any]:
    """Parse *value* as JSON, returning a dict.

    If *value* is already a dict it is returned as-is.
    """
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return {"raw": value}
    return {"raw": str(value)}
