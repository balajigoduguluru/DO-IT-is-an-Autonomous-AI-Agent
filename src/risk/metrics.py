"""Metrics collection and computation utilities."""

from __future__ import annotations

from src.core.models import ToolMetrics


class MetricsCollector:
    """Collects and computes metrics for tools and execution."""

    @staticmethod
    def compute_confidence(success_count: int, total_count: int) -> float:
        """Compute confidence score from historical data.

        Uses a Bayesian-inspired formula with pseudo-counts to avoid
        extreme values when data is scarce.

        Args:
            success_count: Number of successful executions.
            total_count: Total number of executions observed.

        Returns:
            A confidence score between 0.0 and 1.0.
        """
        if total_count <= 0:
            return 0.0

        # Add pseudo-counts (1 success, 1 failure) for a weak prior
        pseudo_successes = 1
        pseudo_total = 2

        adjusted_successes = success_count + pseudo_successes
        adjusted_total = total_count + pseudo_total

        # Lower confidence when data is scarce
        data_confidence = min(1.0, total_count / 20.0)  # reaches 1.0 at 20 samples
        raw_estimate = adjusted_successes / adjusted_total

        return round(raw_estimate * data_confidence + 0.5 * (1.0 - data_confidence), 4)

    @staticmethod
    def compute_weighted_score(metrics: ToolMetrics) -> float:
        """Compute weighted marketplace score for tool selection.

        The score is a weighted combination of:
            - accuracy (40%)
            - (1 - failure_rate) (30%)
            - (1 - normalised_latency) (20%)
            - (1 - normalised_cost) (10%)

        Args:
            metrics: The tool's performance metrics.

        Returns:
            A score between 0.0 and 1.0.
        """
        norm_lat = MetricsCollector.latency_normalize(metrics.latency_ms)
        norm_cost = MetricsCollector.cost_normalize(metrics.avg_cost)

        score = (
            metrics.accuracy * 0.4
            + (1.0 - metrics.failure_rate) * 0.3
            + (1.0 - min(norm_lat, 1.0)) * 0.2
            + (1.0 - min(norm_cost, 1.0)) * 0.1
        )
        return round(score, 4)

    @staticmethod
    def latency_normalize(latency_ms: float, max_latency: float = 10000) -> float:
        """Normalize latency to a 0-1 range.

        Values above *max_latency* are clamped to 1.0.

        Args:
            latency_ms: Latency in milliseconds.
            max_latency: The value at which output saturates at 1.0.

        Returns:
            A normalised value in [0.0, 1.0].
        """
        if latency_ms <= 0:
            return 0.0
        return min(latency_ms / max_latency, 1.0)

    @staticmethod
    def cost_normalize(cost: float, max_cost: float = 100) -> float:
        """Normalize cost to a 0-1 range.

        Values above *max_cost* are clamped to 1.0.

        Args:
            cost: Monetary cost.
            max_cost: The value at which output saturates at 1.0.

        Returns:
            A normalised value in [0.0, 1.0].
        """
        if cost <= 0:
            return 0.0
        return min(cost / max_cost, 1.0)
