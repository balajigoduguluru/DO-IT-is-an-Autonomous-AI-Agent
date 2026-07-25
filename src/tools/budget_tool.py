"""Budget calculation and tracking tool."""

from __future__ import annotations

from typing import Any

from src.core.constants import ToolCategory
from src.core.models import ToolRegistration
from src.tools.base_tool import BaseTool


class BudgetTool(BaseTool):
    """Budget calculation and tracking tool.

    Accepts a list of expense items, each with a category, estimated cost,
    and actual cost.  Returns subtotals by category, totals, remaining
    budget, and a human-readable breakdown.
    """

    def get_registration(self) -> ToolRegistration:
        return ToolRegistration(
            name="budget_calculator",
            description="Calculate and track budget across expense categories. Accepts items with estimated/actual costs.",
            category=ToolCategory.BUDGET,
            provider="Internal",
            input_schema={
                "type": "object",
                "properties": {
                    "items": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "category": {"type": "string"},
                                "estimated_cost": {"type": "number"},
                                "actual_cost": {"type": "number"},
                            },
                            "required": ["category", "estimated_cost"],
                        },
                    },
                    "total_budget": {"type": "number", "description": "Overall budget cap"},
                    "currency": {"type": "string", "description": "Currency code (default INR)"},
                },
                "required": ["items", "total_budget"],
            },
        )

    async def execute(self, **kwargs: Any) -> dict[str, Any]:
        items_raw = kwargs.get("items", [])
        total_budget = kwargs.get("total_budget")
        currency = str(kwargs.get("currency", "INR")).upper()

        if not items_raw:
            raise ValueError("items list is required and must not be empty")

        if total_budget is None:
            raise ValueError("total_budget is required")

        total_budget = float(total_budget)
        if total_budget <= 0:
            raise ValueError("total_budget must be positive")

        # Normalise items
        items = []
        for idx, item in enumerate(items_raw):
            if not isinstance(item, dict):
                raise ValueError(f"Item at index {idx} must be a dict")

            category = str(item.get("category", "General"))
            estimated = float(item.get("estimated_cost", 0))
            actual = item.get("actual_cost")
            actual = float(actual) if actual is not None else None

            items.append({
                "category": category,
                "estimated_cost": estimated,
                "actual_cost": actual,
            })

        # Compute subtotals by category
        subtotals_by_category: dict[str, dict[str, float]] = {}
        for item in items:
            cat = item["category"]
            if cat not in subtotals_by_category:
                subtotals_by_category[cat] = {"estimated": 0.0, "actual": 0.0}
            subtotals_by_category[cat]["estimated"] += item["estimated_cost"]
            if item["actual_cost"] is not None:
                subtotals_by_category[cat]["actual"] += item["actual_cost"]

        total_estimated = sum(item["estimated_cost"] for item in items)
        total_actual = sum(
            item["actual_cost"] for item in items if item["actual_cost"] is not None
        )

        remaining = round(total_budget - total_actual, 2)
        within_budget = total_actual <= total_budget if total_actual > 0 else True

        # Human-readable breakdown
        lines = [f"Budget Breakdown ({currency}):"]
        lines.append(f"{'='*50}")
        for item in items:
            actual_str = (
                f"  {item['actual_cost']:>10,.2f}" if item["actual_cost"] is not None
                else "  {'—':>10}"
            )
            lines.append(
                f"  {item['category']:<20}  Est: {item['estimated_cost']:>8,.2f}  "
                f"Actual:{actual_str}"
            )
        lines.append(f"{'='*50}")
        lines.append(f"  {'Total Estimated':<20}  {total_estimated:>23,.2f}")
        if total_actual > 0:
            lines.append(f"  {'Total Actual':<20}  {total_actual:>23,.2f}")
            lines.append(f"  {'Total Budget':<20}  {total_budget:>23,.2f}")
            lines.append(f"  {'Remaining':<20}  {remaining:>23,.2f}")
            lines.append(f"  {'Within Budget?':<20}  {'Yes' if within_budget else 'No':>23}")
        breakdown_text = "\n".join(lines)

        return {
            "items": items,
            "subtotals_by_category": subtotals_by_category,
            "total_estimated": round(total_estimated, 2),
            "total_actual": round(total_actual, 2) if total_actual > 0 else None,
            "total_budget": total_budget,
            "remaining": remaining,
            "within_budget": within_budget,
            "currency": currency,
            "breakdown": breakdown_text,
        }
