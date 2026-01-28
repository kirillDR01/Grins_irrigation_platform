"""Natural language constraint parser using AI.

This service converts natural language scheduling constraints into structured
parameters that can be used by the OR-Tools solver.

Validates: Schedule AI Updates Requirements 4.2-4.10
"""

import json
from typing import ClassVar
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from grins_platform.log_config import LoggerMixin
from grins_platform.models.staff import Staff
from grins_platform.schemas.schedule_explanation import (
    ParseConstraintsRequest,
    ParseConstraintsResponse,
    ParsedConstraint,
)
from grins_platform.services.ai.agent import AIAgentService


class ConstraintParserService(LoggerMixin):
    """Service for parsing natural language constraints.

    Validates: Requirements 4.2-4.10
    """

    DOMAIN = "business"

    CONSTRAINT_TYPES: ClassVar[set[str]] = {
        "staff_time",
        "job_grouping",
        "staff_restriction",
        "geographic",
    }

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the service.

        Args:
            session: Async database session
        """
        super().__init__()
        self.session = session
        self.ai_service = AIAgentService(session)

    async def parse_constraints(
        self,
        request: ParseConstraintsRequest,
    ) -> ParseConstraintsResponse:
        """Parse natural language constraints into structured format.

        Args:
            request: Constraint parsing request

        Returns:
            Parsed constraints with validation

        Validates: Requirements 4.2-4.10
        """
        self.log_started(
            "parse_constraints",
            text_length=len(request.constraint_text),
        )

        # Get known staff names for validation (Requirement 4.7)
        staff_names = await self._get_staff_names()

        # Create prompt for AI
        prompt = self._create_parsing_prompt(
            request.constraint_text,
            staff_names,
        )

        try:
            # Use existing AI service
            response_text = await self.ai_service.chat(
                user_id=UUID("00000000-0000-0000-0000-000000000000"),
                message=prompt,
                context={"staff_names": staff_names},
            )

            # Parse AI response into structured constraints
            constraints = self._parse_ai_response(response_text)

            # Validate constraints (Requirement 4.7, 4.8)
            for constraint in constraints:
                self._validate_constraint(constraint, staff_names)

            self.log_completed(
                "parse_constraints",
                constraints_count=len(constraints),
            )

            return ParseConstraintsResponse(
                constraints=constraints,
                unparseable_text=None,
            )

        except Exception as e:
            self.log_rejected(
                "parse_constraints",
                reason="ai_unavailable",
                error=str(e),
            )
            # Graceful degradation: return empty constraints with error
            return ParseConstraintsResponse(
                constraints=[],
                unparseable_text=request.constraint_text,
            )

    async def _get_staff_names(self) -> list[str]:
        """Get list of known staff names for validation.

        Returns:
            List of staff names
        """
        try:
            result = await self.session.execute(
                select(Staff.name).where(Staff.is_active),
            )
            staff = result.scalars().all()
            return list(staff)
        except Exception as e:
            # Fallback to empty list if database unavailable
            self.log_rejected(
                "_get_staff_names",
                reason="database_error",
                error=str(e),
            )
            return []

    def _create_parsing_prompt(
        self,
        constraint_text: str,
        staff_names: list[str],
    ) -> str:
        """Create prompt for constraint parsing.

        Validates: Requirements 4.3-4.6

        Args:
            constraint_text: Natural language constraint
            staff_names: Known staff names

        Returns:
            Prompt for AI
        """
        staff_list = ", ".join(staff_names)
        return f"""Parse this scheduling constraint into structured format:

"{constraint_text}"

Known staff: {staff_list}

Supported constraint types:
1. staff_time: Time restrictions for staff (Requirement 4.3)
   Example: "Don't schedule Viktor before 10am on Mondays"
   Parameters: staff_name, day_of_week, start_time, end_time

2. job_grouping: Keep jobs together (Requirement 4.4)
   Example: "Keep Johnson and Smith jobs together"
   Parameters: customer_names (list)

3. staff_restriction: Staff-job restrictions (Requirement 4.5)
   Example: "Vas shouldn't do lake pump jobs"
   Parameters: staff_name, job_type, restriction_type

4. geographic: Geographic preferences (Requirement 4.6)
   Example: "Finish Eden Prairie by noon"
   Parameters: city, time_constraint

Return ONLY a JSON array of constraints in this format:
[
  {{
    "constraint_type": "staff_time",
    "description": "Viktor unavailable before 10am on Mondays",
    "parameters": {{
      "staff_name": "Viktor",
      "day_of_week": "Monday",
      "start_time": "10:00"
    }}
  }}
]

If the constraint cannot be parsed, return an empty array: []
"""

    def _parse_ai_response(
        self,
        response_text: str,
    ) -> list[ParsedConstraint]:
        """Parse AI response into constraint objects.

        Args:
            response_text: AI response text

        Returns:
            List of parsed constraints
        """
        # Extract JSON from response
        try:
            # Try to find JSON array in response
            start = response_text.find("[")
            end = response_text.rfind("]") + 1
            if start == -1 or end == 0:
                return []

            json_text = response_text[start:end]
            constraints_data = json.loads(json_text)

            constraints = []
            for data in constraints_data:
                # Filter out None values from parameters
                params = data.get("parameters", {})
                filtered_params = {k: v for k, v in params.items() if v is not None}
                constraint = ParsedConstraint(
                    constraint_type=data.get("constraint_type", ""),
                    description=data.get("description", ""),
                    parameters=filtered_params,
                    validation_errors=[],
                )
                constraints.append(constraint)

        except json.JSONDecodeError:
            self.log_rejected(
                "parse_ai_response",
                reason="invalid_json",
                response_text=response_text[:200],
            )
            return []
        else:
            return constraints

    def _validate_constraint(
        self,
        constraint: ParsedConstraint,
        staff_names: list[str],
    ) -> None:
        """Validate a parsed constraint.

        Validates: Requirements 4.7, 4.8

        Args:
            constraint: Constraint to validate
            staff_names: Known staff names
        """
        # Validate constraint type
        if constraint.constraint_type not in self.CONSTRAINT_TYPES:
            constraint.validation_errors.append(
                f"Unknown constraint type: {constraint.constraint_type}",
            )

        # Validate staff names (Requirement 4.7, 4.8)
        if "staff_name" in constraint.parameters:
            staff_name = constraint.parameters["staff_name"]
            if isinstance(staff_name, str) and staff_name not in staff_names:
                known_staff = ", ".join(staff_names)
                constraint.validation_errors.append(
                    f"Unknown staff name: {staff_name}. Known staff: {known_staff}",
                )

        # Validate required parameters by type
        if constraint.constraint_type == "staff_time":
            required = {"staff_name", "day_of_week"}
            missing = required - set(constraint.parameters.keys())
            if missing:
                constraint.validation_errors.append(
                    f"Missing required parameters: {', '.join(missing)}",
                )

        elif constraint.constraint_type == "job_grouping":
            if "customer_names" not in constraint.parameters:
                constraint.validation_errors.append(
                    "Missing required parameter: customer_names",
                )

        elif constraint.constraint_type == "staff_restriction":
            required = {"staff_name", "job_type"}
            missing = required - set(constraint.parameters.keys())
            if missing:
                constraint.validation_errors.append(
                    f"Missing required parameters: {', '.join(missing)}",
                )

        elif constraint.constraint_type == "geographic":
            required = {"city"}
            missing = required - set(constraint.parameters.keys())
            if missing:
                constraint.validation_errors.append(
                    f"Missing required parameters: {', '.join(missing)}",
                )
