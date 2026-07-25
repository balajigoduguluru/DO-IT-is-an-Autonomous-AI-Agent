"""API layer for the Agentic AI framework.

Exposes the FastAPI application instance and provides REST + WebSocket
endpoints for interacting with the agentic loop.
"""

from src.api.server import app

__all__ = ["app"]
