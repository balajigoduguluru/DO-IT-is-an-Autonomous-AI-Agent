"""Tests for the tool marketplace (Innovation #5).

Tests tool registration, best-tool selection by scoring, fallback chains,
and metrics update after execution.
"""

import sys
from pathlib import Path

import pytest

_HERE = Path(__file__).resolve().parent
_PROJECT_ROOT = _HERE.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from src.core.constants import ToolCategory
from src.core.models import ToolCallResult, ToolMetrics, ToolRegistration
from src.tools.base_tool import BaseTool
from src.tools.budget_tool import BudgetTool
from src.tools.email_tool import EmailTool
from src.tools.flight_tool import FlightTool, FlightToolMock
from src.tools.hotel_tool import HotelTool
from src.tools.registry import ToolRegistry
from src.tools.train_tool import TrainTool
from src.tools.weather_tool import WeatherTool


class TestToolMarketplace:
    """Test tool registration and selection."""

    # ------------------------------------------------------------------
    # Fixtures
    # ------------------------------------------------------------------

    @pytest.fixture
    def registry(self) -> ToolRegistry:
        return ToolRegistry()

    @pytest.fixture
    def populated_registry(self, registry: ToolRegistry) -> ToolRegistry:
        """A registry with several tools registered."""
        registry._tools["flight_search"] = FlightTool()
        registry._tools["flight_search_mock"] = FlightToolMock()
        registry._tools["train_search"] = TrainTool()
        registry._tools["hotel_search"] = HotelTool()
        registry._tools["weather_check"] = WeatherTool()
        registry._tools["budget_calculator"] = BudgetTool()
        registry._tools["email_sender"] = EmailTool()

        # Populate categories
        registry._categories[ToolCategory.FLIGHT] = ["flight_search", "flight_search_mock"]
        registry._categories[ToolCategory.TRANSPORT] = ["train_search"]
        registry._categories[ToolCategory.HOTEL] = ["hotel_search"]
        registry._categories[ToolCategory.WEATHER] = ["weather_check"]
        registry._categories[ToolCategory.BUDGET] = ["budget_calculator"]
        registry._categories[ToolCategory.EMAIL] = ["email_sender"]

        # Set some metrics so scoring works
        for name, metrics_data in {
            "flight_search": dict(failure_rate=0.3, accuracy=0.7, latency_ms=3200, avg_cost=5.0, total_calls=50),
            "flight_search_mock": dict(failure_rate=0.01, accuracy=0.99, latency_ms=150, avg_cost=0.5, total_calls=200),
            "train_search": dict(failure_rate=0.03, accuracy=0.97, latency_ms=800, avg_cost=2.0, total_calls=100),
            "hotel_search": dict(failure_rate=0.05, accuracy=0.92, latency_ms=1100, avg_cost=3.0, total_calls=80),
        }.items():
            registry._metrics[name] = ToolMetrics(tool_name=name, **metrics_data)

        return registry

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def test_register_tool(self, registry: ToolRegistry) -> None:
        """Test tool registration in marketplace."""
        tool = WeatherTool()
        registry.register(tool)

        assert "weather_check" in registry._tools
        assert "weather_check" in registry._categories[ToolCategory.WEATHER]

    def test_register_duplicate_tool(self, registry: ToolRegistry) -> None:
        """Test that registering a duplicate tool name raises an error."""
        tool1 = WeatherTool()
        registry.register(tool1)

        tool2 = WeatherTool()
        with pytest.raises(ValueError, match="already registered"):
            registry.register(tool2)

    def test_register_multiple_categories(self, registry: ToolRegistry) -> None:
        """Test that tools are categorised correctly."""
        registry.register(WeatherTool())
        registry.register(HotelTool())
        registry.register(BudgetTool())
        registry.register(EmailTool())

        assert "weather_check" in registry._categories[ToolCategory.WEATHER]
        assert "hotel_search" in registry._categories[ToolCategory.HOTEL]
        assert "budget_calculator" in registry._categories[ToolCategory.BUDGET]
        assert "email_sender" in registry._categories[ToolCategory.EMAIL]

    # ------------------------------------------------------------------
    # Best tool selection
    # ------------------------------------------------------------------

    def test_best_tool_selection(self, populated_registry: ToolRegistry) -> None:
        """Test that highest-scored tool is selected."""
        # For FLIGHT category, flight_search_mock should score higher
        best = populated_registry.get_best_tool(ToolCategory.FLIGHT)
        assert best == "flight_search_mock", (
            f"Expected flight_search_mock, got {best}"
        )

    def test_best_tool_transport(self, populated_registry: ToolRegistry) -> None:
        """Test best tool selection for TRANSPORT category."""
        best = populated_registry.get_best_tool(ToolCategory.TRANSPORT)
        assert best == "train_search"

    def test_best_tool_no_candidates(self, registry: ToolRegistry) -> None:
        """Test that selecting from an empty category raises KeyError."""
        with pytest.raises(KeyError):
            registry.get_best_tool(ToolCategory.GENERAL)

    # ------------------------------------------------------------------
    # Fallback chain
    # ------------------------------------------------------------------

    def test_fallback_chain(self, populated_registry: ToolRegistry) -> None:
        """Test fallback chain on tool failure."""
        chain = populated_registry.get_fallback_chain("flight_search")
        assert "flight_search_mock" in chain
        assert "train_search" in chain

    def test_fallback_chain_empty(self, registry: ToolRegistry) -> None:
        """Test that unregistered tool returns empty fallback chain."""
        chain = registry.get_fallback_chain("nonexistent_tool")
        assert chain == []

    # ------------------------------------------------------------------
    # Metrics update
    # ------------------------------------------------------------------

    def test_update_metrics_success(self, registry: ToolRegistry) -> None:
        """Test metrics update after successful execution."""
        tool = WeatherTool()
        registry.register(tool)

        result = ToolCallResult(
            tool_name="weather_check",
            success=True,
            output={"temp": 26},
            error=None,
            latency_ms=350.0,
            cost=0.05,
        )
        registry.update_metrics("weather_check", result)

        metrics = registry.get_metrics("weather_check")
        assert metrics is not None
        assert metrics.total_calls == 1
        assert metrics.latency_ms == 350.0
        assert metrics.avg_cost == 0.05

    def test_update_metrics_failure(self, registry: ToolRegistry) -> None:
        """Test metrics update after failed execution."""
        tool = WeatherTool()
        registry.register(tool)

        # First call: success
        registry.update_metrics(
            "weather_check",
            ToolCallResult(tool_name="weather_check", success=True, latency_ms=200.0, cost=0.02),
        )
        # Second call: failure
        registry.update_metrics(
            "weather_check",
            ToolCallResult(
                tool_name="weather_check", success=False, error="API down", latency_ms=500.0, cost=0.0
            ),
        )

        metrics = registry.get_metrics("weather_check")
        assert metrics is not None
        assert metrics.total_calls == 2
        # Accuracy should have dropped from 1.0 to 0.5
        assert 0.4 <= metrics.accuracy <= 0.6

    # ------------------------------------------------------------------
    # Execute with fallback
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_execute_with_fallback_success(self, populated_registry: ToolRegistry) -> None:
        """Test execute_with_fallback — primary succeeds."""
        # weather_check has no fallback chain, but executes ok
        result, used = await populated_registry.execute_with_fallback(
            "weather_check", {"destination": "Mumbai", "date": "2026-08-15"}
        )
        assert result.success is True
        assert used == "weather_check"

    @pytest.mark.asyncio
    async def test_execute_with_fallback_unregistered(self, registry: ToolRegistry) -> None:
        """Test execute_with_fallback with unregistered tool."""
        result, used = await registry.execute_with_fallback(
            "nonexistent", {}
        )
        assert result.success is False
        assert "not registered" in (result.error or "").lower()

    # ------------------------------------------------------------------
    # Discovery
    # ------------------------------------------------------------------

    def test_discover_tools(self, populated_registry: ToolRegistry) -> None:
        """Test tool discovery lists all registered tools."""
        tools = populated_registry.discover_tools()
        assert len(tools) == 7
        assert "flight_search" in tools
        assert "train_search" in tools
        assert "hotel_search" in tools

    def test_get_available_tools(self, populated_registry: ToolRegistry) -> None:
        """Test get_available_tools returns registrations."""
        registrations = populated_registry.get_available_tools()
        assert len(registrations) == 7
        for reg in registrations:
            assert isinstance(reg, ToolRegistration)

    # ------------------------------------------------------------------
    # All-metrics view
    # ------------------------------------------------------------------

    def test_get_all_metrics(self, populated_registry: ToolRegistry) -> None:
        """Test get_all_metrics returns all tool metrics."""
        all_metrics = populated_registry.get_all_metrics()
        assert len(all_metrics) >= 4  # at least 4 tools have metrics
        assert "flight_search" in all_metrics
        assert isinstance(all_metrics["flight_search"], ToolMetrics)

    def test_get_metrics_nonexistent(self, registry: ToolRegistry) -> None:
        """Test get_metrics returns None for unregistered tool."""
        assert registry.get_metrics("nonexistent") is None
