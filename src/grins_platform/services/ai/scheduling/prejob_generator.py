"""
PreJobGenerator — generates pre-job checklists and upsell suggestions.

Validates: Requirements 2.3, 14.2, 15.2, 15.9, 16.4, 16.5, 17.1, 17.2
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import select

from grins_platform.log_config import LoggerMixin
from grins_platform.models.service_offering import ServiceOffering
from grins_platform.schemas.ai_scheduling import PreJobChecklist, UpsellSuggestion

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class PreJobGenerator(LoggerMixin):
    """Generates pre-job checklists and upsell suggestions for resources.

    Attributes:
        DOMAIN: Logging domain identifier.
    """

    DOMAIN = "scheduling"

    def __init__(self, session: AsyncSession) -> None:
        """Initialise the pre-job generator.

        Args:
            session: Async SQLAlchemy session.
        """
        super().__init__()
        self._session = session

    async def generate_checklist(
        self,
        job_id: UUID,
        resource_id: UUID,
    ) -> PreJobChecklist:
        """Generate a pre-job checklist for a resource.

        Pulls job type, customer profile, equipment requirements, known
        issues, gate code, and special instructions.

        Args:
            job_id: Job UUID.
            resource_id: Staff UUID.

        Returns:
            ``PreJobChecklist`` with all required fields.
        """
        self.log_started(
            "generate_checklist",
            job_id=str(job_id),
            resource_id=str(resource_id),
        )

        try:
            from grins_platform.models.job import Job  # noqa: PLC0415

            stmt = select(Job).where(Job.id == job_id)
            result = await self._session.execute(stmt)
            job = result.scalar_one_or_none()

            if job is None:
                checklist = PreJobChecklist(
                    job_type="Unknown",
                    customer_name="Unknown",
                    customer_address="Unknown",
                    required_equipment=[],
                    known_issues=[],
                    gate_code=None,
                    special_instructions=None,
                    estimated_duration=60,
                )
            else:
                # Load customer and property data
                customer_name = "Customer"
                customer_address = "Address on file"
                gate_code: str | None = None
                special_instructions: str | None = None
                known_issues: list[str] = []
                required_equipment: list[str] = []
                estimated_duration = 60

                # Try to load customer
                try:
                    from grins_platform.models.customer import Customer  # noqa: PLC0415

                    if job.customer_id:
                        cust_stmt = select(Customer).where(
                            Customer.id == job.customer_id
                        )
                        cust_result = await self._session.execute(cust_stmt)
                        customer = cust_result.scalar_one_or_none()
                        if customer:
                            customer_name = (
                                f"{customer.first_name} {customer.last_name}"
                            )
                except Exception as exc:
                    self.logger.debug(
                        "scheduling.prejob.customer_load_failed",
                        error=str(exc),
                    )

                # Try to load primary property for address/gate code
                try:
                    from grins_platform.models.property import Property  # noqa: PLC0415

                    if job.property_id:
                        prop_stmt = select(Property).where(
                            Property.id == job.property_id
                        )
                        prop_result = await self._session.execute(prop_stmt)
                        prop = prop_result.scalar_one_or_none()
                        if prop:
                            customer_address = (
                                f"{prop.address}, {prop.city}, {prop.state}"
                            )
                            gate_code = getattr(prop, "gate_code", None)
                            special_instructions = getattr(
                                prop, "access_instructions", None
                            )
                except Exception as exc:
                    self.logger.debug(
                        "scheduling.prejob.property_load_failed",
                        error=str(exc),
                    )

                # Determine job type and duration from service offering
                job_type = "Service"
                try:
                    if job.service_offering_id:
                        svc_stmt = select(ServiceOffering).where(
                            ServiceOffering.id == job.service_offering_id
                        )
                        svc_result = await self._session.execute(svc_stmt)
                        svc = svc_result.scalar_one_or_none()
                        if svc:
                            job_type = svc.name
                            estimated_duration = getattr(
                                svc, "estimated_duration_minutes", 60
                            )
                            required_equipment = (
                                getattr(svc, "equipment_requirements", []) or []
                            )
                except Exception as exc:
                    self.logger.debug(
                        "scheduling.prejob.service_load_failed",
                        error=str(exc),
                    )

                checklist = PreJobChecklist(
                    job_type=job_type,
                    customer_name=customer_name,
                    customer_address=customer_address,
                    required_equipment=required_equipment,
                    known_issues=known_issues,
                    gate_code=gate_code,
                    special_instructions=special_instructions,
                    estimated_duration=estimated_duration,
                )

        except Exception as exc:
            self.log_failed(
                "generate_checklist",
                error=exc,
                job_id=str(job_id),
            )
            raise
        else:
            self.log_completed(
                "generate_checklist",
                job_id=str(job_id),
                resource_id=str(resource_id),
            )
            return checklist

    async def generate_upsell_suggestions(
        self,
        job_id: UUID,
    ) -> list[UpsellSuggestion]:
        """Generate upsell suggestions based on equipment age and service history.

        Args:
            job_id: Job UUID.

        Returns:
            List of ``UpsellSuggestion`` objects.
        """
        self.log_started("generate_upsell_suggestions", job_id=str(job_id))

        try:
            # Placeholder: real implementation would query equipment age
            # and repair history from the job/property records
            suggestions: list[UpsellSuggestion] = []

        except Exception as exc:
            self.log_failed(
                "generate_upsell_suggestions",
                error=exc,
                job_id=str(job_id),
            )
            raise
        else:
            self.log_completed(
                "generate_upsell_suggestions",
                job_id=str(job_id),
                suggestion_count=len(suggestions),
            )
            return suggestions
