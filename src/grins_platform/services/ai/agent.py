"""AI Agent Service using OpenAI.

Validates: AI Assistant Requirements 1.1, 1.2, 1.5, 1.8-1.12
"""

import os
from collections.abc import AsyncIterator
from typing import Any
from uuid import UUID

from openai import AsyncOpenAI
from sqlalchemy.ext.asyncio import AsyncSession

from grins_platform.log_config import LoggerMixin
from grins_platform.services.ai.audit import AuditService
from grins_platform.services.ai.context.builder import ContextBuilder
from grins_platform.services.ai.prompts.system import SYSTEM_PROMPT
from grins_platform.services.ai.rate_limiter import RateLimitError, RateLimitService


class AIAgentError(Exception):
    """Base exception for AI agent errors."""


class AIAgentService(LoggerMixin):
    """Service for AI agent interactions using OpenAI."""

    DOMAIN = "business"

    def __init__(
        self,
        session: AsyncSession,
        model: str = "gpt-4o-mini",
    ) -> None:
        """Initialize AI agent service.

        Args:
            session: Database session
            model: AI model to use (default: gpt-4o-mini)
        """
        super().__init__()
        self.session = session
        self.model = model
        self.rate_limiter = RateLimitService(session)
        self.audit_service = AuditService(session)
        self.context_builder = ContextBuilder(session)
        self.system_prompt = SYSTEM_PROMPT

        # Initialize OpenAI client
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            self.client = None
        else:
            self.client = AsyncOpenAI(api_key=api_key)

    async def chat(
        self,
        user_id: UUID,
        message: str,
        context: dict[str, Any] | None = None,
    ) -> str:
        """Process a chat message and return response.

        Args:
            user_id: User making the request
            message: User's message
            context: Optional context data

        Returns:
            AI response text

        Raises:
            RateLimitError: If rate limit exceeded
            AIAgentError: If AI processing fails
        """
        self.log_started("chat", user_id=str(user_id), message_length=len(message))

        # Check rate limit
        await self.rate_limiter.check_limit(user_id)

        try:
            # Build context from database if not provided
            if context is None:
                context = await self.context_builder.build_query_context(message)

            # For now, return a placeholder response
            # In production, this would call the actual AI model
            response = await self._generate_response(message, context)

            # Record usage
            await self.rate_limiter.record_usage(
                user_id,
                input_tokens=len(message) // 4,  # Rough estimate
                output_tokens=len(response) // 4,
                cost_usd=0.001,  # Placeholder cost
            )

            self.log_completed("chat", response_length=len(response))
        except RateLimitError:
            raise
        except Exception as e:
            self.log_failed("chat", error=e)
            msg = f"Failed to process chat: {e}"
            raise AIAgentError(msg) from e
        else:
            return response

    async def chat_stream(
        self,
        user_id: UUID,
        message: str,
        context: dict[str, Any] | None = None,
    ) -> AsyncIterator[str]:
        """Process a chat message and stream response.

        Args:
            user_id: User making the request
            message: User's message
            context: Optional context data

        Yields:
            Response chunks

        Raises:
            RateLimitError: If rate limit exceeded
            AIAgentError: If AI processing fails
        """
        self.log_started(
            "chat_stream", user_id=str(user_id), message_length=len(message),
        )

        # Check rate limit
        await self.rate_limiter.check_limit(user_id)

        try:
            # Build context from database if not provided
            if context is None:
                context = await self.context_builder.build_query_context(message)

            # Generate response and yield in chunks
            response = await self._generate_response(message, context)

            # Simulate streaming by yielding chunks
            chunk_size = 50
            for i in range(0, len(response), chunk_size):
                yield response[i : i + chunk_size]

            # Record usage
            await self.rate_limiter.record_usage(
                user_id,
                input_tokens=len(message) // 4,
                output_tokens=len(response) // 4,
                cost_usd=0.001,
            )

            self.log_completed("chat_stream", response_length=len(response))

        except RateLimitError:
            raise
        except Exception as e:
            self.log_failed("chat_stream", error=e)
            msg = f"Failed to stream chat: {e}"
            raise AIAgentError(msg) from e

    async def _generate_response(
        self,
        message: str,
        context: dict[str, Any] | None = None,
    ) -> str:
        """Generate AI response using OpenAI.

        Args:
            message: User's message
            context: Optional context data

        Returns:
            Generated response
        """
        # If no OpenAI client, use fallback responses with real data
        if not self.client:
            return self._fallback_response(message, context)

        try:
            # Build messages for OpenAI
            messages: list[dict[str, str]] = [
                {"role": "system", "content": self.system_prompt},
            ]

            # Add context if provided (includes real business data)
            if context:
                bd = context.get("business_data", {})
                jobs = bd.get("jobs", {})
                jobs_status = jobs.get("by_status", {})
                appts = bd.get("appointments", {}).get("today", {})
                context_str = f"""
Current Business Data (as of {context.get('current_time', 'now')}):

CUSTOMERS:
- Total customers: {bd.get('customers', {}).get('total', 0)}

JOBS:
- Requested: {jobs_status.get('requested', 0)}
- Approved: {jobs_status.get('approved', 0)}
- Scheduled: {jobs_status.get('scheduled', 0)}
- In Progress: {jobs_status.get('in_progress', 0)}
- Completed: {jobs_status.get('completed', 0)}
- Total Pending (requested + approved): {jobs.get('total_pending', 0)}

TODAY'S APPOINTMENTS ({context.get('today', 'today')}):
- Total scheduled for today: {appts.get('total', 0)}
- Scheduled (not started): {appts.get('scheduled', 0)}
- In Progress: {appts.get('in_progress', 0)}
- Completed: {appts.get('completed', 0)}

STAFF:
- Active staff members: {bd.get('staff', {}).get('total_active', 0)}

Use this data to answer the user's question accurately.
If the data shows 0 for something, report that honestly.
"""
                messages.append({"role": "system", "content": context_str})

            messages.append({"role": "user", "content": message})

            # Call OpenAI API
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,  # type: ignore[arg-type]
                max_tokens=500,
                temperature=0.7,
            )

            content = response.choices[0].message.content
        except Exception as e:
            self.log_failed("_generate_response", error=e)
            # Fall back to placeholder responses on error
            return self._fallback_response(message, context)
        else:
            return content or "I couldn't generate a response."

    def _fallback_response(
        self,
        message: str,
        context: dict[str, Any] | None = None,
    ) -> str:
        """Generate fallback response when OpenAI is unavailable.

        Uses real business data from context to provide accurate answers.

        Args:
            message: User's message
            context: Context with business data

        Returns:
            Fallback response with real data
        """
        message_lower = message.lower()
        business_data = context.get("business_data", {}) if context else {}
        today = context.get("today", "today") if context else "today"

        # Handle job/schedule related queries with real data
        if "schedule" in message_lower or "job" in message_lower:
            appointments_today = business_data.get("appointments", {}).get("today", {})
            total_today = appointments_today.get("total", 0)
            scheduled = appointments_today.get("scheduled", 0)
            completed = appointments_today.get("completed", 0)
            in_progress = appointments_today.get("in_progress", 0)

            if "today" in message_lower or "scheduled" in message_lower:
                return (
                    f"Based on the current data for {today}:\n\n"
                    f"• Total appointments scheduled: {total_today}\n"
                    f"• Scheduled (not started): {scheduled}\n"
                    f"• In progress: {in_progress}\n"
                    f"• Completed: {completed}\n\n"
                    "Would you like me to help with scheduling or route optimization?"
                )

            jobs_data = business_data.get("jobs", {})
            by_status = jobs_data.get("by_status", {})
            return (
                f"Here's the current job status:\n\n"
                f"• Requested: {by_status.get('requested', 0)}\n"
                f"• Approved: {by_status.get('approved', 0)}\n"
                f"• Scheduled: {by_status.get('scheduled', 0)}\n"
                f"• In Progress: {by_status.get('in_progress', 0)}\n"
                f"• Completed: {by_status.get('completed', 0)}\n\n"
                f"Total pending (needs scheduling): {jobs_data.get('total_pending', 0)}"
            )

        if "customer" in message_lower:
            customers = business_data.get("customers", {})
            return (
                f"Customer Summary:\n\n"
                f"• Total customers: {customers.get('total', 0)}\n\n"
                "Would you like to search for a specific customer or see more details?"
            )

        if "staff" in message_lower:
            staff = business_data.get("staff", {})
            return (
                f"Staff Summary:\n\n"
                f"• Active staff members: {staff.get('total_active', 0)}\n\n"
                "Would you like to see staff availability or assignments?"
            )

        if "categorize" in message_lower or "category" in message_lower:
            return (
                "I can categorize job requests for you. Please provide the job "
                "description and I'll determine if it's ready to schedule or "
                "requires an estimate."
            )

        if "estimate" in message_lower:
            return (
                "I can help generate an estimate. Please provide the job details "
                "and property information, and I'll calculate the costs."
            )

        if "message" in message_lower or "communication" in message_lower:
            return (
                "I can draft customer communications. What type of message would "
                "you like? (confirmation, reminder, follow-up, etc.)"
            )

        # Default response with summary
        appointments_today = business_data.get("appointments", {}).get("today", {})
        jobs_data = business_data.get("jobs", {})
        customers = business_data.get("customers", {})

        return (
            f"Here's a quick summary of your business:\n\n"
            f"• Total customers: {customers.get('total', 0)}\n"
            f"• Appointments today: {appointments_today.get('total', 0)}\n"
            f"• Jobs pending: {jobs_data.get('total_pending', 0)}\n\n"
            "I can help with scheduling, job categorization, estimates, "
            "and customer communications. What would you like assistance with?"
        )
