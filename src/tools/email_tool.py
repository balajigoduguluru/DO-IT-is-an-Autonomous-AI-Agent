"""Email summary tool."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from src.core.constants import ToolCategory
from src.core.models import ToolRegistration
from src.tools.base_tool import BaseTool


class EmailTool(BaseTool):
    """Send email summaries.

    Simulates an SMTP-based email sending service.  In production this
    would connect to an actual SMTP server or transactional email API.
    """

    def get_registration(self) -> ToolRegistration:
        return ToolRegistration(
            name="email_sender",
            description="Send an email summary to a recipient.",
            category=ToolCategory.EMAIL,
            provider="SMTP",
            input_schema={
                "type": "object",
                "properties": {
                    "to": {"type": "string", "description": "Recipient email address"},
                    "subject": {"type": "string", "description": "Email subject line"},
                    "body": {"type": "string", "description": "Email body content"},
                },
                "required": ["to", "subject", "body"],
            },
        )

    async def execute(self, **kwargs: Any) -> dict[str, Any]:
        to = str(kwargs.get("to", "")).strip()
        subject = str(kwargs.get("subject", "")).strip()
        body = str(kwargs.get("body", "")).strip()

        if not to:
            raise ValueError("recipient email (to) is required")
        if not subject:
            raise ValueError("subject is required")
        if not body:
            raise ValueError("body is required")

        # Basic email validation
        if "@" not in to or "." not in to.split("@")[-1]:
            raise ValueError(f"Invalid email address: {to!r}")

        # Validate body length — reject unreasonably long payloads
        if len(body) > 100_000:
            raise ValueError(
                f"Email body too large ({len(body)} chars). "
                f"Maximum allowed is 100,000 characters."
            )

        now = datetime.now(timezone.utc)
        message_id = f"<{uuid.uuid4().hex}@agentic-ai.internal>"

        # Simulate SMTP send latency
        import asyncio

        await asyncio.sleep(0.1)

        return {
            "sent": True,
            "message_id": message_id,
            "timestamp": now.isoformat(),
            "to": to,
            "subject": subject,
            "body_preview": body[:100] + "..." if len(body) > 100 else body,
            "characters": len(body),
        }
