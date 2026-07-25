"""Miscellaneous helper utilities for the Agentic AI framework."""

import json
import re
import uuid
from typing import Any, Optional


def generate_id(prefix: str = "") -> str:
    """Generate a short unique identifier.

    Parameters
    ----------
    prefix:
        An optional string prepended to the random portion (e.g. ``"task"``
        yields ``"task_a1b2c3d4e5f6"``).

    Returns
    -------
    str
        A unique identifier string.
    """
    uid = uuid.uuid4().hex[:12]
    return f"{prefix}_{uid}" if prefix else uid


def truncate(text: str, max_length: int = 100) -> str:
    """Truncate *text* with an ellipsis if it exceeds *max_length*.

    Parameters
    ----------
    text:
        The string to truncate.
    max_length:
        Maximum number of characters before truncation.  Must be at least 4
        so there is room for the ``"..."`` suffix.

    Returns
    -------
    str
        The original string or a truncated version ending with ``"..."``.
    """
    if max_length < 4:
        max_length = 4
    if len(text) <= max_length:
        return text
    return text[: max_length - 3] + "..."


def safe_json_parse(text: str) -> Optional[dict[str, Any]]:
    """Try to parse JSON from LLM output, handling markdown code fences.

    The parser strips outer markdown fenced code blocks (`````json ... ``````)
    before attempting to decode the JSON.

    Parameters
    ----------
    text:
        Raw text that may contain JSON, possibly wrapped in markdown fences.

    Returns
    -------
    dict or None
        The parsed dictionary, or ``None`` if parsing fails.
    """
    cleaned = text.strip()

    # Remove markdown code fences
    if cleaned.startswith("```"):
        # Locate the first '{' or '[' after the fence
        start = cleaned.find("{")
        if start == -1:
            start = cleaned.find("[")
        if start >= 0:
            cleaned = cleaned[start:]
        # Strip trailing fence if present
        end = cleaned.rfind("```")
        if end >= 0:
            cleaned = cleaned[:end]

    cleaned = cleaned.strip()
    if not cleaned:
        return None

    try:
        return json.loads(cleaned)
    except (json.JSONDecodeError, ValueError):
        return None
