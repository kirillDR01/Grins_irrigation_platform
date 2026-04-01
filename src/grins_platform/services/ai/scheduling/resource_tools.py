"""
Resource scheduling tool functions for OpenAI function calling.

Provides 10 resource-facing scheduling tools that the
SchedulingChatService invokes via OpenAI function calling when a
Resource (field technician) interacts with the AI Chat.

Validates: Requirements 14.1-14.10, 15.1-15.10
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from grins_platform.log_config import LoggerMixin

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class ResourceSchedulingTools(LoggerMixin):
    """Resource-facing scheduling tool functions for OpenAI function calling.

    Each tool is an async method that validates inputs, logs
    execution, and returns structured dict results. Currently
    implemented as stubs returning placeholder data — the actual
    logic will be wired to existing services in a later task.

    Attributes:
        DOMAIN: Logging domain for structured log events.
    """

    DOMAIN = "scheduling"

    def __init__(self, session: AsyncSession) -> None:
        """Initialize resource scheduling tools.

        Args:
            session: Async database session for data access.
        """
        super().__init__()
        self._session = session

    async def report_delay(
        self,
        resource_id: str,
        delay_minutes: int,
    ) -> dict[str, Any]:
        """Report a delay and recalculate downstream ETAs.

        Alerts admin if customer time windows are at risk.

        Args:
            resource_id: UUID string of the resource reporting.
            delay_minutes: Number of minutes delayed.

        Returns:
            Dict with updated ETAs and at-risk windows.
        """
        self.log_started(
            "report_delay",
            resource_id=resource_id,
            delay_minutes=delay_minutes,
        )

        result: dict[str, Any] = {
            "status": "delay_reported",
            "resource_id": resource_id,
            "delay_minutes": delay_minutes,
            "updated_etas": [],
            "at_risk_windows": [],
            "admin_alerted": delay_minutes >= 40,
        }

        self.log_completed(
            "report_delay",
            resource_id=resource_id,
            delay_minutes=delay_minutes,
            admin_alerted=result["admin_alerted"],
        )
        return result

    async def get_prejob_info(
        self,
        resource_id: str,
        job_id: str,
    ) -> dict[str, Any]:
        """Get pre-job information for a specific job.

        Pulls job template, customer profile, and equipment checklist.

        Args:
            resource_id: UUID string of the resource.
            job_id: UUID string of the job.

        Returns:
            Dict with pre-job checklist and customer details.
        """
        self.log_started(
            "get_prejob_info",
            resource_id=resource_id,
            job_id=job_id,
        )

        result: dict[str, Any] = {
            "status": "info_retrieved",
            "resource_id": resource_id,
            "job_id": job_id,
            "job_type": None,
            "customer_name": None,
            "customer_address": None,
            "required_equipment": [],
            "known_issues": [],
            "gate_code": None,
            "special_instructions": None,
            "estimated_duration": 0,
        }

        self.log_completed(
            "get_prejob_info",
            resource_id=resource_id,
            job_id=job_id,
        )
        return result

    async def request_followup(
        self,
        resource_id: str,
        job_id: str,
        field_notes: str,
        parts_needed: list[str] | None = None,
    ) -> dict[str, Any]:
        """Request a follow-up job, creating a ChangeRequest for admin.

        Args:
            resource_id: UUID string of the resource.
            job_id: UUID string of the current job.
            field_notes: Technician's field notes.
            parts_needed: Optional list of parts needed.

        Returns:
            Dict with change request ID and status.
        """
        self.log_started(
            "request_followup",
            resource_id=resource_id,
            job_id=job_id,
        )

        result: dict[str, Any] = {
            "status": "change_request_created",
            "resource_id": resource_id,
            "job_id": job_id,
            "request_type": "followup_job",
            "change_request_id": None,
            "field_notes": field_notes,
            "parts_needed": parts_needed or [],
            "recommended_action": "Schedule follow-up within 48 hours",
        }

        self.log_completed(
            "request_followup",
            resource_id=resource_id,
            job_id=job_id,
            change_request_id=result["change_request_id"],
        )
        return result

    async def report_access_issue(
        self,
        resource_id: str,
        job_id: str,
        issue_type: str,
    ) -> dict[str, Any]:
        """Report a job site access issue.

        Checks customer profile for alternative access info and
        creates a ChangeRequest if the issue cannot be resolved.

        Args:
            resource_id: UUID string of the resource.
            job_id: UUID string of the job.
            issue_type: Type of access issue (gate_locked,
                no_access_code, dog_on_property, construction_blocked,
                customer_not_home).

        Returns:
            Dict with resolution info or change request.
        """
        self.log_started(
            "report_access_issue",
            resource_id=resource_id,
            job_id=job_id,
            issue_type=issue_type,
        )

        result: dict[str, Any] = {
            "status": "access_issue_reported",
            "resource_id": resource_id,
            "job_id": job_id,
            "issue_type": issue_type,
            "alternative_access": None,
            "customer_contacted": False,
            "change_request_id": None,
            "recommended_action": "Contact customer for access",
        }

        self.log_completed(
            "report_access_issue",
            resource_id=resource_id,
            job_id=job_id,
            issue_type=issue_type,
        )
        return result

    async def find_nearby_work(
        self,
        resource_id: str,
        location: str,
    ) -> dict[str, Any]:
        """Find available jobs within 15-minute drive radius.

        Filters by resource skills and truck equipment.

        Args:
            resource_id: UUID string of the resource.
            location: Current location (lat,lng or address).

        Returns:
            Dict with nearby available jobs matching skills/equipment.
        """
        self.log_started(
            "find_nearby_work",
            resource_id=resource_id,
        )

        result: dict[str, Any] = {
            "status": "search_complete",
            "resource_id": resource_id,
            "location": location,
            "radius_minutes": 15,
            "nearby_jobs": [],
            "total_found": 0,
        }

        self.log_completed(
            "find_nearby_work",
            resource_id=resource_id,
            total_found=result["total_found"],
        )
        return result

    async def request_resequence(
        self,
        resource_id: str,
        reason: str,
        shop_stop: bool = False,
    ) -> dict[str, Any]:
        """Request route resequencing, creating a ChangeRequest.

        Args:
            resource_id: UUID string of the resource.
            reason: Reason for resequence request.
            shop_stop: Whether a shop stop is needed.

        Returns:
            Dict with feasibility check and change request.
        """
        self.log_started(
            "request_resequence",
            resource_id=resource_id,
            shop_stop=shop_stop,
        )

        result: dict[str, Any] = {
            "status": "change_request_created",
            "resource_id": resource_id,
            "request_type": "resequence",
            "reason": reason,
            "shop_stop": shop_stop,
            "feasibility": "pending_review",
            "change_request_id": None,
            "recommended_action": "Review route resequence request",
        }

        self.log_completed(
            "request_resequence",
            resource_id=resource_id,
            change_request_id=result["change_request_id"],
        )
        return result

    async def request_assistance(
        self,
        resource_id: str,
        job_id: str,
        skill_needed: str,
    ) -> dict[str, Any]:
        """Request crew assistance for a job.

        Finds nearby qualified resources and creates a ChangeRequest.

        Args:
            resource_id: UUID string of the requesting resource.
            job_id: UUID string of the job needing assistance.
            skill_needed: Specific skill needed for assistance.

        Returns:
            Dict with nearby qualified resources and change request.
        """
        self.log_started(
            "request_assistance",
            resource_id=resource_id,
            job_id=job_id,
            skill_needed=skill_needed,
        )

        result: dict[str, Any] = {
            "status": "change_request_created",
            "resource_id": resource_id,
            "job_id": job_id,
            "request_type": "crew_assist",
            "skill_needed": skill_needed,
            "nearby_qualified": [],
            "change_request_id": None,
            "recommended_action": "Dispatch nearest qualified resource",
        }

        self.log_completed(
            "request_assistance",
            resource_id=resource_id,
            job_id=job_id,
            skill_needed=skill_needed,
        )
        return result

    async def log_parts(
        self,
        resource_id: str,
        job_id: str,
        parts_list: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Log parts used on a job and update truck inventory.

        Flags low stock when inventory drops below reorder threshold.

        Args:
            resource_id: UUID string of the resource.
            job_id: UUID string of the job.
            parts_list: List of dicts with part_name and quantity_used.

        Returns:
            Dict with updated inventory and low-stock warnings.
        """
        self.log_started(
            "log_parts",
            resource_id=resource_id,
            job_id=job_id,
            parts_count=len(parts_list),
        )

        result: dict[str, Any] = {
            "status": "parts_logged",
            "resource_id": resource_id,
            "job_id": job_id,
            "parts_logged": parts_list,
            "inventory_updates": [],
            "low_stock_warnings": [],
        }

        self.log_completed(
            "log_parts",
            resource_id=resource_id,
            job_id=job_id,
            parts_count=len(parts_list),
            low_stock_count=len(result["low_stock_warnings"]),
        )
        return result

    async def get_tomorrow_schedule(
        self,
        resource_id: str,
    ) -> dict[str, Any]:
        """Get tomorrow's schedule with full details.

        Args:
            resource_id: UUID string of the resource.

        Returns:
            Dict with tomorrow's jobs, route, and prep notes.
        """
        self.log_started(
            "get_tomorrow_schedule",
            resource_id=resource_id,
        )

        result: dict[str, Any] = {
            "status": "schedule_retrieved",
            "resource_id": resource_id,
            "schedule_date": None,
            "total_jobs": 0,
            "jobs": [],
            "route_summary": {},
            "prep_notes": [],
        }

        self.log_completed(
            "get_tomorrow_schedule",
            resource_id=resource_id,
            total_jobs=result["total_jobs"],
        )
        return result

    async def request_upgrade_quote(
        self,
        resource_id: str,
        job_id: str,
        upgrade_type: str,
    ) -> dict[str, Any]:
        """Request an upgrade quote for a customer.

        Pulls pricing, creates a quote draft, and creates a
        ChangeRequest for admin approval.

        Args:
            resource_id: UUID string of the resource.
            job_id: UUID string of the current job.
            upgrade_type: Type of upgrade to quote.

        Returns:
            Dict with quote draft and change request.
        """
        self.log_started(
            "request_upgrade_quote",
            resource_id=resource_id,
            job_id=job_id,
            upgrade_type=upgrade_type,
        )

        result: dict[str, Any] = {
            "status": "change_request_created",
            "resource_id": resource_id,
            "job_id": job_id,
            "request_type": "upgrade_quote",
            "upgrade_type": upgrade_type,
            "quote_draft": None,
            "estimated_price": None,
            "change_request_id": None,
            "recommended_action": "Review and send upgrade quote to customer",
        }

        self.log_completed(
            "request_upgrade_quote",
            resource_id=resource_id,
            job_id=job_id,
            upgrade_type=upgrade_type,
        )
        return result

    async def dispatch_tool_call(
        self,
        function_name: str,
        arguments: str,
    ) -> dict[str, Any]:
        """Dispatch an OpenAI function call to the correct tool method.

        Args:
            function_name: Name of the tool function to call.
            arguments: JSON string of function arguments.

        Returns:
            Tool result dict.

        Raises:
            ValueError: If function_name is not a known tool.
        """
        args = json.loads(arguments)

        tool_map: dict[str, Any] = {
            "report_delay": self.report_delay,
            "get_prejob_info": self.get_prejob_info,
            "request_followup": self.request_followup,
            "report_access_issue": self.report_access_issue,
            "find_nearby_work": self.find_nearby_work,
            "request_resequence": self.request_resequence,
            "request_assistance": self.request_assistance,
            "log_parts": self.log_parts,
            "get_tomorrow_schedule": self.get_tomorrow_schedule,
            "request_upgrade_quote": self.request_upgrade_quote,
        }

        handler = tool_map.get(function_name)
        if handler is None:
            msg = f"Unknown resource tool: {function_name}"
            raise ValueError(msg)

        result: dict[str, Any] = await handler(**args)
        return result


