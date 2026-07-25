"""Hotel search and reservation tool."""

from __future__ import annotations

import random
from typing import Any

from src.core.constants import ToolCategory
from src.core.models import ToolRegistration
from src.tools.base_tool import BaseTool


class HotelTool(BaseTool):
    """Hotel search and reservation tool."""

    def get_registration(self) -> ToolRegistration:
        return ToolRegistration(
            name="hotel_search",
            description="Search for available hotels in a destination for given dates and budget.",
            category=ToolCategory.HOTEL,
            provider="BookingAPI",
            input_schema={
                "type": "object",
                "properties": {
                    "destination": {"type": "string", "description": "City to search hotels in"},
                    "check_in": {"type": "string", "description": "Check-in date (YYYY-MM-DD)"},
                    "check_out": {"type": "string", "description": "Check-out date (YYYY-MM-DD)"},
                    "budget": {"type": "number", "description": "Maximum budget per night"},
                    "guests": {"type": "integer", "description": "Number of guests"},
                },
                "required": ["destination", "check_in", "check_out"],
            },
        )

    def _compute_nights(self, check_in: str, check_out: str) -> int:
        """Compute number of nights from check-in/check-out strings."""
        try:
            from datetime import datetime

            in_dt = datetime.strptime(check_in, "%Y-%m-%d")
            out_dt = datetime.strptime(check_out, "%Y-%m-%d")
            nights = (out_dt - in_dt).days
            return max(nights, 1)
        except (ValueError, TypeError):
            return 1

    async def execute(self, **kwargs: Any) -> dict[str, Any]:
        destination = str(kwargs.get("destination", "")).strip()
        check_in = str(kwargs.get("check_in", "")).strip()
        check_out = str(kwargs.get("check_out", "")).strip()
        budget = kwargs.get("budget")
        guests = int(kwargs.get("guests", 1))

        if not destination or not check_in or not check_out:
            raise ValueError("destination, check_in, and check_out are required")

        nights = self._compute_nights(check_in, check_out)

        # Realistic hotel database per destination
        hotel_db = {
            "mumbai": [
                {"name": "Taj Mahal Palace", "rating": 4.8, "price_per_night": 25000, "stars": 5},
                {"name": "The Oberoi Mumbai", "rating": 4.7, "price_per_night": 22000, "stars": 5},
                {"name": "ITC Grand Central", "rating": 4.5, "price_per_night": 12000, "stars": 5},
                {"name": "Hotel Marine Plaza", "rating": 4.3, "price_per_night": 7000, "stars": 4},
                {"name": "Treebo Tryst", "rating": 4.0, "price_per_night": 3000, "stars": 3},
            ],
            "delhi": [
                {"name": "The Imperial", "rating": 4.7, "price_per_night": 20000, "stars": 5},
                {"name": "Taj Mahal Hotel", "rating": 4.6, "price_per_night": 18000, "stars": 5},
                {"name": "The Lalit", "rating": 4.4, "price_per_night": 9500, "stars": 5},
                {"name": "Claridges", "rating": 4.3, "price_per_night": 8000, "stars": 4},
                {"name": "Bloomrooms", "rating": 4.1, "price_per_night": 3500, "stars": 3},
            ],
            "bangalore": [
                {"name": "The Oberoi Bengaluru", "rating": 4.7, "price_per_night": 18000, "stars": 5},
                {"name": "ITC Windsor", "rating": 4.6, "price_per_night": 15000, "stars": 5},
                {"name": "Sheraton Grand", "rating": 4.5, "price_per_night": 11000, "stars": 5},
                {"name": "Royal Orchid", "rating": 4.3, "price_per_night": 6500, "stars": 4},
                {"name": "FabHotel", "rating": 4.0, "price_per_night": 2500, "stars": 3},
            ],
            "goa": [
                {"name": "W Goa", "rating": 4.6, "price_per_night": 15000, "stars": 5},
                {"name": "Taj Fort Aguada", "rating": 4.5, "price_per_night": 12000, "stars": 5},
                {"name": "Alila Diwa", "rating": 4.5, "price_per_night": 10000, "stars": 5},
                {"name": "Sterling Goa", "rating": 4.2, "price_per_night": 5500, "stars": 4},
                {"name": "Zostel", "rating": 4.0, "price_per_night": 1200, "stars": 2},
            ],
        }

        # Dynamic hotel generation for unknown destinations
        hotels_data = hotel_db.get(destination.lower(), [])
        if not hotels_data:
            # Generate reasonable hotels for unknown city
            for i in range(4):
                hotels_data.append({
                    "name": f"{destination.title()} {'Grand' if i == 0 else 'Plaza' if i == 1 else 'Inn' if i == 2 else 'Residency'}",
                    "rating": round(random.uniform(3.5, 5.0), 1),
                    "price_per_night": random.randint(2000, 20000),
                    "stars": random.randint(3, 5),
                })
            hotels_data.sort(key=lambda h: h["price_per_night"])

        hotels = []
        for hotel in hotels_data:
            price_per_night = hotel["price_per_night"]
            if budget is not None and price_per_night > float(budget):
                continue

            total = round(price_per_night * nights, 2)
            hotels.append({
                "name": hotel["name"],
                "rating": hotel["rating"],
                "stars": hotel["stars"],
                "price_per_night": price_per_night,
                "total": total,
                "currency": "INR",
                "available_rooms": random.randint(1, 15),
                "amenities": random.sample(
                    ["WiFi", "Pool", "Gym", "Spa", "Restaurant", "Parking", "AC"],
                    random.randint(2, 5),
                ),
            })

        if not hotels:
            return {
                "hotels": [],
                "total_options": 0,
                "message": "No hotels found within budget.",
            }

        return {
            "hotels": hotels,
            "total_options": len(hotels),
            "destination": destination,
            "check_in": check_in,
            "check_out": check_out,
            "nights": nights,
            "guests": guests,
            "currency": "INR",
        }
