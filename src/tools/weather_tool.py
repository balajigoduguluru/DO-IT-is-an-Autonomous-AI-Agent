"""Weather forecast tool."""

from __future__ import annotations

import random
from datetime import datetime, timezone
from typing import Any

from src.core.constants import ToolCategory
from src.core.models import ToolRegistration
from src.tools.base_tool import BaseTool


class WeatherTool(BaseTool):
    """Weather forecast tool.

    Returns simulated weather data for a given destination and date.
    The result includes an ``advisable`` boolean that indicates whether
    the conditions are favourable for travel.
    """

    def get_registration(self) -> ToolRegistration:
        return ToolRegistration(
            name="weather_check",
            description="Get weather forecast for a destination on a given date.",
            category=ToolCategory.WEATHER,
            provider="WeatherAPI",
            input_schema={
                "type": "object",
                "properties": {
                    "destination": {"type": "string", "description": "City to check weather for"},
                    "date": {"type": "string", "description": "Date (YYYY-MM-DD)"},
                },
                "required": ["destination", "date"],
            },
        )

    # Base climate profiles for known cities (temp in Celsius)
    _climate_profiles = {
        "mumbai": {"base_high": 32, "base_low": 24, "humid": True, "rainy_months": {6, 7, 8, 9}},
        "delhi": {"base_high": 35, "base_low": 18, "humid": False, "rainy_months": {7, 8}},
        "bangalore": {"base_high": 28, "base_low": 18, "humid": False, "rainy_months": {6, 7, 8, 9, 10}},
        "goa": {"base_high": 31, "base_low": 23, "humid": True, "rainy_months": {6, 7, 8, 9}},
        "chennai": {"base_high": 34, "base_low": 25, "humid": True, "rainy_months": {10, 11, 12}},
        "kolkata": {"base_high": 32, "base_low": 22, "humid": True, "rainy_months": {6, 7, 8, 9}},
        "jaipur": {"base_high": 33, "base_low": 16, "humid": False, "rainy_months": {7, 8}},
    }

    def _get_climate(self, destination: str) -> dict:
        """Return climate profile for a destination, generating one if unknown."""
        key = destination.lower()
        profile = self._climate_profiles.get(key)
        if profile is not None:
            return profile
        # Generate plausible profile for unknown city
        base_high = random.randint(20, 38)
        base_low = base_high - random.randint(6, 14)
        return {
            "base_high": base_high,
            "base_low": base_low,
            "humid": random.choice([True, False]),
            "rainy_months": {random.randint(1, 12) for _ in range(random.randint(2, 4))},
        }

    def _get_month(self, date_str: str) -> int:
        """Extract month number from a date string."""
        try:
            return datetime.strptime(date_str, "%Y-%m-%d").month
        except (ValueError, TypeError):
            return datetime.now(timezone.utc).month

    async def execute(self, **kwargs: Any) -> dict[str, Any]:
        destination = str(kwargs.get("destination", "")).strip()
        date_str = str(kwargs.get("date", "")).strip()

        if not destination or not date_str:
            raise ValueError("destination and date are required")

        month = self._get_month(date_str)
        climate = self._get_climate(destination)

        # Seasonal adjustments
        is_summer = month in {3, 4, 5, 6}
        is_winter = month in {11, 12, 1, 2}
        is_rainy = month in climate["rainy_months"]

        temp_high = climate["base_high"] + (5 if is_summer else -5 if is_winter else 0)
        temp_low = climate["base_low"] + (3 if is_summer else -4 if is_winter else 0)

        # Add some randomness
        temp_high += random.randint(-2, 2)
        temp_low += random.randint(-1, 1)
        temp_high = max(temp_low + 3, temp_high)

        humidity_base = 75 if climate["humid"] else 45
        humidity = humidity_base + (15 if is_rainy else -10 if is_winter else 0) + random.randint(-5, 5)
        humidity = max(20, min(100, humidity))

        conditions = ["Sunny", "Partly Cloudy", "Cloudy", "Light Rain", "Heavy Rain", "Thunderstorm"]
        if is_rainy:
            condition = random.choice(["Light Rain", "Heavy Rain", "Thunderstorm", "Cloudy"])
        elif is_summer:
            condition = random.choice(["Sunny", "Sunny", "Partly Cloudy"])
        elif is_winter:
            condition = random.choice(["Sunny", "Partly Cloudy", "Cloudy"])
        else:
            condition = random.choice(["Sunny", "Partly Cloudy", "Cloudy", "Light Rain"])

        wind_speed = round(random.uniform(5, 40) * (1.2 if is_rainy else 0.8), 1)

        # Determine if advisable for travel
        adverse_conditions = {"Heavy Rain", "Thunderstorm"}
        advisable = (
            condition not in adverse_conditions
            and temp_high < 42
            and temp_low > 5
            and wind_speed < 60
        )

        return {
            "forecast": {
                "temp_high": temp_high,
                "temp_low": temp_low,
                "condition": condition,
                "humidity": humidity,
                "wind_speed": wind_speed,
                "precipitation_chance": random.randint(10, 90) if is_rainy else random.randint(0, 20),
            },
            "advisable": advisable,
            "destination": destination,
            "date": date_str,
        }
