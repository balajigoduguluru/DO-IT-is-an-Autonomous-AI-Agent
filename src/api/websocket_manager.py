"""WebSocket manager for live streaming execution events.

Provides the :class:`ConnectionManager` for multiplexing WebSocket connections
per session, and the :class:`EventStreamer` helper that the state machine and
engine components use to emit real-time events to connected clients.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from src.core.models import ApprovalRequest, ExecutionGraph, LedgerEntry, RiskAssessment

logger = logging.getLogger("agentic_ai.websocket")

# ===========================================================================
# Router for the WebSocket endpoint
# ===========================================================================

ws_router = APIRouter()


# ===========================================================================
# Connection Manager
# ===========================================================================


class ConnectionManager:
    """Manages WebSocket connections grouped by session ID.

    Each session can have multiple WebSocket clients connected simultaneously.
    The manager handles connect / disconnect lifecycle and broadcasts messages
    to all clients within a session, gracefully removing dead connections.
    """

    def __init__(self) -> None:
        #: ``{session_id: [WebSocket, ...]}``
        self.active_connections: dict[str, list[WebSocket]] = {}

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def connect(self, session_id: str, websocket: WebSocket) -> None:
        """Accept a new WebSocket and register it under *session_id*."""
        await websocket.accept()
        if session_id not in self.active_connections:
            self.active_connections[session_id] = []
        self.active_connections[session_id].append(websocket)
        logger.info(
            "WebSocket connected for session %s (%d active)",
            session_id,
            len(self.active_connections[session_id]),
        )

    def disconnect(self, session_id: str, websocket: WebSocket) -> None:
        """Remove a WebSocket from the session's connection list.

        Cleans up the session entry when the last connection drops.
        """
        if session_id not in self.active_connections:
            return
        try:
            self.active_connections[session_id].remove(websocket)
        except ValueError:
            # The socket may have already been removed.
            pass
        if not self.active_connections[session_id]:
            del self.active_connections[session_id]
            logger.info("WebSocket group for session %s removed (empty)", session_id)

    # ------------------------------------------------------------------
    # Broadcasting
    # ------------------------------------------------------------------

    async def broadcast(self, session_id: str, message: dict[str, Any]) -> None:
        """Send a JSON message to every connected client for a session.

        Dead connections are removed silently.
        """
        if session_id not in self.active_connections:
            return

        dead: list[WebSocket] = []
        for ws in self.active_connections[session_id]:
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)

        for ws in dead:
            self.disconnect(session_id, ws)

    async def stream_event(
        self, session_id: str, event_type: str, data: dict[str, Any]
    ) -> None:
        """Broadcast a typed event with a timestamp wrapper.

        Parameters
        ----------
        session_id:
            The session to broadcast to.
        event_type:
            A kebab-case string identifying the event kind (e.g.
            ``"phase_change"``, ``"task_update"``).
        data:
            The event payload.
        """
        await self.broadcast(
            session_id,
            {
                "type": event_type,
                "data": data,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get_connection_count(self, session_id: str) -> int:
        """Return the number of active connections for a session."""
        return len(self.active_connections.get(session_id, []))

    @property
    def total_connections(self) -> int:
        """Return the total number of active connections across all sessions."""
        return sum(len(v) for v in self.active_connections.values())


# Global singleton
manager = ConnectionManager()


# ===========================================================================
# Event Streamer
# ===========================================================================


class EventStreamer:
    """Helper that the state machine and engine use to emit real-time events.

    Every static method accepts a *session_id* and relevant domain data,
    then delegates to the global :data:`manager` to broadcast the event.

    Usage::

        await EventStreamer.phase_change(session_id, "BUILD_DAG")
        await EventStreamer.task_update(session_id, tid, "COMPLETED", {...})
    """

    @staticmethod
    async def phase_change(session_id: str, phase: str) -> None:
        """Emit a phase-transition event."""
        await manager.stream_event(session_id, "phase_change", {"phase": phase})

    @staticmethod
    async def task_update(
        session_id: str,
        task_id: str,
        status: str,
        output: dict[str, Any] | None = None,
    ) -> None:
        """Emit a task-status update event."""
        payload: dict[str, Any] = {"task_id": task_id, "status": status}
        if output is not None:
            payload["output"] = output
        await manager.stream_event(session_id, "task_update", payload)

    @staticmethod
    async def ledger_entry(session_id: str, entry: LedgerEntry) -> None:
        """Emit a new ledger entry event."""
        await manager.stream_event(session_id, "ledger_entry", entry.model_dump())

    @staticmethod
    async def approval_requested(session_id: str, request: ApprovalRequest) -> None:
        """Emit an approval-requested event."""
        await manager.stream_event(
            session_id, "approval_requested", request.model_dump()
        )

    @staticmethod
    async def graph_update(session_id: str, graph: ExecutionGraph) -> None:
        """Emit a graph-structure update event."""
        await manager.stream_event(
            session_id,
            "graph_update",
            {
                "nodes": {k: v.model_dump() for k, v in graph.nodes.items()},
                "edges": graph.edges,
            },
        )

    @staticmethod
    async def risk_assessment(
        session_id: str, task_id: str, risk: RiskAssessment
    ) -> None:
        """Emit a risk-assessment event for a task."""
        await manager.stream_event(
            session_id,
            "risk_assessment",
            {"task_id": task_id, "risk": risk.model_dump()},
        )

    @staticmethod
    async def error(
        session_id: str, task_id: str, error: str, recoverable: bool
    ) -> None:
        """Emit an error event."""
        await manager.stream_event(
            session_id,
            "error",
            {"task_id": task_id, "error": error, "recoverable": recoverable},
        )


# ===========================================================================
# WebSocket Endpoint
# ===========================================================================


@ws_router.websocket("/ws/session/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str) -> None:
    """WebSocket endpoint for live session streaming.

    Connected clients receive real-time events (phase changes, task updates,
    approval requests, etc.) broadcast by the :class:`EventStreamer`.

    The endpoint also accepts incoming JSON messages:
      - ``{"type": "ping"}`` → responds with ``{"type": "pong"}``
      - ``{"type": "approval_response", "approval_id": "...", "approved": true}``
        → routed to the approval gate (requires access to the gate singleton).
    """
    await manager.connect(session_id, websocket)
    try:
        while True:
            data = await websocket.receive_text()

            if not data.strip():
                continue

            try:
                msg = json.loads(data)
            except json.JSONDecodeError:
                await websocket.send_json(
                    {"type": "error", "data": {"message": "Invalid JSON"}}
                )
                continue

            msg_type = msg.get("type", "")

            if msg_type == "ping":
                await websocket.send_json({"type": "pong"})
            elif msg_type == "approval_response":
                # Forward approval responses to the approval gate.
                # The actual gate lookup is done via get_approval_gate()
                # imported lazily to avoid circular imports.
                from src.api.routes import get_approval_gate

                gate = get_approval_gate()
                approval_id = msg.get("approval_id", "")
                approved = msg.get("approved", False)
                result = await gate.respond(approval_id, approved)
                if result is not None:
                    await websocket.send_json(
                        {
                            "type": "approval_result",
                            "data": {
                                "approval_id": approval_id,
                                "status": result.status,
                            },
                        }
                    )
                else:
                    await websocket.send_json(
                        {
                            "type": "approval_result",
                            "data": {
                                "approval_id": approval_id,
                                "status": "not_found_or_already_processed",
                            },
                        }
                    )
            else:
                # Unknown message type — echo back an acknowledgement.
                await websocket.send_json(
                    {
                        "type": "echo",
                        "data": {
                            "original_type": msg_type,
                            "message": "Received",
                        },
                    }
                )

    except WebSocketDisconnect:
        manager.disconnect(session_id, websocket)
        logger.info("WebSocket disconnected for session %s", session_id)
    except Exception as exc:
        logger.error(
            "WebSocket error for session %s: %s", session_id, exc, exc_info=True
        )
        manager.disconnect(session_id, websocket)
