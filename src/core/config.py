"""Application configuration loaded from environment variables and .env files."""

from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Central configuration for the Agentic AI framework.

    Values are loaded from environment variables or a ``.env`` file in the
    project root.  All paths are resolved to absolute :class:`Path` objects.
    """

    # ------------------------------------------------------------------
    # Project paths
    # ------------------------------------------------------------------
    PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent.parent
    DATA_DIR: Path = PROJECT_ROOT / "data"
    CHROMA_DB_PATH: Path = DATA_DIR / "chroma_db"
    SQLITE_PATH: Path = DATA_DIR / "sqlite.db"

    # ------------------------------------------------------------------
    # Model configuration
    # ------------------------------------------------------------------
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL_PRIMARY: str = "gpt-5.5"
    OPENAI_MODEL_MINI: str = "gpt-5.5-mini"
    LOCAL_MODEL: str = "qwen3"

    # ------------------------------------------------------------------
    # Application / server configuration
    # ------------------------------------------------------------------
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    DEBUG: bool = True
    MAX_PARALLEL_TASKS: int = 5
    MAX_REPLAN_ATTEMPTS: int = 3
    APPROVAL_TIMEOUT_SECONDS: int = 300

    model_config = {"env_file": ".env", "extra": "ignore"}

    def model_post_init(self, _context: object) -> None:
        """Ensure all data directories exist after settings are initialised."""
        self.DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.CHROMA_DB_PATH.mkdir(parents=True, exist_ok=True)
        self.SQLITE_PATH.parent.mkdir(parents=True, exist_ok=True)


settings = Settings()
