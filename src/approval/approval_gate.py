"""INNOVATION #7: Human Approval Layer.

Before: Payment, Booking, Delete File...
Agent pauses. Requires Approval. Safe.

Uses ``asyncio.Event`` to wait for human response.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from typing import Any

from src.core.models import ApprovalRequest, RiskAssessment


class ApprovalGate:
    """INNOVATION #7: Human Approval Layer.

    Manages pending approval requests and provides an async mechanism for
    agents to block until a human responds (or a timeout expires).
    """

    def __init__(self, timeout_seconds: int = 300) -> None:
        """Initialise the approval gate.

        Args:
            timeout_seconds: Default wait timeout for each approval request.
                             Defaults to the framework-level setting.
        """
        self.timeout_seconds = timeout_seconds
        self._pending_approvals: dict[str, ApprovalRequest] = {}
        self._approval_events: dict[str, asyncio.Event] = {}

    # ------------------------------------------------------------------
    # Request & wait
    # ------------------------------------------------------------------

    async def request_approval(
        self,
        task_id: str,
        action_description: str,
        risk_assessment: RiskAssessment | None = None,
        session_id: str = "",
        *,
        timeout_seconds: int | None = None,
    ) -> ApprovalRequest:
        """Create an approval request and wait for a human response.

        The coroutine blocks until the human responds via :meth:`respond`
        or the timeout expires (in which case the request status becomes
        ``"expired"``).

        Args:
            task_id: Identifier of the task requiring approval.
            action_description: Human-readable description of the action.
            risk_assessment: Optional risk metadata.
            session_id: Session this request belongs to.
            timeout_seconds: Override the default timeout.  ``None`` uses the
                             gate-level default.

        Returns:
            The :class:`ApprovalRequest` with its final ``status`` field set
            to ``"approved"``, ``"rejected"``, or ``"expired"``.
        """
        request = ApprovalRequest(
            id=f"apr_{uuid.uuid4().hex[:12]}",
            session_id=session_id,
            task_id=task_id,
            action_description=action_description,
            risk_assessment=risk_assessment or RiskAssessment(),
            status="pending",
            created_at=datetime.now(timezone.utc),
            responded_at=None,
        )
        self._pending_approvals[request.id] = request

        # Create a one-shot event for the waiter
        event = asyncio.Event()
        self._approval_events[request.id] = event

        timeout = timeout_seconds if timeout_seconds is not None else self.timeout_seconds
        try:
            await asyncio.wait_for(event.wait(), timeout=timeout)
        except asyncio.TimeoutError:
            # Mark as expired only if still pending
            if request.status == "pending":
                request.status = "expired"
                request.responded_at = datetime.now(timezone.utc)
        finally:
            # Cleanup the event reference
            self._approval_events.pop(request.id, None)

        return request

    # ------------------------------------------------------------------
    # Respond
    # ------------------------------------------------------------------

    async def respond(
        self, approval_id: str, approved: bool
    ) -> ApprovalRequest | None:
        """Record a human response to an approval request.

        This is typically called from an HTTP handler or CLI input.

        Args:
            approval_id: The ID of the pending approval request.
            approved: ``True`` to approve, ``False`` to reject.

        Returns:
            The updated :class:`ApprovalRequest`, or ``None`` if the
            ``approval_id`` is unknown or the request is no longer pending.
        """
        request = self._pending_approvals.get(approval_id)
        if request is None or request.status != "pending":
            return None

        request.status = "approved" if approved else "rejected"
        request.responded_at = datetime.now(timezone.utc)

        # Signal the waiter that the response is available
        event = self._approval_events.get(approval_id)
        if event is not None and not event.is_set():
            event.set()

        return request

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get_pending(self) -> list[ApprovalRequest]:
        """Return all requests whose status is still ``"pending"``."""
        return [
            req
            for req in self._pending_approvals.values()
            if req.status == "pending"
        ]

    def get_for_session(self, session_id: str) -> list[ApprovalRequest]:
        """Return all requests (any status) that belong to *session_id*."""
        return [
            req
            for req in self._pending_approvals.values()
            if req.session_id == session_id
        ]

    def get_by_id(self, approval_id: str) -> ApprovalRequest | None:
        """Look up a single request by its ID."""
        return self._pending_approvals.get(approval_id)

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    async def cancel_pending_for_session(self, session_id: str) -> int:
        """Expire all pending requests for a given session (e.g. on shutdown).

        Returns the number of requests that were cancelled.
        """
        to_cancel = [
            req
            for req in self._pending_approvals.values()
            if req.session_id == session_id and req.status == "pending"
        ]
        for req in to_cancel:
            req.status = "expired"
            req.responded_at = datetime.now(timezone.utc)
            event = self._approval_events.get(req.id)
            if event is not None and not event.is_set():
                event.set()

        return len(to_cancel)

    @property
    def pending_count(self) -> int:
        """Number of currently pending approval requests."""
        return sum(
            1 for req in self._pending_approvals.values() if req.status == "pending"
        )
