"""
INNOVATION #4: Risk Predictor.

Before every expensive action the agent predicts:
- Failure Risk (how likely is this to fail?)
- Cost (how much will this cost?)
- Security (any security concerns?)
- User Approval Needed (should we pause for approval?)

Uses a combination of:
- Historical data from LearningMemory (optional)
- Tool metrics from ToolRegistry
- LLM-based reasoning for complex assessments
"""

from __future__ import annotations

import logging
import re
from typing import Any

from src.core.constants import RiskLevel
from src.core.models import RiskAssessment, TaskNode
from src.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)

# Security-sensitive keywords that should trigger extra scrutiny
_SECURITY_KEYWORDS = {
    "payment", "credit_card", "cvv", "password", "otp", "aadhaar",
    "pan_card", "bank_account", "ssn", "passport", "delete", "cancel",
    "refund", "transfer", "pay", "charge",
}

# Actions that inherently require user approval (Write / Transaction)
_APPROVAL_ACTIONS = {"payment", "booking", "reservation", "purchase", "transfer", "cancel",
                     "pay", "book", "buy", "order", "checkout", "fund", "refund", "delete", "execute", "run"}

# Safe Read actions that should be auto-approved
_SAFE_ACTIONS = {"search", "lookup", "fetch", "get", "check", "read", "view", "list"}

# Numeric ordering for risk-level comparison (StrEnum compares alphabetically)
_RISK_ORDER = {
    RiskLevel.LOW: 0,
    RiskLevel.MEDIUM: 1,
    RiskLevel.HIGH: 2,
    RiskLevel.CRITICAL: 3,
}


def _max_risk(a: RiskLevel, b: RiskLevel) -> RiskLevel:
    """Return the higher of two risk levels based on numeric ordering."""
    if _RISK_ORDER.get(b, 0) > _RISK_ORDER.get(a, 0):
        return b
    return a


