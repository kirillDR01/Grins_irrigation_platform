"""
SchedulingChatService — role-aware AI chat for scheduling.

Routes messages to admin or resource tool sets via OpenAI function
calling. Persists conversation history, enforces guardrails, and
logs all interactions with audit trail.

Validates: Requirements 1.6, 1.7, 1.8, 1.9, 2.1, 2.2, 2.3, 2.4,
2.5, 9.1-9.10, 14.1-14.10, 24.2, 24.3, 24.5, 32.3, 34.1
"""

from __future__ import annotations

import json
import os
import time
from typing import TYPE_CHECKING, Any
from uuid import UUID

from openai import AsyncOpenAI
from sqlalchemy import select

from grins_platform.log_config import LoggerMixin
from grins_platform.models.scheduling_chat_session import SchedulingChatSession
from grins_platform.schemas.ai_scheduling import ChatResponse, ScheduleChange
from grins_platform.services.ai.scheduling.admin_tools import (
    AdminSchedulingTools,
    get_tool_definitions as get_admin_tool_definitions,
)
from grins_platform.services.ai.scheduling.resource_tools import (
    ResourceSchedulingTools,
    get_tool_definitions as get_resource_tool_definitions,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


# ---------------------------------------------------------------------------
# System prompts
# ---------------------------------------------------------------------------

ADMIN_SYSTEM_PROMPT = """\
You are the AI Scheduling Co-Pilot for Grin's Irrigation Platform.
You help User Admins (dispatchers, office managers, owners) build,
modify, and optimize field service schedules.

Your capabilities:
- Build weekly schedules optimized across 30 decision criteria
- Reshuffle days when resources call out
- Insert emergency jobs into the best slot
- Forecast capacity for upcoming weeks
- Move jobs between days/times/technicians
- Find underutilized resources and suggest fills
- Batch-schedule seasonal campaigns
- Rank jobs by profitability for open slots
- Reschedule weather-affected outdoor jobs
- Create recurring route templates

IMPORTANT RULES:
1. Before executing any scheduling command, ask ONE clarifying question
   to confirm the user's intent and gather missing details.
2. Only discuss scheduling, staffing, and route optimization topics.
   Politely redirect off-topic questions back to scheduling.
3. Never include raw customer phone numbers, emails, or full street
   addresses in your responses. Use customer names or IDs only.
4. When you call a tool, explain what criteria you used and why.
5. Present results clearly with key metrics highlighted.
"""

RESOURCE_SYSTEM_PROMPT = """\
You are the AI Field Assistant for Grin's Irrigation Platform.
You help field technicians manage their daily schedule, report
issues, and request changes.

Your capabilities:
- Report delays and see updated ETAs
- Get pre-job information (equipment, gate codes, instructions)
- Request follow-up jobs
- Report access issues at job sites
- Find nearby available work
- Request route resequencing
- Request crew assistance
- Log parts used on jobs
- View tomorrow's schedule
- Request upgrade quotes for customers

IMPORTANT RULES:
1. Be concise and action-oriented — technicians are in the field.
2. For requests that need admin approval (follow-ups, resequencing,
   crew assist, upgrade quotes), create a change request and let
   the technician know it's pending approval.
3. For autonomous actions (delay reporting, pre-job info, parts
   logging, schedule viewing), handle directly.
4. Only discuss scheduling and field operations topics.
5. Never include raw customer phone numbers or emails.
"""

# Off-topic keywords that should trigger a redirect
_OFF_TOPIC_PATTERNS = [
    "politics",
    "religion",
    "sports score",
    "stock market",
    "weather forecast for vacation",
    "recipe",
    "joke",
    "personal advice",
    "dating",
]


class SchedulingChatService(LoggerMixin):
    """Role-aware chat service for AI scheduling.

    Routes messages based on user role (admin vs resource) to
    different system prompts and tool sets. Uses OpenAI function
    calling to invoke scheduling tools. Persists conversation
    history to the scheduling_chat_sessions table.

    Attributes:
        DOMAIN: Logging domain for structured log events.
    """

    DOMAIN = "scheduling"

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the scheduling chat service.

        Args:
            session: Async database session.
        """
        super().__init__()
        self._session = session
        self._admin_tools = AdminSchedulingTools(session)
        self._resource_tools = ResourceSchedulingTools(session)

        # Initialize OpenAI client
        api_key = os.getenv("OPENAI_API_KEY")
        self._client: AsyncOpenAI | None = (
            AsyncOpenAI(api_key=api_key) if api_key else None
        )
        self._model = os.getenv("SCHEDULING_AI_MODEL", "gpt-4o-mini")

    async def chat(
        self,
        user_id: UUID,
        role: str,
        message: str,
        session_id: UUID | None = None,
    ) -> ChatResponse:
        """Process a scheduling chat message with role-based routing.

        Args:
            user_id: UUID of the user sending the message.
            role: User role — "admin" or "resource".
            message: The user's natural language message.
            session_id: Optional existing session ID for
                multi-turn conversations.

        Returns:
            ChatResponse with response text and optional
            schedule_changes, clarifying_questions, or
            change_request_id.
        """
        start_time = time.monotonic()
        self.log_started(
            "chat",
            user_id=str(user_id),
            role=role,
            message_length=len(message),
            session_id=str(session_id) if session_id else None,
        )

        try:
            # Load or create chat session
            session_record = await self._load_or_create_session(
                user_id,
                role,
                session_id,
            )

            # Enforce guardrails — reject off-topic
            if self._is_off_topic(message):
                response = ChatResponse(
                    response=(
                        "I'm focused on scheduling and field operations. "
                        "How can I help with your schedule today?"
                    ),
                )
                await self._persist_turn(
                    session_record,
                    message,
                    response.response,
                )
                elapsed = time.monotonic() - start_time
                self.log_completed(
                    "chat",
                    user_id=str(user_id),
                    role=role,
                    intent="off_topic",
                    response_time_ms=round(elapsed * 1000),
                )
                return response

            # Append user message to history
            history = list(session_record.messages or [])
            history.append({"role": "user", "content": message})

            # Route based on role
            if role == "admin":
                response = await self._handle_admin_message(
                    message,
                    history,
                    session_record,
                )
            else:
                response = await self._handle_resource_message(
                    message,
                    history,
                    session_record,
                )

            # Persist conversation turn
            await self._persist_turn(
                session_record,
                message,
                response.response,
            )

            elapsed = time.monotonic() - start_time
            self.log_completed(
                "chat",
                user_id=str(user_id),
                role=role,
                intent="scheduling",
                response_time_ms=round(elapsed * 1000),
                has_changes=bool(response.schedule_changes),
                has_questions=bool(response.clarifying_questions),
                has_change_request=bool(response.change_request_id),
            )

        except Exception as e:
            elapsed = time.monotonic() - start_time
            self.log_failed(
                "chat",
                error=e,
                user_id=str(user_id),
                role=role,
                response_time_ms=round(elapsed * 1000),
            )
            return ChatResponse(
                response=(
                    "I encountered an issue processing your request. "
                    "Please try again or rephrase your question."
                ),
            )
        else:
            return response

    async def _handle_admin_message(
        self,
        _message: str,
        history: list[dict[str, Any]],
        _session: SchedulingChatSession,
    ) -> ChatResponse:
        """Handle a message from a User Admin via OpenAI function calling.

        Uses admin tool definitions so the LLM can invoke scheduling
        tools like generate_schedule, reshuffle_day, etc.

        Args:
            message: The user's message.
            history: Conversation history.
            session: The chat session record.

        Returns:
            ChatResponse with results.
        """
        self.log_started("_handle_admin_message")

        tools = get_admin_tool_definitions()
        system_prompt = ADMIN_SYSTEM_PROMPT

        return await self._call_openai_with_tools(
            system_prompt,
            history,
            tools,
            self._admin_tools,
        )

    async def _handle_resource_message(
        self,
        _message: str,
        history: list[dict[str, Any]],
        _session: SchedulingChatSession,
    ) -> ChatResponse:
        """Handle a message from a Resource via OpenAI function calling.

        Uses resource tool definitions so the LLM can invoke tools
        like report_delay, get_prejob_info, etc.

        Args:
            message: The user's message.
            history: Conversation history.
            session: The chat session record.

        Returns:
            ChatResponse with results.
        """
        self.log_started("_handle_resource_message")

        tools = get_resource_tool_definitions()
        system_prompt = RESOURCE_SYSTEM_PROMPT

        return await self._call_openai_with_tools(
            system_prompt,
            history,
            tools,
            self._resource_tools,
        )

    async def _call_openai_with_tools(
        self,
        system_prompt: str,
        history: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        tool_handler: AdminSchedulingTools | ResourceSchedulingTools,
    ) -> ChatResponse:
        """Send conversation to OpenAI with function calling tools.

        If OpenAI returns a tool call, dispatches to the appropriate
        handler and sends the result back for a final response.

        Args:
            system_prompt: Role-specific system prompt.
            history: Conversation history messages.
            tools: OpenAI tool definitions.
            tool_handler: Admin or resource tools instance.

        Returns:
            ChatResponse with the AI's response.
        """
        if not self._client:
            return self._fallback_response(history)

        messages: list[dict[str, Any]] = [
            {"role": "system", "content": system_prompt},
            *history,
        ]

        try:
            response = await self._client.chat.completions.create(  # type: ignore[call-overload]
                model=self._model,
                messages=messages,  # type: ignore[arg-type]
                tools=tools,  # type: ignore[arg-type]
                tool_choice="auto",
                max_tokens=1000,
                temperature=0.7,
            )

            choice = response.choices[0]
            assistant_message = choice.message

            # If the model wants to call a tool
            if assistant_message.tool_calls:
                tool_call = assistant_message.tool_calls[0]
                function_name = tool_call.function.name
                function_args = tool_call.function.arguments

                self.log_started(
                    "tool_dispatch",
                    function_name=function_name,
                )

                # Execute the tool
                tool_result = await tool_handler.dispatch_tool_call(
                    function_name,
                    function_args,
                )

                self.log_completed(
                    "tool_dispatch",
                    function_name=function_name,
                    status=tool_result.get("status"),
                )

                # Send tool result back to OpenAI for final response
                messages.append(assistant_message.model_dump())  # type: ignore[arg-type]
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": json.dumps(tool_result),
                    },
                )

                final_response = await self._client.chat.completions.create(
                    model=self._model,
                    messages=messages,  # type: ignore[arg-type]
                    max_tokens=1000,
                    temperature=0.7,
                )

                final_text = (
                    final_response.choices[0].message.content
                    or "Schedule operation completed."
                )

                # Build schedule changes from tool result if applicable
                schedule_changes = self._extract_schedule_changes(
                    tool_result,
                )

                return ChatResponse(
                    response=final_text,
                    schedule_changes=schedule_changes or None,
                    change_request_id=(
                        UUID(tool_result["change_request_id"])
                        if tool_result.get("change_request_id")
                        else None
                    ),
                )

            # No tool call — direct text response
            text = assistant_message.content or ""

            # Check if the response contains clarifying questions
            clarifying = self._extract_clarifying_questions(text)

            return ChatResponse(
                response=text,
                clarifying_questions=clarifying or None,
            )

        except Exception as e:
            self.log_failed("_call_openai_with_tools", error=e)
            return self._fallback_response(history)

    # ------------------------------------------------------------------
    # Session management
    # ------------------------------------------------------------------

    async def _load_or_create_session(
        self,
        user_id: UUID,
        role: str,
        session_id: UUID | None,
    ) -> SchedulingChatSession:
        """Load an existing session or create a new one.

        Args:
            user_id: The user's UUID.
            role: User role (admin or resource).
            session_id: Optional existing session ID.

        Returns:
            The chat session record.
        """
        if session_id:
            stmt = select(SchedulingChatSession).where(
                SchedulingChatSession.id == session_id,
                SchedulingChatSession.user_id == user_id,
                SchedulingChatSession.is_active.is_(True),
            )
            result = await self._session.execute(stmt)
            existing: SchedulingChatSession | None = result.scalar_one_or_none()
            if existing:
                return existing

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

        self.log_started(
            "create_session",
            user_id=str(user_id),
            role=role,
            session_id=str(new_session.id),
        )
        return new_session

    async def _persist_turn(
        self,
        session: SchedulingChatSession,
        user_message: str,
        assistant_response: str,
    ) -> None:
        """Persist a conversation turn to the session.

        Args:
            session: The chat session record.
            user_message: The user's message.
            assistant_response: The AI's response.
        """
        history = list(session.messages or [])
        history.append({"role": "user", "content": user_message})
        history.append({"role": "assistant", "content": assistant_response})
        session.messages = history
        await self._session.flush()

    # ------------------------------------------------------------------
    # Guardrails
    # ------------------------------------------------------------------

    @staticmethod
    def _is_off_topic(message: str) -> bool:
        """Check if a message is off-topic for scheduling.

        Args:
            message: The user's message.

        Returns:
            True if the message appears off-topic.
        """
        lower = message.lower()
        return any(pattern in lower for pattern in _OFF_TOPIC_PATTERNS)

    # ------------------------------------------------------------------
    # Response helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_schedule_changes(
        tool_result: dict[str, Any],
    ) -> list[ScheduleChange] | None:
        """Extract schedule changes from a tool result.

        Args:
            tool_result: The tool execution result dict.

        Returns:
            List of ScheduleChange or None if no changes.
        """
        changes: list[ScheduleChange] = []

        # Check for assignments in the result
        changes.extend(
            ScheduleChange(
                change_type="add",
                job_id=assignment.get("job_id"),
                staff_id=assignment.get("staff_id"),
                new_slot=assignment.get("time_slot"),
                explanation=assignment.get("explanation", ""),
            )
            for assignment in tool_result.get("assignments", [])
        )

        # Check for moved jobs
        if tool_result.get("status") == "moved":
            changes.append(
                ScheduleChange(
                    change_type="move",
                    job_id=tool_result.get("job_id"),
                    new_slot=tool_result.get("target_day"),
                    explanation="Job moved per admin request",
                ),
            )

        # Check for reshuffled jobs
        changes.extend(
            ScheduleChange(
                change_type="move",
                job_id=job.get("job_id"),
                staff_id=job.get("new_staff_id"),
                old_slot=job.get("old_slot"),
                new_slot=job.get("new_slot"),
                explanation=job.get("explanation", "Reshuffled"),
            )
            for job in tool_result.get("reassigned_jobs", [])
        )

        return changes if changes else None

    @staticmethod
    def _extract_clarifying_questions(text: str) -> list[str] | None:
        """Extract clarifying questions from AI response text.

        Looks for lines ending with '?' in the response.

        Args:
            text: The AI's response text.

        Returns:
            List of question strings or None.
        """
        questions = [
            line.strip() for line in text.split("\n") if line.strip().endswith("?")
        ]
        return questions if questions else None

    @staticmethod
    def _fallback_response(
        history: list[dict[str, Any]],
    ) -> ChatResponse:
        """Generate a fallback response when OpenAI is unavailable.

        Args:
            history: Conversation history.

        Returns:
            ChatResponse with a helpful fallback message.
        """
        last_message = ""
        if history:
            last_message = history[-1].get("content", "").lower()

        if "schedule" in last_message or "build" in last_message:
            return ChatResponse(
                response=(
                    "I'd be happy to help build a schedule. "
                    "The AI service is currently unavailable, but "
                    "you can use the Schedule Overview to manually "
                    "create assignments."
                ),
                clarifying_questions=[
                    "Which week would you like to schedule?",
                    "How many resources are available?",
                ],
            )

        if "emergency" in last_message:
            return ChatResponse(
                response=(
                    "For emergency jobs, please use the Schedule "
                    "Overview to manually insert the job into the "
                    "nearest available slot."
                ),
            )

        if "delay" in last_message or "running late" in last_message:
            return ChatResponse(
                response=(
                    "Your delay has been noted. Please contact "
                    "dispatch directly for immediate ETA updates."
                ),
            )

        return ChatResponse(
            response=(
                "I'm your scheduling assistant. I can help with "
                "building schedules, managing jobs, forecasting "
                "capacity, and handling field operations. "
                "What would you like to do?"
            ),
        )
