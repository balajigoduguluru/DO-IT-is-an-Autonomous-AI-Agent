"""User preference management backed by LearningMemory."""

from __future__ import annotations

from typing import Any

from src.memory.learning_memory import LearningMemory


class UserPreferenceManager:
    """Read and write user-specific preferences that influence planning decisions."""

    # Well-known preference keys
    KEY_TRANSPORT = "transport"
    KEY_BUDGET_STYLE = "budget_style"

    def __init__(self, memory: LearningMemory) -> None:
        self.memory = memory

    # ------------------------------------------------------------------
    # Common preference lookups
    # ------------------------------------------------------------------

    async def get_transport_preference(self) -> str | None:
        """Return the preferred transport mode, if set.

        Possible values: ``"flight"``, ``"train"``, ``"bus"``, etc.
        """
        raw = await self.memory.get_preference(self.KEY_TRANSPORT)
        if raw is None:
            return None
        return raw.get("mode")

    async def get_budget_style(self) -> str | None:
        """Return the budget style preference, if set.

        Possible values: ``"budget"``, ``"moderate"``, ``"luxury"``.
        """
        raw = await self.memory.get_preference(self.KEY_BUDGET_STYLE)
        if raw is None:
            return None
        return raw.get("style")

    # ------------------------------------------------------------------
    # Generic preference management
    # ------------------------------------------------------------------

    async def set_preference(self, category: str, value: Any) -> None:
        """Persist a user preference.

        ``value`` is wrapped in a dict ``{"value": value}`` if it is not
        already a dict, so that it conforms to the storage format of
        :meth:`LearningMemory.record_preference`.

        Args:
            category: Preference key (e.g. ``"transport"``, ``"budget_style"``).
            value: The value to store (scalar, list, or dict).
        """
        payload: dict[str, Any] = (
            value if isinstance(value, dict) else {"value": value}
        )
        await self.memory.record_preference(
            key=category,
            value=payload,
            session_id="_preferences_",
        )

    async def apply_preferences(self, plan: dict[str, Any]) -> dict[str, Any]:
        """Modify a plan dictionary to match stored user preferences.

        Currently applies:
        - ``budget_style``: adjusts cost-related fields.
        - ``transport``: sets the ``preferred_transport`` key in the plan.

        Args:
            plan: The plan dict to modify (e.g. output from a planner).

        Returns:
            The modified plan (same reference, also returned for convenience).
        """
        plan = dict(plan)  # shallow copy

        budget_style = await self.get_budget_style()
        if budget_style:
            plan["budget_style"] = budget_style
            multipliers = {"budget": 0.7, "moderate": 1.0, "luxury": 1.5}
            if (mult := multipliers.get(budget_style)) is not None:
                # Scale any top-level cost estimate
                current_cost = plan.get("estimated_cost")
                if current_cost is not None:
                    try:
                        plan["estimated_cost"] = round(float(current_cost) * mult, 2)
                    except (ValueError, TypeError):
                        pass
            plan["budget_style_applied"] = True

        transport = await self.get_transport_preference()
        if transport:
            plan["preferred_transport"] = transport
            plan["transport_applied"] = True

        return plan
