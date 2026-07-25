"""Structured logging configuration for the Agentic AI framework."""

import logging
import sys
from typing import Optional


def setup_logging(
    debug: bool = False,
    name: str = "agentic_ai",
    log_file: Optional[str] = None,
) -> logging.Logger:
    """Configure and return the application logger.

    Parameters
    ----------
    debug:
        If ``True`` the logger level is set to ``DEBUG``; otherwise ``INFO``.
    name:
        The logger name to retrieve/configure.  Defaults to ``"agentic_ai"``.
    log_file:
        Optional path to a file for persistent log storage.

    Returns
    -------
    logging.Logger
        The configured logger instance.
    """
    logger = logging.getLogger(name)
    level = logging.DEBUG if debug else logging.INFO
    logger.setLevel(level)

    # Avoid adding duplicate handlers on repeated calls.
    if logger.handlers:
        return logger

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(filename)s:%(lineno)d | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Optional file handler
    if log_file:
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger
