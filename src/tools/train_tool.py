"""Train search tool -- acts as fallback when flights are unavailable."""

from __future__ import annotations

import random
from typing import Any

from src.core.constants import ToolCategory
from src.core.models import ToolRegistration
from src.tools.base_tool import BaseTool


class TrainTool(BaseTool):
    """Train search tool.

    Designed to serve as a fallback when flight search is unavailable or
    returns errors.  Returns realistic Indian Railways train data.
    """

    def get_registration(self) -> ToolRegistration:
        return ToolRegistration(
            name="train_search",
            description="Search for available trains between origin and destination. Fallback for flight failures.",
            category=ToolCategory.TRANSPORT,
            provider="IndianRailways",
            input_schema={
                "type": "object",
                "properties": {
                    "origin": {"type": "string", "description": "Departure city"},
                    "destination": {"type": "string", "description": "Arrival city"},
                    "date": {"type": "string", "description": "Travel date (YYYY-MM-DD)"},
                    "budget": {"type": "number", "description": "Maximum budget per ticket"},
                },
                "required": ["origin", "destination", "date"],
            },
        )

    # Realistic train routes database
    _routes = {
        ("Mumbai", "Delhi"): [
            {"train_number": "12951", "name": "Mumbai Rajdhani Express", "departure": "16:35", "arrival": "08:30", "classes": {"1A": 4895, "2A": 2855, "3A": 2050, "SL": 750}},
            {"train_number": "22221", "name": "Mumbai Central - Hazrat Nizamuddin AC Duronto", "departure": "23:00", "arrival": "12:55", "classes": {"1A": 4590, "2A": 2680, "3A": 1920}},
            {"train_number": "12309", "name": "Mumbai - Delhi Garib Rath", "departure": "23:55", "arrival": "17:00", "classes": {"3A": 1050}},
        ],
        ("Delhi", "Mumbai"): [
            {"train_number": "12952", "name": "Mumbai Rajdhani Express", "departure": "16:25", "arrival": "08:05", "classes": {"1A": 4895, "2A": 2855, "3A": 2050, "SL": 750}},
            {"train_number": "22222", "name": "Hazrat Nizamuddin - Mumbai Central AC Duronto", "departure": "20:55", "arrival": "10:35", "classes": {"1A": 4590, "2A": 2680, "3A": 1920}},
        ],
        ("Mumbai", "Goa"): [
            {"train_number": "10105", "name": "Mandovi Express", "departure": "06:45", "arrival": "14:50", "classes": {"2A": 1120, "3A": 810, "SL": 330}},
            {"train_number": "22119", "name": "Tejas Express", "departure": "07:05", "arrival": "13:50", "classes": {"CC": 1225, "EC": 2345}},
        ],
        ("Goa", "Mumbai"): [
            {"train_number": "10106", "name": "Mandovi Express", "departure": "15:30", "arrival": "23:30", "classes": {"2A": 1120, "3A": 810, "SL": 330}},
            {"train_number": "22120", "name": "Tejas Express", "departure": "15:10", "arrival": "22:00", "classes": {"CC": 1225, "EC": 2345}},
        ],
        ("Delhi", "Jaipur"): [
            {"train_number": "12413", "name": "Shatabdi Express", "departure": "06:45", "arrival": "11:10", "classes": {"CC": 790, "EC": 1485}},
            {"train_number": "12015", "name": "Shatabdi Express", "departure": "16:00", "arrival": "20:40", "classes": {"CC": 790, "EC": 1485}},
        ],
        ("Jaipur", "Delhi"): [
            {"train_number": "12414", "name": "Shatabdi Express", "departure": "17:55", "arrival": "22:30", "classes": {"CC": 790, "EC": 1485}},
            {"train_number": "12016", "name": "Shatabdi Express", "departure": "06:20", "arrival": "11:00", "classes": {"CC": 790, "EC": 1485}},
        ],
    }

    _class_map = {
        "1A": "First AC",
        "2A": "Second AC",
        "3A": "Third AC",
        "SL": "Sleeper",
        "CC": "Chair Car",
        "EC": "Executive Chair Car",
    }

    async def execute(self, **kwargs: Any) -> dict[str, Any]:
        origin = str(kwargs.get("origin", "")).strip()
        destination = str(kwargs.get("destination", "")).strip()
        date = str(kwargs.get("date", "")).strip()
        budget = kwargs.get("budget")

        if not origin or not destination or not date:
            raise ValueError("origin, destination, and date are required")

        if origin.lower() == destination.lower():
            raise ValueError("origin and destination must be different")

        route_key = (origin.title(), destination.title())
        trains_data = self._routes.get(route_key, [])

        if not trains_data:
            # Generate plausible trains for unknown route
            duration_hours = random.randint(4, 18)
            dep_hour = random.randint(6, 22)
            arr_hour = (dep_hour + duration_hours) % 24
            dep_str = f"{dep_hour:02d}:{random.randint(0, 59):02d}"
            arr_str = f"{arr_hour:02d}:{random.randint(0, 59):02d}"

            trains_data = [
                {
                    "train_number": str(random.randint(10001, 99999)),
                    "name": f"{origin.title()} - {destination.title()} Express",
                    "departure": dep_str,
                    "arrival": arr_str,
                    "classes": {
                        "2A": random.randint(800, 3000),
                        "3A": random.randint(500, 2000),
                        "SL": random.randint(200, 800),
                    },
                }
            ]

        trains = []
        for train in trains_data:
            train_classes = []
            for class_code, price in train["classes"].items():
                if budget is not None and price > float(budget):
                    continue
                train_classes.append({
                    "class_code": class_code,
                    "class_name": self._class_map.get(class_code, class_code),
                    "price": price,
                    "available": random.choice([True, True, True, False]),
                })

            if not train_classes:
                continue

            trains.append({
                "train_number": train["train_number"],
                "name": train["name"],
                "departure": train["departure"],
                "arrival": train["arrival"],
                "classes_available": train_classes,
                "duration": "N/A",
                "runs_on": "Daily",
            })

        if not trains:
            return {"trains": [], "total_options": 0, "message": "No trains found within budget."}

        return {"trains": trains, "total_options": len(trains), "currency": "INR"}
