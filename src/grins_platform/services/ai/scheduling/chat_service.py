"""
SchedulingChatService — role-aware AI chat for scheduling.

Routes Admin and Resource messages through different tool sets,
persists conversation history, and enforces guardrails.

Validates: Requirements 1.6, 1.7, 1.8, 1.9, 2.1-2.5,
           9.1-9.10, 14.1-14.10, 24.2, 24.3, 24.5, 32.3, 34.1
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import select, update

from grins_platform.log_config import LoggerMixin
from grins_platform.models.change_request import ChangeRequest
from grins_platform.models.scheduling_chat_session import SchedulingChatSession
from grins_platform.schemas.ai_scheduling import (
    ChatResponse,
    ScheduleChange,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

# ---------------------------------------------------------------------------
# Off-topic guard keywords — reject messages unrelated to scheduling
# ---------------------------------------------------------------------------
_SCHEDULING_KEYWORDS = {
    "schedule",
    "job",
    "staff",
    "resource",
    "route",
    "appointment",
    "customer",
    "capacity",
    "zone",
    "delay",
    "parts",
    "equipment",
    "checklist",
    "tomorrow",
    "today",
    "week",
    "assign",
    "move",
    "swap",
    "emergency",
    "forecast",
    "utilization",
    "batch",
    "revenue",
    "weather",
    "recurring",
    "nearby",
    "resequence",
    "assist",
    "upgrade",
    "quote",
    "access",
    "followup",
    "follow-up",
    "report",
    "log",
    "inventory",
    "truck",
    "backlog",
    "sla",
    "compliance",
    "overtime",
    "seasonal",
    "opening",
    "closing",
    "maintenance",
    "repair",
    "install",
    "diagnostic",
    "estimate",
    "invoice",
    "payment",
    "tech",
    "technician",
    "manager",
    "admin",
    "help",
    "what",
    "how",
    "when",
    "where",
    "who",
    "show",
    "list",
    "get",
    "find",
    "create",
    "add",
    "remove",
    "cancel",
    "update",
    "change",
    "check",
    "status",
    "info",
    "detail",
}

# Admin tool definitions for OpenAI function calling
_ADMIN_TOOLS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "generate_schedule",
            "description": "Build a weekly schedule using all 30 criteria",
            "parameters": {
                "type": "object",
                "properties": {
                    "date": {"type": "string", "description": "ISO date (YYYY-MM-DD)"},
                    "preferences": {
                        "type": "object",
                        "description": "Optional scheduling preferences",
                    },
                },
                "required": ["date"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "reshuffle_day",
            "description": "Redistribute jobs when resources are unavailable",
            "parameters": {
                "type": "object",
                "properties": {
                    "date": {"type": "string"},
                    "unavailable_resources": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "strategy": {"type": "string"},
                },
                "required": ["date"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "insert_emergency",
            "description": "Find best-fit resource for an emergency job",
            "parameters": {
                "type": "object",
                "properties": {
                    "address": {"type": "string"},
                    "skill": {"type": "string"},
                    "duration": {"type": "integer"},
                    "time_constraint": {"type": "string"},
                },
                "required": ["address"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "forecast_capacity",
            "description": "Forecast capacity for job type over weeks",
            "parameters": {
                "type": "object",
                "properties": {
                    "job_type": {"type": "string"},
                    "weeks": {"type": "integer"},
                    "zones": {"type": "array", "items": {"type": "string"}},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "move_job",
            "description": "Move a job to a different day/time",
            "parameters": {
                "type": "object",
                "properties": {
                    "job_id": {"type": "string"},
                    "target_day": {"type": "string"},
                    "target_time": {"type": "string"},
                    "same_tech": {"type": "boolean"},
                },
                "required": ["job_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "find_underutilized",
            "description": "Find underutilized resources for a week",
            "parameters": {
                "type": "object",
                "properties": {"week": {"type": "string"}},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "batch_schedule",
            "description": "Batch schedule jobs across multiple weeks",
            "parameters": {
                "type": "object",
                "properties": {
                    "job_type": {"type": "string"},
                    "customer_count": {"type": "integer"},
                    "weeks": {"type": "integer"},
                    "zone_priority": {"type": "array", "items": {"type": "string"}},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "rank_profitable_jobs",
            "description": "Rank jobs by revenue per resource-hour for open slots",
            "parameters": {
                "type": "object",
                "properties": {
                    "day": {"type": "string"},
                    "open_slots": {"type": "integer"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "weather_reschedule",
            "description": "Reschedule outdoor jobs on severe weather days",
            "parameters": {
                "type": "object",
                "properties": {"day": {"type": "string"}},
                "required": ["day"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_recurring_route",
            "description": "Create a recurring route for commercial accounts",
            "parameters": {
                "type": "object",
                "properties": {
                    "accounts": {"type": "array", "items": {"type": "string"}},
                    "cadence": {"type": "string"},
                    "preferences": {"type": "object"},
                },
                "required": ["accounts", "cadence"],
            },
        },
    },
]

# Resource tool definitions
_RESOURCE_TOOLS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "report_delay",
            "description": "Report a delay and recalculate ETAs",
            "parameters": {
                "type": "object",
                "properties": {
                    "resource_id": {"type": "string"},
                    "delay_minutes": {"type": "integer"},
                },
                "required": ["resource_id", "delay_minutes"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_prejob_info",
            "description": "Get pre-job checklist for a job",
            "parameters": {
                "type": "object",
                "properties": {
                    "resource_id": {"type": "string"},
                    "job_id": {"type": "string"},
                },
                "required": ["resource_id", "job_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "request_followup",
            "description": "Request a follow-up job from the field",
            "parameters": {
                "type": "object",
                "properties": {
                    "resource_id": {"type": "string"},
                    "job_id": {"type": "string"},
                    "field_notes": {"type": "string"},
                    "parts_needed": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["resource_id", "job_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "report_access_issue",
            "description": "Report an access issue at a job site",
            "parameters": {
                "type": "object",
                "properties": {
                    "resource_id": {"type": "string"},
                    "job_id": {"type": "string"},
                    "issue_type": {"type": "string"},
                },
                "required": ["resource_id", "job_id", "issue_type"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "find_nearby_work",
            "description": "Find nearby jobs matching skills and equipment",
            "parameters": {
                "type": "object",
                "properties": {
                    "resource_id": {"type": "string"},
                    "location": {"type": "string"},
                },
                "required": ["resource_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "request_resequence",
            "description": "Request route resequencing",
            "parameters": {
                "type": "object",
                "properties": {
                    "resource_id": {"type": "string"},
                    "reason": {"type": "string"},
                    "shop_stop": {"type": "boolean"},
                },
                "required": ["resource_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "request_assistance",
            "description": "Request crew assistance for a job",
            "parameters": {
                "type": "object",
                "properties": {
                    "resource_id": {"type": "string"},
                    "job_id": {"type": "string"},
                    "skill_needed": {"type": "string"},
                },
                "required": ["resource_id", "job_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "log_parts",
            "description": "Log parts used on a job",
            "parameters": {
                "type": "object",
                "properties": {
                    "resource_id": {"type": "string"},
                    "job_id": {"type": "string"},
                    "parts_list": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "quantity": {"type": "integer"},
                            },
                        },
                    },
                },
                "required": ["resource_id", "job_id", "parts_list"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_tomorrow_schedule",
            "description": "Get tomorrow's schedule for the resource",
            "parameters": {
                "type": "object",
                "properties": {"resource_id": {"type": "string"}},
                "required": ["resource_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "request_upgrade_quote",
            "description": "Request an upgrade quote for customer equipment",
            "parameters": {
                "type": "object",
                "properties": {
                    "resource_id": {"type": "string"},
                    "job_id": {"type": "string"},
                    "upgrade_type": {"type": "string"},
                },
                "required": ["resource_id", "job_id"],
            },
        },
    },
]

_ADMIN_SYSTEM_PROMPT = """You are an AI scheduling assistant for Grin's Irrigation.
You help admins build and optimize schedules using 30 decision criteria.
You have access to tools for schedule generation, emergency insertion, capacity
forecasting, and route optimization. Always ask clarifying questions before
executing major schedule changes. Focus only on scheduling topics."""

_RESOURCE_SYSTEM_PROMPT = """You are an AI field assistant for Grin's Irrigation.
You help technicians with their daily schedule, pre-job information, parts logging,
and field requests. You can report delays, find nearby work, and request assistance.
Focus only on scheduling and field operations topics."""


class SchedulingChatService(LoggerMixin):
    """Role-aware AI chat service for scheduling.

    Routes Admin messages through admin tool set and Resource messages
    through resource tool set. Persists conversation history to
    ``scheduling_chat_sessions`` table.

    Attributes:
        DOMAIN: Logging domain identifier.
    """

    DOMAIN = "scheduling"

    def __init__(self, session: AsyncSession) -> None:
        """Initialise the chat service.

        Args:
            session: Async SQLAlchemy session.
        """
        super().__init__()
        self._session = session
        api_key = os.getenv("OPENAI_API_KEY")
        self._client = None
        if api_key:
            try:
                from openai import (  # noqa: PLC0415
                    AsyncOpenAI,  # type: ignore[import-untyped]
                )

                self._client = AsyncOpenAI(api_key=api_key)
            except ImportError:
                self.logger.debug(
                    "scheduling.chatsvc.openai_not_installed",
                    message="openai package not installed; using fallback responses",
                )
        self._model = os.getenv("SCHEDULING_CHAT_MODEL", "gpt-4o-mini")

    async def chat(
        self,
        user_id: UUID,
        role: str,
        message: str,
        session_id: UUID | None = None,
    ) -> ChatResponse:
        """Process a scheduling chat message.

        Routes to admin or resource handler based on role. Persists
        conversation history and writes an audit log entry.

        Args:
            user_id: Staff member UUID.
            role: User role ('admin', 'manager', or 'technician').
            message: User's natural-language message.
            session_id: Existing session UUID for multi-turn conversations.

        Returns:
            ``ChatResponse`` with AI text, optional schedule changes,
            clarifying questions, or change-request ID.
        """
        self.log_started(
            "chat",
            user_id=str(user_id),
            role=role,
            message_length=len(message),
            session_id=str(session_id) if session_id else None,
        )

        try:
            # Guardrail: reject off-topic messages
            if not self._is_scheduling_related(message):
                self.logger.info(
                    "scheduling.chatsvc.off_topic_rejected",
                    user_id=str(user_id),
                    role=role,
                )
                return ChatResponse(
                    response=(
                        "I can only help with scheduling and field operations topics. "
                        "Please ask about jobs, routes, staff, capacity, or equipment."
                    ),
                )

            # Load or create session
            session_obj = await self._get_or_create_session(
                user_id,
                role,
                session_id,
            )

            # Route by role
            is_admin = role in ("admin", "manager")
            if is_admin:
                response = await self._handle_admin_message(
                    message,
                    session_obj,
                )
            else:
                response = await self._handle_resource_message(
                    message,
                    session_obj,
                    user_id,
                )

            # Multi-turn continuity: every post-session response carries the
            # session id back so clients can echo it on the next request.
            # criteria_used / schedule_summary stay None until a tool call
            # returns a real ScheduleSolution to summarize (deferred follow-up).
            response.session_id = session_obj.id

            # Persist updated history
            await self._append_message(
                session_obj,
                "user",
                message,
            )
            await self._append_message(
                session_obj,
                "assistant",
                response.response,
            )
            await self._session.commit()

            # Audit log
            self.logger.info(
                "scheduling.chatsvc.interaction_logged",
                user_id=str(user_id),
                role=role,
                session_id=str(session_obj.id),
                response_length=len(response.response),
                has_changes=bool(response.schedule_changes),
                has_questions=bool(response.clarifying_questions),
                has_change_request=bool(response.change_request_id),
            )

        except Exception as exc:
            self.log_failed("chat", error=exc, user_id=str(user_id))
            raise
        else:
            self.log_completed(
                "chat",
                user_id=str(user_id),
                role=role,
            )
            return response

    # ------------------------------------------------------------------
    # Role handlers
    # ------------------------------------------------------------------

    async def _handle_admin_message(
        self,
        message: str,
        session_obj: SchedulingChatSession,
    ) -> ChatResponse:
        """Handle an admin/manager scheduling message."""
        if not self._client:
            return self._fallback_admin_response(message)

        messages = self._build_messages(
            _ADMIN_SYSTEM_PROMPT,
            session_obj.messages,
            message,
        )

        try:
            completion = await self._client.chat.completions.create(  # type: ignore[call-overload]
                model=self._model,
                messages=messages,  # type: ignore[arg-type]
                tools=_ADMIN_TOOLS,  # type: ignore[arg-type]
                tool_choice="auto",
                max_tokens=800,
                temperature=0.3,
            )
        except Exception as exc:
            self.log_failed("_handle_admin_message", error=exc)
            return self._fallback_admin_response(message)

        choice = completion.choices[0]
        text = choice.message.content or ""
        schedule_changes: list[ScheduleChange] | None = None
        clarifying_questions: list[str] | None = None

        # Parse tool calls into schedule changes
        if choice.message.tool_calls:
            schedule_changes = []
            for tc in choice.message.tool_calls:
                try:
                    args = json.loads(tc.function.arguments)  # type: ignore[union-attr]
                except (json.JSONDecodeError, AttributeError):
                    args = {}
                schedule_changes.append(
                    ScheduleChange(
                        change_type=tc.function.name,  # type: ignore[union-attr]
                        explanation=f"Executing {tc.function.name} with {args}",  # type: ignore[union-attr]
                    )
                )

        # Detect clarifying questions (lines ending with "?")
        if text:
            questions = [
                line.strip() for line in text.splitlines() if line.strip().endswith("?")
            ]
            if questions:
                clarifying_questions = questions

        return ChatResponse(
            response=text or "I'll process that scheduling request.",
            schedule_changes=schedule_changes or None,
            clarifying_questions=clarifying_questions,
        )

    async def _handle_resource_message(
        self,
        message: str,
        session_obj: SchedulingChatSession,
        user_id: UUID,
    ) -> ChatResponse:
        """Handle a resource/technician field message."""
        if not self._client:
            return self._fallback_resource_response(message)

        messages = self._build_messages(
            _RESOURCE_SYSTEM_PROMPT,
            session_obj.messages,
            message,
        )

        try:
            completion = await self._client.chat.completions.create(  # type: ignore[call-overload]
                model=self._model,
                messages=messages,  # type: ignore[arg-type]
                tools=_RESOURCE_TOOLS,  # type: ignore[arg-type]
                tool_choice="auto",
                max_tokens=600,
                temperature=0.3,
            )
        except Exception as exc:
            self.log_failed("_handle_resource_message", error=exc)
            return self._fallback_resource_response(message)

        choice = completion.choices[0]
        text = choice.message.content or ""
        change_request_id: UUID | None = None

        # Tool calls that require admin approval become ChangeRequests
        _escalation_tools = {
            "request_followup",
            "report_access_issue",
            "request_resequence",
            "request_assistance",
            "request_upgrade_quote",
        }

        if choice.message.tool_calls:
            for tc in choice.message.tool_calls:
                if tc.function.name in _escalation_tools:  # type: ignore[union-attr]
                    try:
                        args = json.loads(tc.function.arguments)  # type: ignore[union-attr]
                    except (json.JSONDecodeError, AttributeError):
                        args = {}
                    change_request_id = await self._create_change_request(
                        user_id,
                        tc.function.name,  # type: ignore[union-attr]
                        args,
                    )
                    break  # one change request per message

        return ChatResponse(
            response=text or "I'll handle that for you.",
            change_request_id=change_request_id,
        )

    # ------------------------------------------------------------------
    # Session management
    # ------------------------------------------------------------------

    async def _get_or_create_session(
        self,
        user_id: UUID,
        role: str,
        session_id: UUID | None,
    ) -> SchedulingChatSession:
        """Load an existing session or create a new one."""
        if session_id is not None:
            stmt = select(SchedulingChatSession).where(
                SchedulingChatSession.id == session_id,
                SchedulingChatSession.user_id == user_id,
                SchedulingChatSession.is_active.is_(True),
            )
            result = await self._session.execute(stmt)
            existing = result.scalar_one_or_none()
            if existing is not None:
                return existing  # type: ignore[return-value, no-any-return]

        # Create new session
        new_session = SchedulingChatSession(
            user_id=user_id,
            user_role=role,
            messages=[],
            context={},
            is_active=True,
        )
        self._session.add(new_session)
        await self._session.flush()
        return new_session

    async def _append_message(
        self,
        session_obj: SchedulingChatSession,
        role: str,
        content: str,
    ) -> None:
        """Append a message to the session history."""
        messages = list(session_obj.messages or [])
        messages.append(
            {
                "role": role,
                "content": content,
                "timestamp": datetime.now(tz=timezone.utc).isoformat(),
            }
        )
        await self._session.execute(
            update(SchedulingChatSession)
            .where(SchedulingChatSession.id == session_obj.id)
            .values(messages=messages)
        )
        session_obj.messages = messages

    # ------------------------------------------------------------------
    # Change request creation
    # ------------------------------------------------------------------

    async def _create_change_request(
        self,
        resource_id: UUID,
        request_type: str,
        details: dict[str, Any],
    ) -> UUID | None:
        """Persist a ChangeRequest and return its ID."""
        try:
            cr = ChangeRequest(
                resource_id=resource_id,
                request_type=request_type,
                details=details,
                recommended_action=f"Review {request_type} request from resource",
                status="pending",
            )
            self._session.add(cr)
            await self._session.flush()
        except Exception as exc:
            self.log_failed("_create_change_request", error=exc)
            return None
        else:
            return cr.id  # type: ignore[return-value, no-any-return]

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _is_scheduling_related(message: str) -> bool:
        """Return True if the message is related to scheduling topics."""
        lower = message.lower()
        return any(kw in lower for kw in _SCHEDULING_KEYWORDS)

    @staticmethod
    def _build_messages(
        system_prompt: str,
        history: list[dict[str, Any]],
        new_message: str,
    ) -> list[dict[str, str]]:
        """Build the OpenAI messages list from history + new message."""
        msgs: list[dict[str, str]] = [{"role": "system", "content": system_prompt}]
        # Include last 10 turns to stay within context limits
        for entry in history[-20:]:
            role = entry.get("role", "user")
            content = entry.get("content", "")
            if role in ("user", "assistant") and content:
                msgs.append({"role": role, "content": content})
        msgs.append({"role": "user", "content": new_message})
        return msgs

    @staticmethod
    def _fallback_admin_response(_message: str) -> ChatResponse:
        """Fallback when OpenAI is unavailable (admin)."""
        return ChatResponse(
            response=(
                "I can help you with scheduling. "
                "Available commands: generate schedule, insert emergency job, "
                "forecast capacity, move job, find underutilized resources, "
                "batch schedule, rank profitable jobs, weather reschedule, "
                "create recurring route. "
                "Please describe what you need."
            ),
            clarifying_questions=[
                "Which date or week are you scheduling for?",
                "Are there any specific constraints I should know about?",
            ],
        )

    @staticmethod
    def _fallback_resource_response(_message: str) -> ChatResponse:
        """Fallback when OpenAI is unavailable (resource)."""
        return ChatResponse(
            response=(
                "I can help you with: running late reports, pre-job info, "
                "follow-up requests, access issues, nearby work, route resequencing, "
                "crew assistance, parts logging, tomorrow's schedule, and upgrade "
                "quotes. What do you need?"
            ),
        )
