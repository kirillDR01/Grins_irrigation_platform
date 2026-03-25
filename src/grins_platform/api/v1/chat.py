"""Public AI chatbot API endpoint.

Provides a public (no auth) endpoint for the AI chatbot widget.

Validates: CRM Gap Closure Req 43.1, 43.4
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: TC002

from grins_platform.api.v1.dependencies import get_db_session
from grins_platform.log_config import LoggerMixin
from grins_platform.services.chat_service import ChatService

router = APIRouter()


class _ChatEndpoints(LoggerMixin):
    """Chat API endpoint handlers with logging."""

    DOMAIN = "api"


_endpoints = _ChatEndpoints()


class ChatRequest(BaseModel):
    """Public chat request."""

    message: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="User message",
    )
    session_id: str | None = Field(
        default=None,
        max_length=100,
        description="Chat session ID for context continuity",
    )


class ChatResponseSchema(BaseModel):
    """Public chat response."""

    reply: str = Field(..., description="AI response")
    session_id: str = Field(..., description="Session ID for follow-up")
    escalated: bool = Field(
        default=False,
        description="Whether the conversation was escalated",
    )


@router.post(
    "/public",
    response_model=ChatResponseSchema,
    summary="Public AI chatbot",
    description="Public endpoint for AI chatbot interactions. No auth required.",
)
async def public_chat(
    data: ChatRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ChatResponseSchema:
    """Handle a public AI chatbot message.

    This endpoint is PUBLIC — no authentication required.

    Validates: CRM Gap Closure Req 43.1, 43.4
    """
    _endpoints.log_started("public_chat", session_id=data.session_id)
    try:
        service = ChatService()
        chat_session_id = data.session_id or str(uuid.uuid4())
        result = await service.handle_public_message(
            db=session,
            session_id=chat_session_id,
            message=data.message,
        )
        _endpoints.log_completed(
            "public_chat",
            session_id=result.session_id,
            escalated=result.escalated,
        )
        return ChatResponseSchema(
            reply=result.reply,
            session_id=result.session_id,
            escalated=result.escalated,
        )
    except Exception as e:
        _endpoints.log_failed("public_chat", error=e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Chat service unavailable",
        ) from e
