"""FastAPI application factory and global configuration.

Use :func:`create_app` to build a fully-configured FastAPI instance, or
import the module-level ``app`` singleton::

    from src.api import app
    # OR
    from src.api.server import app
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.utils.logger import setup_logging
from src.core.config import settings

logger = setup_logging()


# ===========================================================================
# Lifespan
# ===========================================================================


@asynccontextmanager
async def lifespan(app: FastAPI) -> None:
    """Application lifespan: initialise services on startup, clean up on shutdown.

    Startup
    -------
    * Configures structured logging.
    * Initializes the Tool Marketplace (registering built-in tools).
    * Sets up the Approval Gate.
    * Prepares the ChromaDB / memory store connection.

    Shutdown
    --------
    * Closes database connections.
    * Cancels any pending approval requests.
    * Cleans up background tasks.
    """
    # -- Startup -----------------------------------------------------------
    logger.info("Starting Agentic AI API server ...")

    # Initialize the tool registry (singleton) with built-in tools.
    from src.tools.registry import ToolRegistry
    from src.tools.flight_tool import FlightTool
    from src.tools.hotel_tool import HotelTool
    from src.tools.train_tool import TrainTool
    from src.tools.weather_tool import WeatherTool
    from src.tools.budget_tool import BudgetTool
    from src.tools.email_tool import EmailTool

    registry = ToolRegistry()
    for tool_cls in (FlightTool, HotelTool, TrainTool, WeatherTool, BudgetTool, EmailTool):
        try:
            registry.register(tool_cls())
            logger.debug("Registered tool: %s", tool_cls.__name__)
        except ValueError:
            # Tool already registered; skip.
            pass
        except Exception as exc:
            logger.warning("Failed to register tool %s: %s", tool_cls.__name__, exc)

    # Build the full LangGraph state machine with all dependencies.
    from src.engine.state_machine import AgenticStateMachine as LangGraphSM
    from src.engine.parallel_executor import ParallelExecutor
    from src.engine.dependency_graph import DependencyGraphBuilder
    from src.risk.risk_predictor import RiskPredictor

    learning_memory = None
    try:
        from src.memory.learning_memory import LearningMemory
        learning_memory = LearningMemory()
        logger.info("LearningMemory initialised")
    except Exception as exc:
        logger.warning("LearningMemory not available: %s", exc)

    risk_predictor = RiskPredictor(tool_registry=registry)

    lg_sm = LangGraphSM(
        tool_registry=registry,
        risk_predictor=risk_predictor,
        learning_memory=learning_memory,
        settings=settings,
    )

    # Store on app.state for access in routes.
    app.state.tool_registry = registry
    app.state.langraph_app = lg_sm.compile()
    app.state.learning_memory = learning_memory
    app.state.risk_predictor = risk_predictor
    app.state.approval_gate = None  # Lazy initialised in routes.

    logger.info("Agentic AI API server started.")

    yield

    # -- Shutdown -----------------------------------------------------------
    logger.info("Shutting down Agentic AI API server ...")

    # Cancel any pending approval requests for all sessions.
    if hasattr(app.state, "approval_gate") and app.state.approval_gate is not None:
        # Cancel per session — iterate over known sessions.
        from src.api.routes import sessions

        for session_id in sessions:
            try:
                cancelled = await app.state.approval_gate.cancel_pending_for_session(
                    session_id
                )
                if cancelled:
                    logger.info(
                        "Cancelled %d pending approvals for session %s",
                        cancelled,
                        session_id,
                    )
            except Exception as exc:
                logger.warning("Error cancelling approvals for %s: %s", session_id, exc)

    logger.info("Agentic AI API server shut down.")


# ===========================================================================
# App factory
# ===========================================================================


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.

    Returns
    -------
    FastAPI
        A fully-configured application instance ready to be served by
        an ASGI server (e.g. Uvicorn).
    """
    app = FastAPI(
        title="Agentic AI",
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # -- CORS -----------------------------------------------------------------
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
        allow_credentials=True,
    )

    # -- Register REST routes -------------------------------------------------
    from src.api.routes import router as rest_router

    app.include_router(rest_router, prefix="/api")

    # -- Register WebSocket routes --------------------------------------------
    from src.api.websocket_manager import ws_router

    app.include_router(ws_router)

    return app


# Module-level singleton for convenience imports (e.g. ``from src.api import app``).
app = create_app()
