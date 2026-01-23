"""
Customer repository for database operations.

This module provides the CustomerRepository class for all customer-related
database operations using SQLAlchemy 2.0 async patterns.

Validates: Requirement 1.1, 1.4, 1.5, 1.6, 3.4, 4.1-4.7, 7.2, 11.1-11.4
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import func, or_, select, update
from sqlalchemy.orm import selectinload

from grins_platform.log_config import LoggerMixin
from grins_platform.models.customer import Customer
from grins_platform.models.property import Property
from grins_platform.schemas.customer import CustomerListParams, ServiceHistorySummary

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession


class CustomerRepository(LoggerMixin):
    """Repository for customer database operations.

    This class handles all database operations for customers including
    CRUD operations, queries, and flag management.

    Attributes:
        session: AsyncSession for database operations

    Validates: Requirement 1.1, 1.4, 1.5, 1.6
    """

    DOMAIN = "database"

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository with database session.

        Args:
            session: AsyncSession for database operations
        """
        super().__init__()
        self.session = session

    async def create(
        self,
        first_name: str,
        last_name: str,
        phone: str,
        email: str | None = None,
        lead_source: str | None = None,
        lead_source_details: dict[str, Any] | None = None,
        sms_opt_in: bool = False,
        email_opt_in: bool = False,
    ) -> Customer:
        """Create a new customer record.

        Args:
            first_name: Customer's first name
            last_name: Customer's last name
            phone: Customer's phone number (normalized)
            email: Customer's email address (optional)
            lead_source: How the customer found the business
            lead_source_details: Additional lead source information
            sms_opt_in: SMS communication opt-in status
            email_opt_in: Email communication opt-in status

        Returns:
            Created Customer instance

        Validates: Requirement 1.1
        """
        self.log_started("create", phone=phone[-4:])

        customer = Customer(
            first_name=first_name,
            last_name=last_name,
            phone=phone,
            email=email,
            lead_source=lead_source,
            lead_source_details=lead_source_details,
            sms_opt_in=sms_opt_in,
            email_opt_in=email_opt_in,
        )

        self.session.add(customer)
        await self.session.flush()
        await self.session.refresh(customer)

        self.log_completed("create", customer_id=str(customer.id))
        return customer

    async def get_by_id(
        self,
        customer_id: UUID,
        include_deleted: bool = False,
    ) -> Customer | None:
        """Get a customer by ID.

        Args:
            customer_id: UUID of the customer
            include_deleted: Whether to include soft-deleted customers

        Returns:
            Customer instance or None if not found

        Validates: Requirement 1.4
        """
        self.log_started("get_by_id", customer_id=str(customer_id))

        stmt = (
            select(Customer)
            .options(selectinload(Customer.properties))
            .where(Customer.id == customer_id)
        )

        if not include_deleted:
            stmt = stmt.where(Customer.is_deleted == False)  # noqa: E712

        result = await self.session.execute(stmt)
        customer: Customer | None = result.scalar_one_or_none()

        if customer:
            self.log_completed("get_by_id", customer_id=str(customer_id))
        else:
            self.log_completed("get_by_id", customer_id=str(customer_id), found=False)

        return customer

    async def update(
        self,
        customer_id: UUID,
        data: dict[str, Any],
    ) -> Customer | None:
        """Update a customer record.

        Args:
            customer_id: UUID of the customer to update
            data: Dictionary of fields to update

        Returns:
            Updated Customer instance or None if not found

        Validates: Requirement 1.5
        """
        self.log_started("update", customer_id=str(customer_id))

        # Remove None values and empty dict
        update_data = {k: v for k, v in data.items() if v is not None}

        if not update_data:
            # No updates to make, just return the customer
            return await self.get_by_id(customer_id)

        # Handle communication preferences timestamp
        if "sms_opt_in" in update_data or "email_opt_in" in update_data:
            update_data["communication_preferences_updated_at"] = datetime.now()

        # Update timestamp
        update_data["updated_at"] = datetime.now()

        stmt = (
            update(Customer)
            .where(Customer.id == customer_id)
            .where(Customer.is_deleted == False)  # noqa: E712
            .values(**update_data)
            .returning(Customer)
        )

        result = await self.session.execute(stmt)
        await self.session.flush()

        customer: Customer | None = result.scalar_one_or_none()

        if customer:
            # Refresh to get relationships
            await self.session.refresh(customer, ["properties"])
            self.log_completed("update", customer_id=str(customer_id))
        else:
            self.log_completed("update", customer_id=str(customer_id), found=False)

        return customer

    async def soft_delete(self, customer_id: UUID) -> bool:
        """Soft delete a customer.

        Args:
            customer_id: UUID of the customer to delete

        Returns:
            True if customer was deleted, False if not found

        Validates: Requirement 1.6
        """
        self.log_started("soft_delete", customer_id=str(customer_id))

        stmt = (
            update(Customer)
            .where(Customer.id == customer_id)
            .where(Customer.is_deleted == False)  # noqa: E712
            .values(
                is_deleted=True,
                deleted_at=datetime.now(),
                updated_at=datetime.now(),
            )
        )

        result = await self.session.execute(stmt)
        await self.session.flush()

        # rowcount is available on CursorResult but pyright doesn't recognize it
        rowcount: int = getattr(result, "rowcount", 0) or 0
        deleted: bool = rowcount > 0

        if deleted:
            self.log_completed("soft_delete", customer_id=str(customer_id))
        else:
            self.log_completed(
                "soft_delete",
                customer_id=str(customer_id),
                found=False,
            )

        return deleted

    async def find_by_phone(self, phone: str) -> Customer | None:
        """Find a customer by exact phone number.

        Args:
            phone: Normalized phone number (10 digits)

        Returns:
            Customer instance or None if not found

        Validates: Requirement 11.1
        """
        self.log_started("find_by_phone", phone=phone[-4:])

        stmt = (
            select(Customer)
            .options(selectinload(Customer.properties))
            .where(Customer.phone == phone)
            .where(Customer.is_deleted == False)  # noqa: E712
        )

        result = await self.session.execute(stmt)
        customer: Customer | None = result.scalar_one_or_none()

        self.log_completed("find_by_phone", found=customer is not None)
        return customer

    async def find_by_phone_partial(self, phone_partial: str) -> list[Customer]:
        """Find customers by partial phone number match.

        Args:
            phone_partial: Partial phone number to search for

        Returns:
            List of matching Customer instances

        Validates: Requirement 11.4
        """
        self.log_started("find_by_phone_partial", phone_partial=phone_partial[-4:])

        # Search for phone numbers containing the partial match
        stmt = (
            select(Customer)
            .options(selectinload(Customer.properties))
            .where(Customer.phone.contains(phone_partial))
            .where(Customer.is_deleted == False)  # noqa: E712
            .order_by(Customer.last_name, Customer.first_name)
        )

        result = await self.session.execute(stmt)
        customers = list(result.scalars().all())

        self.log_completed("find_by_phone_partial", count=len(customers))
        return customers

    async def find_by_email(self, email: str) -> list[Customer]:
        """Find customers by email address (case-insensitive).

        Args:
            email: Email address to search for

        Returns:
            List of matching Customer instances

        Validates: Requirement 11.2
        """
        self.log_started("find_by_email", email=email)

        stmt = (
            select(Customer)
            .options(selectinload(Customer.properties))
            .where(func.lower(Customer.email) == func.lower(email))
            .where(Customer.is_deleted == False)  # noqa: E712
            .order_by(Customer.last_name, Customer.first_name)
        )

        result = await self.session.execute(stmt)
        customers = list(result.scalars().all())

        self.log_completed("find_by_email", count=len(customers))
        return customers

    async def list_with_filters(
        self,
        params: CustomerListParams,
    ) -> tuple[list[Customer], int]:
        """List customers with filtering and pagination.

        Args:
            params: Query parameters for filtering and pagination

        Returns:
            Tuple of (list of customers, total count)

        Validates: Requirement 4.1-4.7
        """
        self.log_started(
            "list_with_filters",
            page=params.page,
            page_size=params.page_size,
        )

        # Base query
        base_query = select(Customer).where(Customer.is_deleted == False)  # noqa: E712

        # Apply filters
        if params.status:
            base_query = base_query.where(Customer.status == params.status.value)

        if params.is_priority is not None:
            base_query = base_query.where(Customer.is_priority == params.is_priority)

        if params.is_red_flag is not None:
            base_query = base_query.where(Customer.is_red_flag == params.is_red_flag)

        if params.is_slow_payer is not None:
            base_query = base_query.where(
                Customer.is_slow_payer == params.is_slow_payer,
            )

        # Search by name or email (case-insensitive)
        if params.search:
            search_term = f"%{params.search}%"
            base_query = base_query.where(
                or_(
                    func.lower(Customer.first_name).like(func.lower(search_term)),
                    func.lower(Customer.last_name).like(func.lower(search_term)),
                    func.lower(Customer.email).like(func.lower(search_term)),
                ),
            )

        # Filter by city (customers with properties in that city)
        if params.city:
            base_query = base_query.where(
                Customer.id.in_(
                    select(Property.customer_id)
                    .where(func.lower(Property.city) == func.lower(params.city))
                    .distinct(),
                ),
            )

        # Get total count
        count_query = select(func.count()).select_from(base_query.subquery())
        total_result = await self.session.execute(count_query)
        total = total_result.scalar() or 0

        # Apply sorting
        sort_column = getattr(Customer, params.sort_by, Customer.last_name)
        if params.sort_order == "desc":
            sort_column = sort_column.desc()
        else:
            sort_column = sort_column.asc()

        # Apply pagination
        offset = (params.page - 1) * params.page_size
        paginated_query = (
            base_query.options(selectinload(Customer.properties))
            .order_by(sort_column)
            .offset(offset)
            .limit(params.page_size)
        )

        result = await self.session.execute(paginated_query)
        customers = list(result.scalars().all())

        self.log_completed(
            "list_with_filters",
            count=len(customers),
            total=total,
        )
        return customers, total

    async def update_flags(
        self,
        customer_id: UUID,
        flags: dict[str, Any],
    ) -> Customer | None:
        """Update customer flags.

        Args:
            customer_id: UUID of the customer
            flags: Dictionary of flag names and values

        Returns:
            Updated Customer instance or None if not found

        Validates: Requirement 3.4
        """
        self.log_started("update_flags", customer_id=str(customer_id))

        # Filter out None values
        update_data: dict[str, Any] = {k: v for k, v in flags.items() if v is not None}

        if not update_data:
            return await self.get_by_id(customer_id)

        update_data["updated_at"] = datetime.now()

        stmt = (
            update(Customer)
            .where(Customer.id == customer_id)
            .where(Customer.is_deleted == False)  # noqa: E712
            .values(**update_data)
            .returning(Customer)
        )

        result = await self.session.execute(stmt)
        await self.session.flush()

        customer: Customer | None = result.scalar_one_or_none()

        if customer:
            await self.session.refresh(customer, ["properties"])
            self.log_completed("update_flags", customer_id=str(customer_id))
        else:
            self.log_completed(
                "update_flags",
                customer_id=str(customer_id),
                found=False,
            )

        return customer

    async def get_service_summary(self, customer_id: UUID) -> ServiceHistorySummary:
        """Get service history summary for a customer.

        Note: This is a placeholder implementation. Full implementation
        requires the service_history table which will be added in a future task.

        Args:
            customer_id: UUID of the customer

        Returns:
            ServiceHistorySummary with aggregated data

        Validates: Requirement 7.2
        """
        self.log_started("get_service_summary", customer_id=str(customer_id))

        # Placeholder implementation - returns empty summary
        # Full implementation requires service_history table
        summary = ServiceHistorySummary(
            total_jobs=0,
            last_service_date=None,
            total_revenue=0.0,
        )

        self.log_completed("get_service_summary", customer_id=str(customer_id))
        return summary

    async def bulk_update_preferences(
        self,
        customer_ids: list[UUID],
        sms_opt_in: bool | None = None,
        email_opt_in: bool | None = None,
    ) -> tuple[int, list[dict[str, Any]]]:
        """Bulk update communication preferences for multiple customers.

        Args:
            customer_ids: List of customer UUIDs to update
            sms_opt_in: New SMS opt-in status (None to skip)
            email_opt_in: New email opt-in status (None to skip)

        Returns:
            Tuple of (updated count, list of errors)

        Validates: Requirement 12.3
        """
        self.log_started("bulk_update_preferences", count=len(customer_ids))

        update_data: dict[str, Any] = {
            "updated_at": datetime.now(),
            "communication_preferences_updated_at": datetime.now(),
        }

        if sms_opt_in is not None:
            update_data["sms_opt_in"] = sms_opt_in
        if email_opt_in is not None:
            update_data["email_opt_in"] = email_opt_in

        if len(update_data) == 2:  # Only timestamps, no actual updates
            return 0, []

        stmt = (
            update(Customer)
            .where(Customer.id.in_(customer_ids))
            .where(Customer.is_deleted == False)  # noqa: E712
            .values(**update_data)
        )

        result = await self.session.execute(stmt)
        await self.session.flush()

        # rowcount is available on CursorResult but pyright doesn't recognize it
        updated_count: int = getattr(result, "rowcount", 0) or 0
        errors: list[dict[str, Any]] = []

        self.log_completed("bulk_update_preferences", updated_count=updated_count)
        return updated_count, errors

    async def count_all(self) -> int:
        """Count all customers (excluding deleted).

        Returns:
            Total count of non-deleted customers

        Validates: Admin Dashboard Requirement 1.6
        """
        self.log_started("count_all")

        stmt = (
            select(func.count())
            .select_from(Customer)
            .where(Customer.is_deleted == False)  # noqa: E712
        )

        result = await self.session.execute(stmt)
        count = result.scalar() or 0

        self.log_completed("count_all", count=count)
        return count

    async def count_active(self) -> int:
        """Count active customers (non-deleted with recent activity).

        For now, this counts all non-deleted customers.
        Future: Could filter by last_activity_date or similar.

        Returns:
            Count of active customers

        Validates: Admin Dashboard Requirement 1.6
        """
        self.log_started("count_active")

        # For now, active = not deleted
        # Future enhancement: filter by recent activity
        stmt = (
            select(func.count())
            .select_from(Customer)
            .where(Customer.is_deleted == False)  # noqa: E712
        )

        result = await self.session.execute(stmt)
        count = result.scalar() or 0

        self.log_completed("count_active", count=count)
        return count
