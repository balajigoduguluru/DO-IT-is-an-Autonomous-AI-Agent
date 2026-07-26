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
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles

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

    # Compile the LangGraph state machine (may fail if langgraph not installed)
    langraph_app = None
    try:
        langraph_app = lg_sm.compile()
        logger.info("LangGraph state machine compiled successfully")
    except ImportError as exc:
        logger.warning("LangGraph not available, state machine disabled: %s", exc)
    except Exception as exc:
        logger.error("Failed to compile LangGraph state machine: %s", exc)

    # Store on app.state for access in routes.
    app.state.tool_registry = registry
    app.state.langraph_app = langraph_app
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

    # -- Health check (no dependencies) -------------------------------------
    @app.get("/health")
    async def health_check():
        return {
            "status": "ok",
            "langgraph_available": app.state.langraph_app is not None,
            "learning_memory_available": app.state.learning_memory is not None,
        }

    # -- Register WebSocket routes --------------------------------------------
    from src.api.websocket_manager import ws_router

    app.include_router(ws_router)

    # -- Serve React frontend ------------------------------------------------
    import os
    static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "static")
    static_dir = os.path.normpath(static_dir)

    if os.path.isdir(static_dir):
        app.mount("/assets", StaticFiles(directory=os.path.join(static_dir, "assets")), name="static-assets")

        @app.get("/{full_path:path}", response_class=HTMLResponse)
        async def serve_spa(full_path: str):
            file_path = os.path.join(static_dir, full_path)
            if os.path.isfile(file_path):
                return FileResponse(file_path)
            index_path = os.path.join(static_dir, "index.html")
            if os.path.isfile(index_path):
                return FileResponse(index_path)
            return HTMLResponse("<h1>Frontend not built. Run: cd frontend && npm run build</h1>", status_code=404)
    else:
        @app.get("/", response_class=HTMLResponse)
        async def root():
            return HTMLResponse("<h1>DO IT - Autonomous AI Agent</h1><p>Frontend not built. Run: cd frontend && npm run build</p>")

    return app


# Module-level singleton for convenience imports (e.g. ``from src.api import app``).
app = create_app()
