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
from fastapi.responses import HTMLResponse

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

    # -- Root route -----------------------------------------------------------
    @app.get("/", response_class=HTMLResponse)
    async def root():
        return """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>DO IT - Autonomous AI Agent</title>
<style>
  *{margin:0;padding:0;box-sizing:border-box}
  body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:#0a0a0a;color:#e0e0e0;min-height:100vh;display:flex;flex-direction:column;align-items:center;justify-content:center;padding:2rem}
  .container{max-width:700px;width:100%;text-align:center}
  h1{font-size:2.8rem;font-weight:700;background:linear-gradient(135deg,#00d4ff,#7b2ff7);-webkit-background-clip:text;-webkit-text-fill-color:transparent;margin-bottom:.5rem}
  .tagline{color:#888;font-size:1.1rem;margin-bottom:2.5rem}
  .status{display:inline-flex;align-items:center;gap:.5rem;background:#1a1a2e;border:1px solid #333;border-radius:999px;padding:.4rem 1rem;font-size:.85rem;margin-bottom:2rem}
  .dot{width:8px;height:8px;border-radius:50%;background:#00ff88;animation:pulse 2s infinite}
  @keyframes pulse{0%,100%{opacity:1}50%{opacity:.4}}
  .cards{display:grid;grid-template-columns:1fr 1fr;gap:1rem;margin-bottom:2rem}
  .card{background:#111;border:1px solid #222;border-radius:12px;padding:1.5rem;text-decoration:none;color:#e0e0e0;transition:all .2s}
  .card:hover{border-color:#00d4ff;transform:translateY(-2px);box-shadow:0 4px 20px rgba(0,212,255,.1)}
  .card h3{font-size:1rem;margin-bottom:.4rem;color:#fff}
  .card p{font-size:.85rem;color:#888}
  .card .icon{font-size:1.8rem;margin-bottom:.8rem}
  .endpoints{background:#111;border:1px solid #222;border-radius:12px;padding:1.5rem;text-align:left}
  .endpoints h3{margin-bottom:1rem;color:#fff}
  .ep{display:flex;justify-content:space-between;align-items:center;padding:.5rem 0;border-bottom:1px solid #1a1a1a;font-size:.85rem}
  .ep:last-child{border-bottom:none}
  .ep code{color:#00d4ff;font-family:'Fira Code',monospace}
  .method{background:#1a1a2e;border-radius:4px;padding:.15rem .5rem;font-size:.75rem;font-weight:600;margin-right:.5rem}
  .method.get{color:#00ff88}
  .method.post{color:#f5a623}
  .footer{margin-top:2rem;color:#555;font-size:.8rem}
</style>
</head>
<body>
<div class="container">
  <h1>DO IT</h1>
  <p class="tagline">Autonomous AI Agent &mdash; Plan, Execute, Deliver</p>
  <div class="status"><div class="dot"></div> System Online</div>
  <div class="cards">
    <a href="/docs" class="card">
      <div class="icon">&#128214;</div>
      <h3>API Docs</h3>
      <p>Interactive Swagger UI</p>
    </a>
    <a href="/health" class="card">
      <div class="icon">&#128154;</div>
      <h3>Health Check</h3>
      <p>System status</p>
    </a>
  </div>
  <div class="endpoints">
    <h3>Endpoints</h3>
    <div class="ep"><span><span class="method post">POST</span> /api/session</span><span>Create a new session</span></div>
    <div class="ep"><span><span class="method post">POST</span> /api/session/{id}/message</span><span>Send a message</span></div>
    <div class="ep"><span><span class="method get">GET</span> /api/session/{id}</span><span>Get session state</span></div>
    <div class="ep"><span><span class="method get">GET</span> /api/tools</span><span>List available tools</span></div>
    <div class="ep"><span><span class="method get">GET</span> /api/health</span><span>API health</span></div>
  </div>
  <p class="footer">DO IT &copy; 2026 &mdash; Built with LangGraph + FastAPI</p>
</div>
</body>
</html>"""

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

    return app


# Module-level singleton for convenience imports (e.g. ``from src.api import app``).
app = create_app()