def get_tool_definitions() -> list[dict[str, Any]]:
    """Return OpenAI function calling tool definitions for all 10 resource tools.

    Returns:
        List of tool definition dicts in OpenAI function calling format.
    """
    return [
        {
            "type": "function",
            "function": {
                "name": "report_delay",
                "description": (
                    "Report that you are running behind schedule. "
                    "Recalculates downstream ETAs and alerts admin "
                    "if customer windows are at risk."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "resource_id": {
                            "type": "string",
                            "description": "Your resource ID.",
                        },
                        "delay_minutes": {
                            "type": "integer",
                            "description": "How many minutes behind you are.",
                        },
                    },
                    "required": ["resource_id", "delay_minutes"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_prejob_info",
                "description": (
                    "Get pre-job information including customer details, "
                    "equipment checklist, gate codes, and special instructions."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "resource_id": {
                            "type": "string",
                            "description": "Your resource ID.",
                        },
                        "job_id": {
                            "type": "string",
                            "description": "The job ID to get info for.",
                        },
                    },
                    "required": ["resource_id", "job_id"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "request_followup",
                "description": (
                    "Request a follow-up job for a customer. "
                    "Creates a change request for admin approval."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "resource_id": {
                            "type": "string",
                            "description": "Your resource ID.",
                        },
                        "job_id": {
                            "type": "string",
                            "description": "The current job ID.",
                        },
                        "field_notes": {
                            "type": "string",
                            "description": (
                                "Your field notes about why follow-up is needed."
                            ),
                        },
                        "parts_needed": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Parts needed for the follow-up.",
                        },
                    },
                    "required": ["resource_id", "job_id", "field_notes"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "report_access_issue",
                "description": (
                    "Report a job site access issue such as locked gate, "
                    "no access code, or customer not home."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "resource_id": {
                            "type": "string",
                            "description": "Your resource ID.",
                        },
                        "job_id": {
                            "type": "string",
                            "description": "The job ID with the access issue.",
                        },
                        "issue_type": {
                            "type": "string",
                            "enum": [
                                "gate_locked",
                                "no_access_code",
                                "dog_on_property",
                                "construction_blocked",
                                "customer_not_home",
                            ],
                            "description": "Type of access issue.",
                        },
                    },
                    "required": ["resource_id", "job_id", "issue_type"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "find_nearby_work",
                "description": (
                    "Find available jobs within a 15-minute drive "
                    "that match your skills and truck equipment."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "resource_id": {
                            "type": "string",
                            "description": "Your resource ID.",
                        },
                        "location": {
                            "type": "string",
                            "description": (
                                "Your current location (lat,lng or address)."
                            ),
                        },
                    },
                    "required": ["resource_id", "location"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "request_resequence",
                "description": (
                    "Request to change the order of your remaining jobs. "
                    "Creates a change request for admin approval."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "resource_id": {
                            "type": "string",
                            "description": "Your resource ID.",
                        },
                        "reason": {
                            "type": "string",
                            "description": "Reason for resequence request.",
                        },
                        "shop_stop": {
                            "type": "boolean",
                            "description": "Whether you need a shop stop.",
                        },
                    },
                    "required": ["resource_id", "reason"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "request_assistance",
                "description": (
                    "Request crew assistance for a job that needs "
                    "a specific skill you don't have."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "resource_id": {
                            "type": "string",
                            "description": "Your resource ID.",
                        },
                        "job_id": {
                            "type": "string",
                            "description": "The job needing assistance.",
                        },
                        "skill_needed": {
                            "type": "string",
                            "description": "The specific skill needed.",
                        },
                    },
                    "required": ["resource_id", "job_id", "skill_needed"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "log_parts",
                "description": (
                    "Log parts used on a job. Updates truck inventory "
                    "and flags low stock."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "resource_id": {
                            "type": "string",
                            "description": "Your resource ID.",
                        },
                        "job_id": {
                            "type": "string",
                            "description": "The job ID parts were used on.",
                        },
                        "parts_list": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "part_name": {"type": "string"},
                                    "quantity_used": {"type": "integer"},
                                },
                                "required": ["part_name", "quantity_used"],
                            },
                            "description": "List of parts used with quantities.",
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
                "description": (
                    "Get your schedule for tomorrow with full job details, "
                    "route, and prep notes."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "resource_id": {
                            "type": "string",
                            "description": "Your resource ID.",
                        },
                    },
                    "required": ["resource_id"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "request_upgrade_quote",
                "description": (
                    "Request an upgrade quote for a customer's equipment. "
                    "Creates a quote draft and change request."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "resource_id": {
                            "type": "string",
                            "description": "Your resource ID.",
                        },
                        "job_id": {
                            "type": "string",
                            "description": "The current job ID.",
                        },
                        "upgrade_type": {
                            "type": "string",
                            "description": "Type of upgrade to quote.",
                        },
                    },
                    "required": ["resource_id", "job_id", "upgrade_type"],
                },
            },
        },
    ]
