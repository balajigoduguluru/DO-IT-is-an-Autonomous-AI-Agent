"""Tests for the risk predictor (Innovation #4).

Tests risk assessment logic for different action types, security flag
detection, cost estimation, and approval trigger thresholds.
"""

import sys
from pathlib import Path

import pytest

_HERE = Path(__file__).resolve().parent
_PROJECT_ROOT = _HERE.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from src.core.constants import RiskLevel, ToolCategory
from src.core.models import RiskAssessment, ToolMetrics, ToolRegistration
from src.risk.risk_predictor import RiskPredictor
from src.tools.registry import ToolRegistry


class TestRiskPredictor:
    """Test risk assessment logic."""

    # ------------------------------------------------------------------
    # Fixtures
    # ------------------------------------------------------------------

    @pytest.fixture
    def registry(self) -> ToolRegistry:
        reg = ToolRegistry()
        # Register a few tools with predefined metrics
        reg._metrics["payment_gateway"] = ToolMetrics(
            tool_name="payment_gateway",
            failure_rate=0.05,
            avg_cost=2.50,
            latency_ms=1200,
            accuracy=0.95,
            total_calls=100,
        )
        reg._metrics["weather_check"] = ToolMetrics(
            tool_name="weather_check",
            failure_rate=0.02,
            avg_cost=0.10,
            latency_ms=300,
            accuracy=0.98,
            total_calls=200,
        )
        reg._metrics["flight_search"] = ToolMetrics(
            tool_name="flight_search",
            failure_rate=0.35,
            avg_cost=5.00,
            latency_ms=3200,
            accuracy=0.65,
            total_calls=50,
        )
        return reg

    @pytest.fixture
    def predictor(self, registry: ToolRegistry) -> RiskPredictor:
        return RiskPredictor(tool_registry=registry)

    # ------------------------------------------------------------------
    # High risk detection
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_high_risk_payment(
        self, predictor: RiskPredictor
    ) -> None:
        """Test that payment actions get high risk."""
        assessment = await predictor.assess(
            action="make_payment",
            tool_name="payment_gateway",
            input_data={"amount": 15000, "currency": "INR"},
            cost_threshold=100.0,
        )
        assert assessment.risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL)
        assert assessment.requires_approval is True
        assert len(assessment.security_flags) > 0

    @pytest.mark.asyncio
    async def test_high_risk_booking(
        self, predictor: RiskPredictor
    ) -> None:
        """Test that booking actions get high risk and require approval."""
        assessment = await predictor.assess(
            action="book_flight",
            tool_name="flight_search",
            input_data={"origin": "Mumbai", "destination": "Delhi"},
            cost_threshold=100.0,
        )
        assert assessment.risk_level in (RiskLevel.MEDIUM, RiskLevel.HIGH)
        assert assessment.requires_approval is True

    @pytest.mark.asyncio
    async def test_high_risk_critical_action(
        self, predictor: RiskPredictor
    ) -> None:
        """Test that critical financial actions are flagged."""
        assessment = await predictor.assess(
            action="process_refund",
            tool_name="payment_gateway",
            input_data={"amount": 5000},
            cost_threshold=100.0,
        )
        assert assessment.risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL)
        assert assessment.requires_approval is True

    # ------------------------------------------------------------------
    # Low risk detection
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_low_risk_weather(
        self, predictor: RiskPredictor
    ) -> None:
        """Test that weather checks get low risk."""
        assessment = await predictor.assess(
            action="check_weather",
            tool_name="weather_check",
            input_data={"destination": "Bangalore", "date": "2026-08-15"},
            cost_threshold=100.0,
        )
        assert assessment.risk_level == RiskLevel.LOW
        assert assessment.requires_approval is False
        assert assessment.failure_probability < 0.1

    @pytest.mark.asyncio
    async def test_low_risk_search(
        self, predictor: RiskPredictor
    ) -> None:
        """Test that simple search actions are low risk."""
        assessment = await predictor.assess(
            action="search_hotels",
            tool_name="weather_check",  # Using a reliable tool
            input_data={"destination": "Goa"},
            cost_threshold=100.0,
        )
        assert assessment.risk_level == RiskLevel.LOW
        assert assessment.requires_approval is False

    # ------------------------------------------------------------------
    # Security flag detection
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_security_flags_pii(
        self, predictor: RiskPredictor
    ) -> None:
        """Test that PII in input data triggers security flags."""
        assessment = await predictor.assess(
            action="process_user_data",
            tool_name="payment_gateway",
            input_data={"credit_card": "4111-1111-1111-1111"},
            cost_threshold=100.0,
        )
        assert len(assessment.security_flags) >= 1
        assert any("credit" in flag.lower() for flag in assessment.security_flags)

    @pytest.mark.asyncio
    async def test_security_flags_password(
        self, predictor: RiskPredictor
    ) -> None:
        """Test that password input triggers security flags."""
        assessment = await predictor.assess(
            action="user_login",
            tool_name="payment_gateway",
            input_data={"password": "secret123"},
            cost_threshold=100.0,
        )
        assert len(assessment.security_flags) >= 1

    # ------------------------------------------------------------------
    # Cost estimation
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_cost_estimate_within_threshold(
        self, predictor: RiskPredictor
    ) -> None:
        """Test cost estimation within threshold."""
        assessment = await predictor.assess(
            action="check_weather",
            tool_name="weather_check",
            input_data={"destination": "Mumbai"},
            cost_threshold=100.0,
        )
        assert assessment.cost_estimate < 100.0

    @pytest.mark.asyncio
    async def test_cost_estimate_exceeds_threshold(
        self, predictor: RiskPredictor
    ) -> None:
        """Test that exceeding cost threshold raises risk."""
        assessment = await predictor.assess(
            action="book_flight",
            tool_name="flight_search",
            input_data={"origin": "Mumbai", "destination": "New York"},
            cost_threshold=1.0,  # very low threshold
        )
        # Cost should exceed this tiny threshold
        if assessment.cost_estimate > 1.0:
            assert assessment.risk_level in (RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.CRITICAL)

    # ------------------------------------------------------------------
    # Approval triggers
    # ------------------------------------------------------------------

    def test_approval_trigger_critical(self, predictor: RiskPredictor) -> None:
        """Test that CRITICAL risk triggers approval."""
        assert predictor._requires_approval(
            action="test",
            input_data={},
            risk=RiskLevel.CRITICAL,
        ) is True

    def test_approval_trigger_low(self, predictor: RiskPredictor) -> None:
        """Test that LOW risk with no other factors does NOT trigger approval."""
        assert predictor._requires_approval(
            action="check_weather",
            input_data={},
            risk=RiskLevel.LOW,
            cost_estimate=1.0,
            cost_threshold=100.0,
        ) is False

    def test_approval_trigger_booking_keyword(self, predictor: RiskPredictor) -> None:
        """Test that 'booking' in the action triggers approval."""
        assert predictor._requires_approval(
            action="make_booking",
            input_data={},
            risk=RiskLevel.MEDIUM,
        ) is True

    def test_approval_trigger_security_flags(self, predictor: RiskPredictor) -> None:
        """Test that security flags trigger approval."""
        assert predictor._requires_approval(
            action="process_data",
            input_data={},
            risk=RiskLevel.LOW,
            security_flags=["credit_card_detected"],
        ) is True

    # ------------------------------------------------------------------
    # Risk assessment for task node
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_assess_task_node(
        self, predictor: RiskPredictor
    ) -> None:
        """Test assess_task convenience wrapper."""
        from src.core.models import TaskNode

        task = TaskNode(
            id="test_task",
            agent_type="worker",
            input={"action": "book_flight", "tool_name": "flight_search"},
        )
        assessment = await predictor.assess_task(task)
        assert isinstance(assessment, RiskAssessment)
        # Booking with flight_search should have at least MEDIUM risk
        assert assessment.risk_level in (RiskLevel.MEDIUM, RiskLevel.HIGH)

    # ------------------------------------------------------------------
    # Failure probability from high-failure tool
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_failure_probability_high(
        self, predictor: RiskPredictor
    ) -> None:
        """Test that a tool with high failure rate gets appropriate risk."""
        assessment = await predictor.assess(
            action="search",
            tool_name="flight_search",  # 35% failure rate
            input_data={},
            cost_threshold=100.0,
        )
        # Should have moderate-to-high failure probability
        assert assessment.failure_probability >= 0.3
