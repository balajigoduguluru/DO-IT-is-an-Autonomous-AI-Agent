"""Abstract base class for all tools in the marketplace."""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from typing import Any

from src.core.models import ToolCallResult, ToolRegistration


class BaseTool(ABC):
    """Abstract base for all tools in the marketplace."""

    @abstractmethod
    async def execute(self, **kwargs: Any) -> dict[str, Any]:
        """Execute the tool with given parameters."""

    @abstractmethod
    def get_registration(self) -> ToolRegistration:
        """Return tool's registration metadata for the marketplace."""

    def get_name(self) -> str:
        return self.get_registration().name

    async def execute_with_metrics(self, **kwargs: Any) -> ToolCallResult:
        """Wrap execute() with timing, success/failure tracking."""
        start = time.time()
        try:
            output = await self.execute(**kwargs)
            latency = (time.time() - start) * 1000
            return ToolCallResult(
                tool_name=self.get_name(),
                success=True,
                output=output,
                error=None,
                latency_ms=latency,
                cost=self._estimate_cost(latency),
            )
        except Exception as e:
            latency = (time.time() - start) * 1000
            return ToolCallResult(
                tool_name=self.get_name(),
                success=False,
                output=None,
                error=str(e),
                latency_ms=latency,
                cost=0.0,
            )

    def _estimate_cost(self, latency_ms: float) -> float:
        """Estimate API cost based on latency. Override per tool."""
        return latency_ms * 0.0001  # default: $0.10 per second
