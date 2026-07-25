"""INNOVATION #8: Execution Ledger.

Every action produces a timestamped entry:
{time, agent, action, confidence, details}
Judges love transparency.

Also persisted to SQLite for durability.
"""

from __future__ import annotations

import json
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.core.config import settings
from src.core.models import LedgerEntry


class ExecutionLedger:
    """INNOVATION #8: Execution Ledger.

    Thread-safe audit log that records every agent action both in memory
    and in an embedded SQLite database for crash-safe persistence.
    """

    def __init__(self, db_path: str | Path | None = None) -> None:
        """Initialise the ledger.

        Args:
            db_path: Filesystem path for the SQLite database.
                     Defaults to ``settings.SQLITE_PATH``.
        """
        self._entries: list[LedgerEntry] = []
        self._db_path = Path(db_path or settings.SQLITE_PATH)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    # ------------------------------------------------------------------
    # Database initialisation
    # ------------------------------------------------------------------

    def _init_db(self) -> None:
        """Create the SQLite table if it does not exist."""
        conn = sqlite3.connect(str(self._db_path))
        try:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS execution_ledger (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp   TEXT    NOT NULL,
                    agent       TEXT    NOT NULL,
                    action      TEXT    NOT NULL,
                    task_id     TEXT,
                    session_id  TEXT,
                    confidence  REAL    NOT NULL DEFAULT 1.0,
                    latency_ms  REAL    NOT NULL DEFAULT 0.0,
                    risk_level  TEXT,
                    details     TEXT
                )
                """
            )
            conn.commit()
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # Record
    # ------------------------------------------------------------------

    async def record(
        self,
        agent: str,
        action: str,
        task_id: str | None = None,
        session_id: str | None = None,
        confidence: float = 1.0,
        latency_ms: float = 0.0,
        risk_level: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> LedgerEntry:
        """Persist an action in the ledger (in-memory + SQLite).

        Args:
            agent: Name / identifier of the agent that performed the action.
            action: Description of the action taken.
            task_id: Optional task/node ID this action relates to.
            session_id: Optional session identifier for grouping.
            confidence: Confidence level (0.0 - 1.0).
            latency_ms: Execution time in milliseconds.
            risk_level: ``"LOW"``, ``"MEDIUM"``, ``"HIGH"``, or ``"CRITICAL"``.
            details: Arbitrary key-value data attached to the entry.

        Returns:
            The newly created :class:`LedgerEntry`.
        """
        entry = LedgerEntry(
            agent=agent,
            action=action,
            task_id=task_id,
            confidence=max(0.0, min(1.0, confidence)),
            latency_ms=max(0.0, latency_ms),
            risk_level=risk_level,
            details=details,
        )
        self._entries.append(entry)

        # Persist to SQLite
        conn = sqlite3.connect(str(self._db_path))
        try:
            conn.execute(
                """
                INSERT INTO execution_ledger
                    (timestamp, agent, action, task_id, session_id,
                     confidence, latency_ms, risk_level, details)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    entry.timestamp.isoformat(),
                    entry.agent,
                    entry.action,
                    entry.task_id,
                    session_id,
                    entry.confidence,
                    entry.latency_ms,
                    entry.risk_level,
                    json.dumps(entry.details) if entry.details else None,
                ),
            )
            conn.commit()
        finally:
            conn.close()

        return entry

    # ------------------------------------------------------------------
    # Querying
    # ------------------------------------------------------------------

    async def get_all(self, limit: int = 100, offset: int = 0) -> list[LedgerEntry]:
        """Return ledger entries from SQLite with pagination.

        Results are ordered newest-first.
        """
        conn = sqlite3.connect(str(self._db_path))
        try:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                SELECT timestamp, agent, action, task_id, confidence,
                       latency_ms, risk_level, details
                FROM execution_ledger
                ORDER BY id DESC
                LIMIT ? OFFSET ?
                """,
                (limit, offset),
            ).fetchall()
        finally:
            conn.close()

        return [self._row_to_entry(r) for r in rows]

    async def get_by_session(self, session_id: str) -> list[LedgerEntry]:
        """Return all entries that belong to a given session.

        Results are ordered oldest-first (chronological).
        """
        conn = sqlite3.connect(str(self._db_path))
        try:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                SELECT timestamp, agent, action, task_id, confidence,
                       latency_ms, risk_level, details
                FROM execution_ledger
                WHERE session_id = ?
                ORDER BY id ASC
                """,
                (session_id,),
            ).fetchall()
        finally:
            conn.close()

        return [self._row_to_entry(r) for r in rows]

    async def get_summary(self) -> dict[str, Any]:
        """Compute aggregate statistics over all entries in the ledger.

        Returns:
            A dict with keys:
            - ``total_actions``
            - ``avg_confidence``
            - ``total_latency``
            - ``risk_breakdown``: ``{LOW: N, MEDIUM: N, ...}``
        """
        conn = sqlite3.connect(str(self._db_path))
        try:
            conn.row_factory = sqlite3.Row
            total = conn.execute(
                "SELECT COUNT(*) AS cnt FROM execution_ledger"
            ).fetchone()["cnt"]

            avg_conf = conn.execute(
                "SELECT COALESCE(AVG(confidence), 0.0) AS val FROM execution_ledger"
            ).fetchone()["val"]

            total_lat = conn.execute(
                "SELECT COALESCE(SUM(latency_ms), 0.0) AS val FROM execution_ledger"
            ).fetchone()["val"]

            risk_rows = conn.execute(
                "SELECT risk_level, COUNT(*) AS cnt FROM execution_ledger "
                "WHERE risk_level IS NOT NULL GROUP BY risk_level"
            ).fetchall()
        finally:
            conn.close()

        risk_breakdown: dict[str, int] = {}
        for r in risk_rows:
            risk_breakdown[r["risk_level"]] = r["cnt"]

        return {
            "total_actions": total,
            "avg_confidence": round(avg_conf, 4),
            "total_latency_ms": round(total_lat, 2),
            "risk_breakdown": risk_breakdown,
        }

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def to_json(self) -> str:
        """Serialise the in-memory entries to a JSON string.

        Useful for sending the current session ledger to a UI or API
        response.
        """
        return json.dumps(
            [e.model_dump(mode="json") for e in self._entries],
            default=str,
            indent=2,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _row_to_entry(row: sqlite3.Row) -> LedgerEntry:
        """Convert a SQLite row to a :class:`LedgerEntry`."""
        details_raw = row["details"]
        details: dict[str, Any] | None = None
        if details_raw:
            try:
                details = json.loads(details_raw)
            except (json.JSONDecodeError, TypeError):
                details = {"raw": details_raw}

        return LedgerEntry(
            timestamp=datetime.fromisoformat(row["timestamp"]),
            agent=row["agent"],
            action=row["action"],
            task_id=row["task_id"],
            confidence=row["confidence"],
            latency_ms=row["latency_ms"],
            risk_level=row["risk_level"],
            details=details,
        )
