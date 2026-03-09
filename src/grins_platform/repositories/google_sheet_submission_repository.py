"""Repository for Google Sheet submission database operations."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from sqlalchemy import delete, func, or_, select, update

from grins_platform.log_config import LoggerMixin
from grins_platform.models.google_sheet_submission import GoogleSheetSubmission

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession

    from grins_platform.schemas.google_sheet_submission import SubmissionListParams


class GoogleSheetSubmissionRepository(LoggerMixin):
    """Repository for Google Sheet submission database operations."""

    DOMAIN = "database"

    def __init__(self, session: AsyncSession) -> None:
        super().__init__()
        self.session = session

    async def create(self, **kwargs: Any) -> GoogleSheetSubmission:
        """Create a new submission record."""
        self.log_started("create")
        submission = GoogleSheetSubmission(**kwargs)
        self.session.add(submission)
        await self.session.flush()
        await self.session.refresh(submission)
        self.log_completed("create", submission_id=str(submission.id))
        return submission

    async def get_by_id(self, submission_id: UUID) -> GoogleSheetSubmission | None:
        """Get a submission by UUID."""
        self.log_started("get_by_id", submission_id=str(submission_id))
        stmt = select(GoogleSheetSubmission).where(
            GoogleSheetSubmission.id == submission_id,
        )
        result = await self.session.execute(stmt)
        submission: GoogleSheetSubmission | None = result.scalar_one_or_none()
        self.log_completed(
            "get_by_id",
            submission_id=str(submission_id),
            found=submission is not None,
        )
        return submission

    async def delete_all(self) -> int:
        """Delete all submission records. Returns the number deleted."""
        self.log_started("delete_all")
        stmt = delete(GoogleSheetSubmission)
        result = await self.session.execute(stmt)
        count = result.rowcount
        await self.session.flush()
        self.log_completed("delete_all", deleted=count)
        return count

    async def get_max_row_number(self) -> int:
        """Get the highest sheet_row_number, or 0 if no rows exist."""
        self.log_started("get_max_row_number")
        max_expr = func.max(GoogleSheetSubmission.sheet_row_number)
        stmt = select(func.coalesce(max_expr, 0))
        result = await self.session.execute(stmt)
        max_row: int = result.scalar() or 0
        self.log_completed("get_max_row_number", max_row=max_row)
        return max_row

    async def list_with_filters(
        self,
        params: SubmissionListParams,
    ) -> tuple[list[GoogleSheetSubmission], int]:
        """List submissions with filtering, search, and pagination."""
        self.log_started(
            "list_with_filters",
            page=params.page,
            page_size=params.page_size,
        )

        base_query = select(GoogleSheetSubmission)

        if params.processing_status is not None:
            base_query = base_query.where(
                GoogleSheetSubmission.processing_status == params.processing_status,
            )

        if params.client_type is not None:
            base_query = base_query.where(
                GoogleSheetSubmission.client_type == params.client_type,
            )

        if params.search:
            search_term = f"%{params.search}%"
            base_query = base_query.where(
                or_(
                    func.lower(GoogleSheetSubmission.name).like(
                        func.lower(search_term),
                    ),
                    GoogleSheetSubmission.phone.like(search_term),
                    func.lower(GoogleSheetSubmission.email).like(
                        func.lower(search_term),
                    ),
                ),
            )

        count_query = select(func.count()).select_from(base_query.subquery())
        total_result = await self.session.execute(count_query)
        total = total_result.scalar() or 0

        sort_column = getattr(
            GoogleSheetSubmission,
            params.sort_by,
            GoogleSheetSubmission.imported_at,
        )
        if params.sort_order == "desc":
            sort_column = sort_column.desc()
        else:
            sort_column = sort_column.asc()

        offset = (params.page - 1) * params.page_size
        paginated_query = (
            base_query.order_by(sort_column).offset(offset).limit(params.page_size)
        )

        result = await self.session.execute(paginated_query)
        submissions = list(result.scalars().all())

        self.log_completed(
            "list_with_filters",
            count=len(submissions),
            total=total,
        )
        return submissions, total

    async def update(
        self,
        submission_id: UUID,
        update_data: dict[str, Any],
    ) -> GoogleSheetSubmission | None:
        """Update submission fields and return updated submission."""
        self.log_started("update", submission_id=str(submission_id))

        update_data["updated_at"] = datetime.now(tz=timezone.utc)

        stmt = (
            update(GoogleSheetSubmission)
            .where(GoogleSheetSubmission.id == submission_id)
            .values(**update_data)
            .returning(GoogleSheetSubmission)
        )

        result = await self.session.execute(stmt)
        await self.session.flush()

        submission: GoogleSheetSubmission | None = result.scalar_one_or_none()

        if submission:
            await self.session.refresh(submission)
            self.log_completed("update", submission_id=str(submission_id))
        else:
            self.log_completed(
                "update",
                submission_id=str(submission_id),
                found=False,
            )

        return submission