class RiskPredictor:
    """
    Innovation #4: Risk Predictor.

    Assesses risk for tool invocations and tasks before execution.
    """

    def __init__(
        self,
        tool_registry: ToolRegistry,
        memory: Any = None,
    ) -> None:
        self.tool_registry = tool_registry
        self.memory = memory  # optional LearningMemory reference

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def assess(
        self,
        action: str,
        tool_name: str,
        input_data: dict[str, Any],
        cost_threshold: float = 100.0,
    ) -> RiskAssessment:
        """
        Assess risk of an action before executing it.

        1. Check tool metrics for failure rate.
        2. Check cost estimate vs threshold.
        3. Check security flags (payment, personal data, destructive ops).
        4. Use LLM for overall risk reasoning.
        5. Return a RiskAssessment with confidence score.

        Triggers approval if:
        - Cost > threshold
        - Action involves payment/booking
        - Security flags present
        - Historical failure rate > 0.3
        """
        tool_metrics = self.tool_registry.get_metrics(tool_name)
        failure_prob = 0.0
        cost_estimate = 0.0
        security_flags: list[str] = []
        risk_level = RiskLevel.LOW
        reasoning_parts: list[str] = []

        # ---- 1. Historical failure rate from tool metrics ----
        if tool_metrics is not None:
            failure_prob = min(tool_metrics.failure_rate, 1.0)
            if tool_metrics.failure_rate > 0.3:
                risk_level = _max_risk(risk_level, RiskLevel.MEDIUM)
                reasoning_parts.append(
                    f"Tool {tool_name!r} has high historical failure rate "
                    f"({tool_metrics.failure_rate:.1%})."
                )
            elif tool_metrics.failure_rate > 0.1:
                risk_level = _max_risk(risk_level, RiskLevel.LOW)
                reasoning_parts.append(
                    f"Tool {tool_name!r} has moderate failure rate "
                    f"({tool_metrics.failure_rate:.1%})."
                )
            else:
                reasoning_parts.append(
                    f"Tool {tool_name!r} has low historical failure rate "
                    f"({tool_metrics.failure_rate:.1%})."
                )

        # ---- 2. Cost estimate ----
        cost_estimate = self._estimate_cost(action, tool_name, input_data)
        if cost_estimate > cost_threshold:
            risk_level = _max_risk(risk_level, RiskLevel.HIGH)
            reasoning_parts.append(
                f"Estimated cost ${cost_estimate:.2f} exceeds threshold "
                f"${cost_threshold:.2f}."
            )
        elif cost_estimate > cost_threshold * 0.5:
            risk_level = _max_risk(risk_level, RiskLevel.MEDIUM)
            reasoning_parts.append(
                f"Estimated cost ${cost_estimate:.2f} is within 50% of threshold."
            )
        else:
            reasoning_parts.append(f"Estimated cost ${cost_estimate:.2f} is within budget.")

        # ---- 3. Security flags ----
        security_flags = self._check_security(action, input_data)
        if security_flags:
            risk_level = _max_risk(risk_level, RiskLevel.HIGH)
            reasoning_parts.append(
                f"Security flags detected: {', '.join(security_flags)}."
            )

        # ---- 4. LLM risk analysis ----
        llm_analysis = await self._llm_risk_analysis(action, tool_name, input_data)
        llm_risk_str = llm_analysis.get("risk_level", "LOW")
        llm_risk = RiskLevel(llm_risk_str)
        risk_level = _max_risk(risk_level, llm_risk)

        llm_reasoning = llm_analysis.get("reasoning", "")
        if llm_reasoning:
            reasoning_parts.append(f"LLM analysis: {llm_reasoning}")

        confidence = 0.0
        if tool_metrics is not None and tool_metrics.total_calls > 0:
            confidence = min(0.3 + tool_metrics.total_calls * 0.02, 0.9)

        requires_approval = self._requires_approval(
            action, input_data, risk_level, cost_estimate, cost_threshold, security_flags
        )

        return RiskAssessment(
            risk_level=risk_level,
            confidence=round(confidence, 2),
            failure_probability=round(failure_prob, 4),
            cost_estimate=round(cost_estimate, 2),
            security_flags=security_flags,
            requires_approval=requires_approval,
            reasoning=" | ".join(reasoning_parts),
        )

    async def assess_task(self, task: TaskNode) -> RiskAssessment:
        """Convenience wrapper for assessing a TaskNode."""
        action = task.input.get("action", "unknown")
        tool_name = task.input.get("tool_name", "unknown")
        return await self.assess(action, tool_name, task.input)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _requires_approval(
        self,
        action: str,
        input_data: dict[str, Any],
        risk: RiskLevel,
        cost_estimate: float = 0.0,
        cost_threshold: float = 100.0,
        security_flags: list[str] | None = None,
    ) -> bool:
        """Determine if human approval is needed."""
        if risk == RiskLevel.CRITICAL:
            return True

        if cost_estimate > cost_threshold:
            return True

        action_lower = action.lower()
        
        # If it explicitly matches a safe "Read" action, we can bypass approval
        # (Assuming the risk level isn't HIGH/CRITICAL and cost is low, which is already handled above)
        if any(keyword in action_lower for keyword in _SAFE_ACTIONS):
            if risk in (RiskLevel.LOW, RiskLevel.MEDIUM):
                return False
                
        for keyword in _APPROVAL_ACTIONS:
            if keyword in action_lower:
                return True

        if security_flags:
            return True

        return False

    def _estimate_cost(
        self,
        action: str,
        tool_name: str,
        input_data: dict[str, Any],
    ) -> float:
        """Estimate the cost of a tool invocation based on metrics and input."""
        metrics = self.tool_registry.get_metrics(tool_name)
        if metrics is not None and metrics.avg_cost > 0:
            base_cost = metrics.avg_cost
        else:
            base_cost = 2.0  # default estimate for unknown tools

        # Scale cost based on action type
        multipliers = {
            "booking": 3.0,
            "search": 0.5,
            "check": 0.3,
            "send": 0.2,
        }
        action_lower = action.lower()
        multiplier = 1.0
        for keyword, mult in multipliers.items():
            if keyword in action_lower:
                multiplier = mult
                break

        return base_cost * multiplier

    def _check_security(
        self,
        action: str,
        input_data: dict[str, Any],
    ) -> list[str]:
        """Check input data for security-sensitive content."""
        flags: list[str] = []
        action_lower = action.lower()

        # Check against security keywords
        for keyword in _SECURITY_KEYWORDS:
            if keyword in action_lower:
                flags.append(f"Action contains sensitive keyword: {keyword}")
                break

        # Sensitive field names to detect in input data keys
        sensitive_keys = {
            "password", "credit_card", "credit", "card", "ssn",
            "cvv", "otp", "aadhaar", "pan", "pan_card",
            "bank_account", "passport", "card_number",
        }

        # Values whose presence in input data is inherently sensitive
        sensitive_values = {"payment", "password", "credit", "card", "cvv", "otp", "aadhaar"}

        for key, value in input_data.items():
            key_lower = key.lower()

            # Check if the key name itself indicates a sensitive field
            for sk in sensitive_keys:
                if sk in key_lower:
                    flag = f"Input '{key}' is a sensitive field"
                    if flag not in flags:
                        flags.append(flag)
                    break

            # Scan input data values for sensitive patterns
            if isinstance(value, str):
                value_lower = value.lower()
                for sensitive in sensitive_values:
                    if sensitive in value_lower:
                        flag = f"Input '{key}' may contain sensitive data"
                        if flag not in flags:
                            flags.append(flag)

                # Check for credit-card-like number patterns (digits with dashes/spaces)
                clean = re.sub(r"[\s\-]+", "", value)
                if clean.isdigit() and 13 <= len(clean) <= 19:
                    flag = f"Input '{key}' contains potential credit card number"
                    if flag not in flags:
                        flags.append(flag)

        return flags

    async def _llm_risk_analysis(
        self,
        action: str,
        tool_name: str,
        input_data: dict[str, Any],
    ) -> dict[str, Any]:
        """Use LLM to analyse risk factors.

        In a production system this would call an actual LLM.  Here we
        simulate the analysis with a rule-based fallback that produces
        plausible reasoning.
        """
        # Simulate LLM risk analysis based on heuristics
        high_risk_tools = {"payment", "refund", "cancel_booking"}
        medium_risk_tools = {"flight_search", "hotel_search", "train_search"}

        action_lower = action.lower()
        tool_lower = tool_name.lower()

        if any(kw in action_lower for kw in high_risk_tools):
            risk_level = "HIGH"
            reasoning = (
                f"Action '{action}' typically involves financial transactions "
                f"which carry inherent risk."
            )
        elif any(kw in tool_lower for kw in medium_risk_tools):
            risk_level = "MEDIUM"
            reasoning = (
                f"Tool '{tool_name}' performs bookings which may have "
                f"cancellation fees or price changes."
            )
        else:
            risk_level = "LOW"
            reasoning = (
                f"Action '{action}' on tool '{tool_name}' appears to be "
                f"low-risk based on type and context."
            )

        return {"risk_level": risk_level, "reasoning": reasoning}
