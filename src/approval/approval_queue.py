"""Queue management for multiple pending approval requests."""

from __future__ import annotations

from collections import deque

from src.approval.approval_gate import ApprovalGate
from src.core.models import ApprovalRequest


class ApprovalQueue:
    """FIFO queue for managing pending approval requests.

    Useful when the system is processing multiple high-risk actions
    concurrently and wants to present them to the human operator one at
    a time or in a controlled order.
    """

    def __init__(self, gate: ApprovalGate) -> None:
        """Initialise the queue backed by an :class:`ApprovalGate`.

        Args:
            gate: The :class:`ApprovalGate` that will handle the actual
                  approval / rejection logic.
        """
        self.gate = gate
        self._queue: deque[ApprovalRequest] = deque()

    # ------------------------------------------------------------------
    # Queue operations
    # ------------------------------------------------------------------

    async def enqueue(self, request: ApprovalRequest) -> None:
        """Add an approval request to the end of the queue.

        The request should already have been created via
        :meth:`ApprovalGate.request_approval`.

        Args:
            request: The :class:`ApprovalRequest` to queue.
        """
        self._queue.append(request)

    async def enqueue_new(
        self,
        task_id: str,
        action_description: str,
        risk_assessment: object = None,
        session_id: str = "",
    ) -> ApprovalRequest:
        """Convenience: create a new approval request and enqueue it.

        The request is inserted into the queue but is **not** awaited --
        the caller should use :meth:`process_next` to wait for responses
        in FIFO order.

        Returns:
            The newly created :class:`ApprovalRequest` (status ``"pending"``).
        """
        from src.core.models import RiskAssessment

        # We don't call request_approval here because that would block.
        # Instead we create the request and manually register it.
        import uuid
        from datetime import datetime, timezone

        ra = risk_assessment if isinstance(risk_assessment, RiskAssessment) else RiskAssessment()
        request = ApprovalRequest(
            id=f"apr_{uuid.uuid4().hex[:12]}",
            session_id=session_id,
            task_id=task_id,
            action_description=action_description,
            risk_assessment=ra,
            status="pending",
            created_at=datetime.now(timezone.utc),
        )
        self._queue.append(request)
        return request

    async def process_next(
        self, *, timeout_seconds: int | None = None
    ) -> ApprovalRequest | None:
        """Dequeue the next pending request and wait for the human response.

        Args:
            timeout_seconds: Optional per-request timeout override.

        Returns:
            The resolved :class:`ApprovalRequest` (status ``"approved"``,
            ``"rejected"``, or ``"expired"``), or ``None`` if the queue
            is empty.
        """
        if not self._queue:
            return None

        request = self._queue.popleft()
        if request.status != "pending":
            # Already resolved by an external path; just return it.
            return request

        # Hand off to the gate to await a response
        return await self.gate.request_approval(
            task_id=request.task_id,
            action_description=request.action_description,
            risk_assessment=request.risk_assessment,
            session_id=request.session_id,
            timeout_seconds=timeout_seconds,
        )

    def peek(self) -> ApprovalRequest | None:
        """Return the next pending request **without** dequeuing it.

        Returns:
            The :class:`ApprovalRequest` at the front of the queue, or
            ``None`` if empty.
        """
        return self._queue[0] if self._queue else None

    async def process_all(
        self, *, timeout_seconds: int | None = None
    ) -> list[ApprovalRequest]:
        """Process every request currently in the queue in FIFO order.

        Args:
            timeout_seconds: Optional per-request timeout.

        Returns:
            A list of resolved :class:`ApprovalRequest` objects in the
            order they were processed.
        """
        results: list[ApprovalRequest] = []
        while self._queue:
            result = await self.process_next(timeout_seconds=timeout_seconds)
            if result is not None:
                results.append(result)
        return results

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    @property
    def size(self) -> int:
        """Number of requests currently waiting in the queue."""
        return len(self._queue)

    def list_pending(self) -> list[ApprovalRequest]:
        """Return all queued requests whose status is ``"pending"``."""
        return [req for req in self._queue if req.status == "pending"]

    def clear(self) -> int:
        """Remove and return the number of items currently in the queue.

        Does **not** affect the underlying gate — pending requests
        registered with the gate remain accessible via
        :meth:`ApprovalGate.get_pending`.
        """
        count = len(self._queue)
        self._queue.clear()
        return count
