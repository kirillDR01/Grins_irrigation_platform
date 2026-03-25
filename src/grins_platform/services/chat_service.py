"""ChatService for public AI chatbot.

Handles public chat messages using GPT-4o-mini with Grins Irrigation context.
Maintains session state in Redis with 30min TTL.
Detects human escalation keywords and creates Communication + Lead records.

Validates: CRM Gap Closure Req 43.1, 43.2, 43.3, 43.5
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import TYPE_CHECKING
from uuid import UUID

from grins_platform.log_config import LoggerMixin

if TYPE_CHECKING:
    from redis.asyncio import Redis
    from sqlalchemy.ext.asyncio import AsyncSession


# Escalation keywords that trigger human handoff
ESCALATION_KEYWORDS: list[str] = [
    "speak to human",
    "speak to a human",
    "talk to a human",
    "talk to a person",
    "real person",
    "real human",
    "manager",
    "supervisor",
    "representative",
    "speak to someone",
    "talk to someone",
    "human please",
    "agent please",
    "live agent",
    "live person",
    "customer service",
    "help me please",
    "i need help",
    "not helpful",
    "stop bot",
]

# Redis key prefix and TTL
CHAT_SESSION_PREFIX = "chat:session:"
CHAT_SESSION_TTL_SECONDS = 1800  # 30 minutes

# Grins Irrigation system context for GPT
GRINS_SYSTEM_CONTEXT = (
    "You are a helpful assistant for Grins Irrigation, a professional "
    "irrigation and sprinkler system company. You help customers with "
    "questions about irrigation services, scheduling, pricing inquiries, "
    "and general information. Be friendly, professional, and concise. "
    "If the customer needs specific pricing or wants to schedule service, "
    "encourage them to submit a request through the website or call the office. "
    "If the customer asks to speak with a human, acknowledge their request "
    "and let them know someone will follow up shortly."
)


@dataclass
class ChatResponse:
    """Response from the chat service."""

    message: str
    session_id: str
    escalated: bool = False
    lead_id: UUID | None = None
    collected_info: dict[str, str] = field(default_factory=dict)


class ChatService(LoggerMixin):
    """Service for public AI chatbot interactions.

    Uses GPT-4o-mini with Grins Irrigation context.
    Session state stored in Redis with 30min TTL.
    Detects escalation keywords and creates Communication + Lead.

    Validates: CRM Gap Closure Req 43.1, 43.2, 43.3, 43.5
    """

    DOMAIN = "chat"

    def __init__(
        self,
        redis_client: Redis | None = None,
        openai_api_key: str | None = None,
    ) -> None:
        """Initialize ChatService.

        Args:
            redis_client: Redis client for session storage.
            openai_api_key: OpenAI API key for GPT-4o-mini.
        """
        super().__init__()
        self.redis = redis_client
        self.openai_api_key = openai_api_key

    def _detect_escalation(self, message: str) -> bool:
        """Check if the message contains escalation keywords.

        Args:
            message: User message text.

        Returns:
            True if escalation detected.
        """
        message_lower = message.lower().strip()
        return any(keyword in message_lower for keyword in ESCALATION_KEYWORDS)

    async def _get_session_history(
        self,
        session_id: str,
    ) -> list[dict[str, str]]:
        """Retrieve chat session history from Redis.

        Args:
            session_id: Chat session identifier.

        Returns:
            List of message dicts with role and content.
        """
        if self.redis is None:
            return []

        key = f"{CHAT_SESSION_PREFIX}{session_id}"
        raw = await self.redis.get(key)
        if raw is None:
            return []

        try:
            history: list[dict[str, str]] = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return []
        else:
            return history

    async def _save_session_history(
        self,
        session_id: str,
        history: list[dict[str, str]],
    ) -> None:
        """Save chat session history to Redis with TTL.

        Args:
            session_id: Chat session identifier.
            history: List of message dicts.
        """
        if self.redis is None:
            return

        key = f"{CHAT_SESSION_PREFIX}{session_id}"
        await self.redis.set(
            key,
            json.dumps(history),
            ex=CHAT_SESSION_TTL_SECONDS,
        )

    async def _call_openai(
        self,
        messages: list[dict[str, str]],
    ) -> str:
        """Call OpenAI GPT-4o-mini API.

        Args:
            messages: List of message dicts for the API.

        Returns:
            Assistant response text.
        """
        if self.openai_api_key is None:
            return (
                "I'm sorry, the chat service is temporarily unavailable. "
                "Please call our office or submit a request on our website."
            )

        try:
            import openai  # noqa: PLC0415

            client = openai.AsyncOpenAI(api_key=self.openai_api_key)
            response = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,  # type: ignore[arg-type]
                max_tokens=500,
                temperature=0.7,
            )
            content = response.choices[0].message.content
        except Exception as exc:
            self.log_failed("call_openai", error=exc)
            return (
                "I'm sorry, I'm having trouble right now. "
                "Please try again or call our office for assistance."
            )
        else:
            return content or "I'm sorry, I couldn't generate a response."

    async def _handle_escalation(
        self,
        db: AsyncSession,
        session_id: str,
        message: str,
        collected_info: dict[str, str],
    ) -> ChatResponse:
        """Handle escalation by creating Communication + Lead records.

        Args:
            db: Database session.
            session_id: Chat session identifier.
            message: The escalation message.
            collected_info: Name/phone collected during chat.

        Returns:
            ChatResponse with escalation flag set.
        """
        from grins_platform.models.communication import (  # noqa: PLC0415
            Communication,
        )

        self.log_started(
            "handle_escalation",
            session_id=session_id,
        )

        lead_id: UUID | None = None
        name = collected_info.get("name", "Chat Visitor")
        phone = collected_info.get("phone", "")

        # Create Communication record if we have enough info
        if phone:
            try:
                comm = Communication(
                    customer_id=None,  # type: ignore[arg-type]
                    channel="CHAT",
                    direction="INBOUND",
                    content=f"Chat escalation request: {message}",
                    addressed=False,
                )
                db.add(comm)
                await db.flush()

                self.logger.info(
                    "chat.escalation.communication_created",
                    communication_id=str(comm.id),
                    session_id=session_id,
                )
            except Exception as exc:
                self.log_failed(
                    "create_communication",
                    error=exc,
                    session_id=session_id,
                )

        # Create Lead record
        if name and phone:
            try:
                from grins_platform.models.lead import Lead  # noqa: PLC0415

                lead = Lead(
                    name=name,
                    phone=phone,
                    situation="exploring",
                    lead_source="chat",
                    source_detail=f"Chat escalation (session: {session_id})",
                    action_tags=["NEEDS_CONTACT"],
                    status="new",
                )
                db.add(lead)
                await db.flush()
                lead_id = lead.id

                self.logger.info(
                    "chat.escalation.lead_created",
                    lead_id=str(lead_id),
                    session_id=session_id,
                )
            except Exception as exc:
                self.log_failed(
                    "create_lead",
                    error=exc,
                    session_id=session_id,
                )

        self.log_completed(
            "handle_escalation",
            session_id=session_id,
            lead_id=str(lead_id) if lead_id else None,
        )

        return ChatResponse(
            message=(
                "I understand you'd like to speak with someone from our team. "
                "A representative will follow up with you shortly. "
                "Thank you for your patience!"
            ),
            session_id=session_id,
            escalated=True,
            lead_id=lead_id,
            collected_info=collected_info,
        )

    def _extract_info_from_history(
        self,
        history: list[dict[str, str]],
    ) -> dict[str, str]:
        """Extract name and phone from chat history.

        Simple heuristic: look for messages that contain phone-like
        patterns or name introductions.

        Args:
            history: Chat message history.

        Returns:
            Dict with extracted name and phone if found.
        """
        import re  # noqa: PLC0415

        info: dict[str, str] = {}
        phone_pattern = re.compile(r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b")

        for msg in history:
            if msg.get("role") != "user":
                continue
            content = msg.get("content", "")

            # Extract phone
            if "phone" not in info:
                phone_match = phone_pattern.search(content)
                if phone_match:
                    digits = re.sub(r"[^0-9]", "", phone_match.group())
                    info["phone"] = digits

            # Extract name from common patterns
            if "name" not in info:
                name_re = (
                    r"(?:my name is|i'm|i am|this is)"
                    r"\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)"
                )
                name_patterns = [name_re]
                for pattern in name_patterns:
                    match = re.search(pattern, content, re.IGNORECASE)
                    if match:
                        info["name"] = match.group(1).strip()
                        break

        return info

    async def handle_public_message(
        self,
        db: AsyncSession,
        session_id: str,
        message: str,
    ) -> ChatResponse:
        """Handle a public chat message.

        Sends message to GPT-4o-mini with Grins context.
        Maintains session in Redis (30min TTL).
        Detects escalation keywords → creates Communication + Lead.

        Args:
            db: Database session.
            session_id: Chat session identifier.
            message: User message text.

        Returns:
            ChatResponse with assistant reply or escalation info.

        Validates: Req 43.1, 43.2, 43.3, 43.5
        """
        self.log_started(
            "handle_public_message",
            session_id=session_id,
        )

        # Load session history
        history = await self._get_session_history(session_id)

        # Add user message to history
        history.append({"role": "user", "content": message})

        # Check for escalation
        if self._detect_escalation(message):
            collected_info = self._extract_info_from_history(history)
            response = await self._handle_escalation(
                db,
                session_id,
                message,
                collected_info,
            )
            # Save history with escalation
            history.append({"role": "assistant", "content": response.message})
            await self._save_session_history(session_id, history)
            return response

        # Build messages for OpenAI
        api_messages: list[dict[str, str]] = [
            {"role": "system", "content": GRINS_SYSTEM_CONTEXT},
            *history,
        ]

        # Call OpenAI
        assistant_reply = await self._call_openai(api_messages)

        # Save updated history
        history.append({"role": "assistant", "content": assistant_reply})
        await self._save_session_history(session_id, history)

        self.log_completed(
            "handle_public_message",
            session_id=session_id,
        )

        return ChatResponse(
            message=assistant_reply,
            session_id=session_id,
        )
