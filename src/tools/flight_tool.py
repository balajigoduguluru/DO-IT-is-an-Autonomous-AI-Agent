"""Flight search and booking tool with mock fallback."""

from __future__ import annotations

import random
from typing import Any

from src.core.constants import ToolCategory
from src.core.models import ToolRegistration
from src.tools.base_tool import BaseTool


class FlightTool(BaseTool):
    """Flight search and booking tool.

    Simulates a real flight API (e.g. Amadeus).  Can be configured to
    fail on demand so the caller can exercise fallback logic.
    """

    def __init__(self, simulate_failure: bool = False) -> None:
        self._simulate_failure = simulate_failure
        self._cities = {
            ("Mumbai", "Delhi"): {"base_price": 4500, "airlines": ["IndiGo", "SpiceJet", "Vistara"]},
            ("Delhi", "Mumbai"): {"base_price": 4500, "airlines": ["IndiGo", "SpiceJet", "Vistara"]},
            ("Mumbai", "Bangalore"): {"base_price": 3500, "airlines": ["IndiGo", "AirAsia", "GoFirst"]},
            ("Bangalore", "Mumbai"): {"base_price": 3500, "airlines": ["IndiGo", "AirAsia", "GoFirst"]},
            ("Delhi", "Bangalore"): {"base_price": 5500, "airlines": ["Vistara", "Air India", "IndiGo"]},
            ("Bangalore", "Delhi"): {"base_price": 5500, "airlines": ["Vistara", "Air India", "IndiGo"]},
            ("Mumbai", "Goa"): {"base_price": 3000, "airlines": ["SpiceJet", "GoFirst", "Akasa Air"]},
            ("Goa", "Mumbai"): {"base_price": 3000, "airlines": ["SpiceJet", "GoFirst", "Akasa Air"]},
            ("Delhi", "Goa"): {"base_price": 6000, "airlines": ["IndiGo", "Vistara", "Akasa Air"]},
            ("Goa", "Delhi"): {"base_price": 6000, "airlines": ["IndiGo", "Vistara", "Akasa Air"]},
        }

    def simulate_flight_api_failure(self, should_fail: bool) -> None:
        """Toggle simulated failure mode for demonstration purposes."""
        self._simulate_failure = should_fail

    def get_registration(self) -> ToolRegistration:
        return ToolRegistration(
            name="flight_search",
            description="Search for available flights between origin and destination on a given date.",
            category=ToolCategory.FLIGHT,
            provider="Amadeus",
            fallback_chain=["flight_search_mock", "train_search"],
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

        # Simulate API failure for demo
        if self._simulate_failure:
            raise RuntimeError(
                "Flight API returned 503 Service Unavailable: "
                "Amadeus API is temporarily down for maintenance."
            )

        route = self._cities.get(route_key)
        if route is None:
            # Unknown route — return a generic result
            base_price = random.randint(4000, 15000)
            airlines = ["IndiGo", "SpiceJet", "Air India", "Vistara", "GoFirst"]
        else:
            base_price = route["base_price"]
            airlines = route["airlines"]

        flights = []
        for i, airline in enumerate(airlines):
            price_variation = random.randint(-500, 500)
            price = max(1000, base_price + price_variation)

            if budget is not None and price > float(budget):
                continue

            departure_hour = 6 + (i * 3) + random.randint(0, 1)
            arrival_hour = departure_hour + 1 + random.randint(0, 2)
            departure = f"{departure_hour:02d}:{random.randint(0, 59):02d}"
            arrival = f"{arrival_hour:02d}:{random.randint(0, 59):02d}"

            flights.append({
                "airline": airline,
                "flight_number": f"{airline[:2].upper()}{random.randint(100, 999)}",
                "departure": departure,
                "arrival": arrival,
                "duration_minutes": (arrival_hour - departure_hour) * 60,
                "price": round(price, 2),
                "currency": "INR",
                "stops": random.choice([0, 0, 0, 1]),
            })

        if not flights:
            return {"flights": [], "total_options": 0, "message": "No flights found within budget."}

        return {"flights": flights, "total_options": len(flights), "currency": "INR"}


class FlightToolMock(BaseTool):
    """Mock flight tool - always returns data for demo/testing."""

    def get_registration(self) -> ToolRegistration:
        return ToolRegistration(
            name="flight_search_mock",
            description="Mock flight search - always returns sample flight data for testing.",
            category=ToolCategory.FLIGHT,
            provider="MockAPI",
            fallback_chain=["train_search"],
            input_schema={
                "type": "object",
                "properties": {
                    "origin": {"type": "string"},
                    "destination": {"type": "string"},
                    "date": {"type": "string"},
                    "budget": {"type": "number"},
                },
                "required": ["origin", "destination", "date"],
            },
        )

    async def execute(self, **kwargs: Any) -> dict[str, Any]:
        origin = str(kwargs.get("origin", "Mumbai")).strip()
        destination = str(kwargs.get("destination", "Delhi")).strip()
        _date = kwargs.get("date", "2026-08-15")

        if not origin or not destination:
            raise ValueError("origin and destination are required")

        # Hardcoded realistic mock data
        mock_flights = [
            {
                "airline": "IndiGo",
                "flight_number": "6E-213",
                "departure": "06:30",
                "arrival": "08:15",
                "duration_minutes": 105,
                "price": 4299.0,
                "currency": "INR",
                "stops": 0,
            },
            {
                "airline": "Vistara",
                "flight_number": "UK-945",
                "departure": "09:45",
                "arrival": "11:55",
                "duration_minutes": 130,
                "price": 5899.0,
                "currency": "INR",
                "stops": 0,
            },
            {
                "airline": "SpiceJet",
                "flight_number": "SG-817",
                "departure": "14:20",
                "arrival": "16:10",
                "duration_minutes": 110,
                "price": 3799.0,
                "currency": "INR",
                "stops": 0,
            },
            {
                "airline": "Air India",
                "flight_number": "AI-671",
                "departure": "18:00",
                "arrival": "20:30",
                "duration_minutes": 150,
                "price": 7199.0,
                "currency": "INR",
                "stops": 0,
            },
        ]

        budget = kwargs.get("budget")
        if budget is not None:
            mock_flights = [f for f in mock_flights if f["price"] <= float(budget)]

        return {"flights": mock_flights, "total_options": len(mock_flights), "currency": "INR"}
