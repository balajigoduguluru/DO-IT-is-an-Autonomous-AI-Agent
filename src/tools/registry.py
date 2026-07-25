"""
INNOVATION #5: Tool Marketplace.

Every tool stores: latency, accuracy, failures, avg_cost.
The scheduler selects the highest-scored tool rather than using hardcoded
routing.  Supports fallback chains on failure, and learns from past
executions via LearningMemory.
"""

from __future__ import annotations

import copy
from datetime import datetime, timezone
from typing import Any

from src.core.constants import ToolCategory
from src.core.models import ToolCallResult, ToolMetrics, ToolRegistration
from src.tools.base_tool import BaseTool


class ToolRegistry:
    """
    Tool Marketplace -- Innovation #5.

    Manages tool registration, capability-aware selection, fallback
    chains, and execution metrics.
    """

    def __init__(self) -> None:
        self._tools: dict[str, BaseTool] = {}
        self._metrics: dict[str, ToolMetrics] = {}
        self._categories: dict[ToolCategory, list[str]] = {
            cat: [] for cat in ToolCategory
        }

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register(self, tool: BaseTool) -> None:
        """Register a tool in the marketplace."""
        reg = tool.get_registration()
        name = reg.name

        if name in self._tools:
            raise ValueError(f"A tool with the name {name!r} is already registered")

        self._tools[name] = tool
        self._metrics[name] = reg.metrics or ToolMetrics(tool_name=name)
        self._categories[reg.category].append(name)

    def get_tool(self, name: str) -> BaseTool | None:
        """Retrieve a tool instance by name."""
        return self._tools.get(name)

    # ------------------------------------------------------------------
    # Selection
    # ------------------------------------------------------------------

    def get_best_tool(
        self,
        category: ToolCategory,
        required_capability: str | None = None,
    ) -> str:
        """
        Select the best tool by scoring each candidate in the category.

        Score = (accuracy * 0.4)
              + ((1 - failure_rate) * 0.3)
              + ((1 - normalised_latency) * 0.2)
              + ((1 - normalised_cost) * 0.1)

        Returns the name of the highest-scoring tool.
        """
        candidates = self._categories.get(category, [])
        if not candidates:
            raise KeyError(f"No tools registered for category {category!r}")

        if required_capability:
            filtered = []
            for name in candidates:
                reg = self._tools[name].get_registration()
                if required_capability in reg.description:
                    filtered.append(name)
            candidates = filtered or candidates  # fall back to all if none match

        best_name = candidates[0]
        best_score = -1.0

        for name in candidates:
            m = self._metrics[name]
            norm_lat = m.latency_ms / 10000.0 if m.latency_ms > 0 else 0.0
            norm_cost = m.avg_cost / 100.0 if m.avg_cost > 0 else 0.0

            score = (
                m.accuracy * 0.4
                + (1.0 - m.failure_rate) * 0.3
                + (1.0 - min(norm_lat, 1.0)) * 0.2
                + (1.0 - min(norm_cost, 1.0)) * 0.1
            )

            if score > best_score:
                best_score = score
                best_name = name

        return best_name

    # ------------------------------------------------------------------
    # Fallback chains
    # ------------------------------------------------------------------

    def get_fallback_chain(self, tool_name: str) -> list[str]:
        """Get ordered fallback tools if the primary tool fails."""
        tool = self._tools.get(tool_name)
        if tool is None:
            return []
        return tool.get_registration().fallback_chain

    async def execute_with_fallback(
        self,
        tool_name: str,
        input_data: dict[str, Any],
    ) -> tuple[ToolCallResult, str]:
        """
        Try the primary tool. On failure, walk the fallback chain.

        Returns ``(result, actual_tool_name_used)``.
        """
        chain = [tool_name] + self.get_fallback_chain(tool_name)
        last_error: str | None = None

        for attempt_name in chain:
            tool = self._tools.get(attempt_name)
            if tool is None:
                last_error = f"Tool {attempt_name!r} is not registered"
                continue

            result = await tool.execute_with_metrics(**input_data)
            self.update_metrics(attempt_name, result)

            if result.success:
                return result, attempt_name

            last_error = result.error

        # All attempts failed — return the last failure
        return ToolCallResult(
            tool_name=tool_name,
            success=False,
            output=None,
            error=f"All fallbacks exhausted. Last error: {last_error}",
            latency_ms=0.0,
            cost=0.0,
        ), tool_name

    # ------------------------------------------------------------------
    # Metrics
    # ------------------------------------------------------------------

    def update_metrics(self, tool_name: str, result: ToolCallResult) -> None:
        """Update tool metrics after each execution."""
        m = self._metrics.setdefault(
            tool_name, ToolMetrics(tool_name=tool_name)
        )

        m.total_calls += 1
        m.last_used = datetime.now(timezone.utc)

        # Exponentially-weighted moving average for latency
        if m.total_calls == 1:
            m.latency_ms = result.latency_ms
        else:
            m.latency_ms = 0.9 * m.latency_ms + 0.1 * result.latency_ms

        # Failure rate
        if result.success:
            m.accuracy = ((m.accuracy * (m.total_calls - 1)) + 1.0) / m.total_calls
        else:
            m.accuracy = ((m.accuracy * (m.total_calls - 1)) + 0.0) / m.total_calls

        m.failure_rate = 1.0 - m.accuracy

        # Average cost
        if m.total_calls == 1:
            m.avg_cost = result.cost
        else:
            m.avg_cost = ((m.avg_cost * (m.total_calls - 1)) + result.cost) / m.total_calls

    def get_all_metrics(self) -> dict[str, ToolMetrics]:
        """Return all tool metrics for the marketplace UI."""
        return dict(self._metrics)

    def get_metrics(self, tool_name: str) -> ToolMetrics | None:
        """Return metrics for a single tool."""
        return self._metrics.get(tool_name)

    # ------------------------------------------------------------------
    # Discovery
    # ------------------------------------------------------------------

    def get_available_tools(self) -> list[ToolRegistration]:
        """Return all registered tool registrations."""
        return [
            tool.get_registration() for tool in self._tools.values()
        ]

    def discover_tools(self) -> list[str]:
        """Return list of available tool names."""
        return list(self._tools.keys())
