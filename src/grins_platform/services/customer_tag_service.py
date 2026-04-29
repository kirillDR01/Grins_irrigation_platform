"""CustomerTag service for business logic.

Implements diff-based save: preserves system tags, inserts new manual tags,
deletes removed manual tags.

Validates: Requirements 12.5, 12.6, 12.7
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError

from grins_platform.log_config import LoggerMixin
from grins_platform.schemas.customer_tag import (
    CustomerTagResponse,
    CustomerTagsUpdateRequest,
    CustomerTagsUpdateResponse,
    TagInput,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from grins_platform.repositories.customer_tag_repository import (
        CustomerTagRepository,
    )


class CustomerTagService(LoggerMixin):
    """Service for customer tag operations.

    Validates: Requirements 12.5, 12.6, 12.7
    """

    DOMAIN = "customer_tags"

    def __init__(self, repo: CustomerTagRepository) -> None:
        """Initialize service with repository."""
        super().__init__()
        self.repo = repo

    async def get_tags(self, customer_id: UUID) -> list[CustomerTagResponse]:
        """Return all tags for a customer.

        Args:
            customer_id: Customer UUID

        Returns:
            List of CustomerTagResponse
        """
        self.log_started("get_tags", customer_id=str(customer_id))
        tags = await self.repo.get_by_customer_id(customer_id)
        result = [CustomerTagResponse.model_validate(t) for t in tags]
        self.log_completed("get_tags", count=len(result))
        return result

    async def save_tags(
        self,
        customer_id: UUID,
        request: CustomerTagsUpdateRequest,
        session: AsyncSession,
    ) -> CustomerTagsUpdateResponse:
        """Diff-based save for customer tags.

        Preserves system tags, inserts new manual tags, deletes removed ones.

        Args:
            customer_id: Customer UUID
            request: Incoming tag list (manual tags only)
            session: AsyncSession for transaction

        Returns:
            CustomerTagsUpdateResponse with final tag list

        Raises:
            HTTPException 422: Duplicate labels in request
            HTTPException 409: Race condition unique violation
        """
        self.log_started("save_tags", customer_id=str(customer_id))

        existing = await self.repo.get_by_customer_id(customer_id)
        system_tags = [t for t in existing if t.source == "system"]
        manual_tags = [t for t in existing if t.source == "manual"]

        incoming_labels = {t.label for t in request.tags}
        existing_manual_labels = {t.label: t for t in manual_tags}

        # Delete manual tags not in incoming set
        to_delete = [t.id for t in manual_tags if t.label not in incoming_labels]
        if to_delete:
            _ = await self.repo.delete_by_ids(to_delete)

        # Insert new manual tags not already present
        new_tags = []
        try:
            for tag_input in request.tags:
                if tag_input.label not in existing_manual_labels:
                    new_tag = await self.repo.create(
                        customer_id=customer_id,
                        label=tag_input.label,
                        tone=tag_input.tone.value,
                        source="manual",
                    )
                    new_tags.append(new_tag)
                else:
                    # Keep existing tag (already in DB, not deleted)
                    pass
            await session.flush()
        except IntegrityError as e:
            await session.rollback()
            self.log_failed("save_tags", error=e)
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Tag label already exists for this customer (race condition)",
            ) from e

        # Build final list: system tags + surviving manual tags + new tags
        surviving_manual = [t for t in manual_tags if t.label in incoming_labels]
        all_tags = system_tags + surviving_manual + new_tags
        all_tags.sort(key=lambda t: t.created_at)

        result = CustomerTagsUpdateResponse(
            tags=[CustomerTagResponse.model_validate(t) for t in all_tags]
        )
        self.log_completed("save_tags", total=len(result.tags))
        return result

    @staticmethod
    def _validate_no_duplicates(tags: list[TagInput]) -> None:
        """Validate no duplicate labels in request.

        Args:
            tags: List of TagInput

        Raises:
            HTTPException 422: Duplicate labels found
        """
        labels = [t.label for t in tags]
        if len(labels) != len(set(labels)):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Duplicate tag labels are not allowed within a single request",
            )
