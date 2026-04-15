"""
Customer service for business logic operations.

This module provides the CustomerService class for all customer-related
business operations including CRUD, lookups, flag management, bulk operations,
duplicate detection, merge, and Stripe payment integration.

Validates: Requirement 1.1-1.6, 3.1-3.6, 4.1-4.7, 6.6, 8.1-8.4, 11.1-11.6, 12.1-12.5
CRM Gap Closure: 7.1, 7.2, 7.4, 8.4, 10.1, 10.2, 11.3, 56.1, 56.2, 56.3, 56.5, 56.6
"""

from __future__ import annotations

import csv
import io
from datetime import datetime
from typing import TYPE_CHECKING, Any

import stripe
from sqlalchemy import (
    func as sa_func,
    select,
    text,
    update as sa_update,
)

from grins_platform.exceptions import (
    BulkOperationError,
    CustomerNotFoundError,
    DuplicateCustomerError,
    MergeConflictError,
)
from grins_platform.log_config import LoggerMixin
from grins_platform.models.audit_log import AuditLog
from grins_platform.models.customer import Customer
from grins_platform.schemas.customer import (
    ChargeResponse,
    CustomerCreate,
    CustomerDetailResponse,
    CustomerFlagsUpdate,
    CustomerListParams,
    CustomerResponse,
    CustomerUpdate,
    DuplicateCustomerMatch,
    DuplicateGroup,
    PaginatedCustomerResponse,
    PaymentMethodResponse,
    ServiceHistorySummary,
    normalize_phone,
)
from grins_platform.services.stripe_config import StripeSettings

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession

    from grins_platform.repositories.customer_repository import CustomerRepository


# Maximum records allowed for bulk operations
MAX_BULK_RECORDS = 1000


class CustomerService(LoggerMixin):
    """Service for customer management operations.

    This class handles all business logic for customer operations including
    CRUD operations, lookups, flag management, and bulk operations.

    Attributes:
        repository: CustomerRepository for database operations

    Validates: Requirement 1.1-1.6, 8.1-8.4
    """

    DOMAIN = "customer"

    def __init__(self, repository: CustomerRepository) -> None:
        """Initialize service with repository.

        Args:
            repository: CustomerRepository for database operations
        """
        super().__init__()
        self.repository = repository

    # =========================================================================
    # Task 5.1: CRUD Operations
    # =========================================================================

    async def create_customer(self, data: CustomerCreate) -> CustomerResponse:
        """Create a new customer with duplicate check.

        Args:
            data: CustomerCreate schema with customer data

        Returns:
            CustomerResponse with created customer data

        Raises:
            DuplicateCustomerError: If phone number already exists

        Validates: Requirement 1.1, 6.6, 8.1-8.4
        """
        self.log_started("create_customer", phone=data.phone[-4:])

        # Check for duplicate phone number
        existing = await self.repository.find_by_phone(data.phone)
        if existing:
            self.log_rejected(
                "create_customer",
                reason="duplicate_phone",
                existing_id=str(existing.id),
            )
            raise DuplicateCustomerError(existing.id, data.phone)

        # Create customer via repository
        customer = await self.repository.create(
            first_name=data.first_name,
            last_name=data.last_name,
            phone=data.phone,
            email=data.email,
            lead_source=data.lead_source.value if data.lead_source else None,
            lead_source_details=data.lead_source_details,
            sms_opt_in=data.sms_opt_in,
            email_opt_in=data.email_opt_in,
        )

        self.log_completed("create_customer", customer_id=str(customer.id))
        response: CustomerResponse = CustomerResponse.model_validate(customer)
        return response

    async def get_customer(
        self,
        customer_id: UUID,
        include_properties: bool = True,
        include_service_history: bool = True,
    ) -> CustomerDetailResponse:
        """Get customer with properties and service history.

        Args:
            customer_id: UUID of the customer to retrieve
            include_properties: Whether to include properties (default True)
            include_service_history: Whether to include service history (default True)

        Returns:
            CustomerDetailResponse with customer, properties, and service history

        Raises:
            CustomerNotFoundError: If customer not found or is deleted

        Validates: Requirement 1.4, 8.1-8.4
        """
        self.log_started("get_customer", customer_id=str(customer_id))

        customer = await self.repository.get_by_id(customer_id)
        if not customer:
            self.log_rejected("get_customer", reason="not_found")
            raise CustomerNotFoundError(customer_id)

        # Get service history summary if requested
        service_summary: ServiceHistorySummary | None = None
        if include_service_history:
            service_summary = await self.repository.get_service_summary(customer_id)

        # Build response with properties from the loaded relationship
        response_data = {
            "id": customer.id,
            "first_name": customer.first_name,
            "last_name": customer.last_name,
            "phone": customer.phone,
            "email": customer.email,
            "status": customer.status,
            "is_priority": customer.is_priority,
            "is_red_flag": customer.is_red_flag,
            "is_slow_payer": customer.is_slow_payer,
            "is_new_customer": customer.is_new_customer,
            "sms_opt_in": customer.sms_opt_in,
            "email_opt_in": customer.email_opt_in,
            "lead_source": customer.lead_source,
            "internal_notes": customer.internal_notes,
            "preferred_service_times": customer.preferred_service_times,
            "created_at": customer.created_at,
            "updated_at": customer.updated_at,
            "properties": customer.properties if include_properties else [],
            "service_history_summary": service_summary,
        }

        self.log_completed(
            "get_customer",
            customer_id=str(customer_id),
            property_count=len(customer.properties) if include_properties else 0,
        )
        response: CustomerDetailResponse = CustomerDetailResponse.model_validate(
            response_data,
        )
        return response

    async def update_customer(
        self,
        customer_id: UUID,
        data: CustomerUpdate,
    ) -> CustomerResponse:
        """Update customer information with validation.

        Args:
            customer_id: UUID of the customer to update
            data: CustomerUpdate schema with fields to update

        Returns:
            CustomerResponse with updated customer data

        Raises:
            CustomerNotFoundError: If customer not found or is deleted
            DuplicateCustomerError: If new phone number already exists

        Validates: Requirement 1.5, 6.6, 8.1-8.4
        """
        self.log_started("update_customer", customer_id=str(customer_id))

        # Check customer exists
        customer = await self.repository.get_by_id(customer_id)
        if not customer:
            self.log_rejected("update_customer", reason="not_found")
            raise CustomerNotFoundError(customer_id)

        # Check phone uniqueness if changing
        if data.phone and data.phone != customer.phone:
            existing = await self.repository.find_by_phone(data.phone)
            if existing and existing.id != customer_id:
                self.log_rejected(
                    "update_customer",
                    reason="duplicate_phone",
                    existing_id=str(existing.id),
                )
                raise DuplicateCustomerError(existing.id, data.phone)

        # Build update data, excluding unset fields
        update_data = data.model_dump(exclude_unset=True)

        # Convert enum to string value if present
        if "status" in update_data and update_data["status"] is not None:
            update_data["status"] = update_data["status"].value
        if "lead_source" in update_data and update_data["lead_source"] is not None:
            update_data["lead_source"] = update_data["lead_source"].value

        updated = await self.repository.update(customer_id, update_data)
        if not updated:
            self.log_rejected("update_customer", reason="update_failed")
            raise CustomerNotFoundError(customer_id)

        self.log_completed("update_customer", customer_id=str(customer_id))
        response: CustomerResponse = CustomerResponse.model_validate(updated)
        return response

    async def delete_customer(self, customer_id: UUID) -> bool:
        """Soft delete a customer.

        Args:
            customer_id: UUID of the customer to delete

        Returns:
            True if customer was deleted

        Raises:
            CustomerNotFoundError: If customer not found

        Validates: Requirement 1.6, 6.8, 8.1-8.4
        """
        self.log_started("delete_customer", customer_id=str(customer_id))

        # Check customer exists first
        customer = await self.repository.get_by_id(customer_id)
        if not customer:
            self.log_rejected("delete_customer", reason="not_found")
            raise CustomerNotFoundError(customer_id)

        deleted = await self.repository.soft_delete(customer_id)
        if not deleted:
            self.log_rejected("delete_customer", reason="delete_failed")
            raise CustomerNotFoundError(customer_id)

        self.log_completed("delete_customer", customer_id=str(customer_id))
        return True

    # =========================================================================
    # Task 5.2: List and Lookup Methods
    # =========================================================================

    async def list_customers(
        self,
        params: CustomerListParams,
    ) -> PaginatedCustomerResponse:
        """List customers with filtering and pagination.

        Args:
            params: CustomerListParams with filter and pagination options

        Returns:
            PaginatedCustomerResponse with customers and pagination info

        Validates: Requirement 4.1-4.7, 8.1-8.4
        """
        self.log_started(
            "list_customers",
            page=params.page,
            page_size=params.page_size,
            filters={
                "city": params.city,
                "status": params.status.value if params.status else None,
                "search": params.search,
            },
        )

        customers, total = await self.repository.list_with_filters(params)

        # Calculate total pages
        total_pages = (total + params.page_size - 1) // params.page_size

        # Convert to response schemas
        customer_responses = [CustomerResponse.model_validate(c) for c in customers]

        self.log_completed(
            "list_customers",
            count=len(customers),
            total=total,
            total_pages=total_pages,
        )

        return PaginatedCustomerResponse(
            items=customer_responses,
            total=total,
            page=params.page,
            page_size=params.page_size,
            total_pages=total_pages,
        )

    async def lookup_by_phone(
        self,
        phone: str,
        partial_match: bool = False,
    ) -> list[CustomerResponse]:
        """Lookup customers by phone number.

        Args:
            phone: Phone number to search for
            partial_match: If True, search for partial matches

        Returns:
            List of matching CustomerResponse objects

        Validates: Requirement 11.1, 11.3-11.5, 8.1-8.4
        """
        # Log only last 4 digits for privacy
        phone_suffix = phone[-4:] if len(phone) >= 4 else phone
        self.log_started(
            "lookup_by_phone",
            phone=phone_suffix,
            partial_match=partial_match,
        )

        # Normalize phone number for search
        try:
            normalized = normalize_phone(phone)
        except ValueError:
            # For partial matches, just extract digits
            normalized = "".join(filter(str.isdigit, phone))

        if partial_match:
            customers = await self.repository.find_by_phone_partial(normalized)
        else:
            customer = await self.repository.find_by_phone(normalized)
            customers = [customer] if customer else []

        self.log_completed("lookup_by_phone", count=len(customers))
        return [CustomerResponse.model_validate(c) for c in customers]

    async def lookup_by_email(self, email: str) -> list[CustomerResponse]:
        """Lookup customers by email address (case-insensitive).

        Args:
            email: Email address to search for

        Returns:
            List of matching CustomerResponse objects

        Validates: Requirement 11.2, 11.3, 8.1-8.4
        """
        self.log_started("lookup_by_email", email=email)

        customers = await self.repository.find_by_email(email)

        self.log_completed("lookup_by_email", count=len(customers))
        return [CustomerResponse.model_validate(c) for c in customers]

    async def check_tier1_duplicates(
        self,
        phone: str | None = None,
        email: str | None = None,
        exclude_id: UUID | None = None,
    ) -> list[CustomerResponse]:
        """Tier 1 duplicate check: exact phone or email match.

        Args:
            phone: Phone number to check.
            email: Email address to check.
            exclude_id: Customer ID to exclude (for edit scenarios).

        Returns:
            List of matching customers.

        Validates: Requirement 6.13
        """
        self.log_started("check_tier1_duplicates")
        matches: dict[str, CustomerResponse] = {}

        if phone:
            try:
                normalized = normalize_phone(phone)
            except ValueError:
                normalized = "".join(filter(str.isdigit, phone))
            customer = await self.repository.find_by_phone(normalized)
            if customer and (not exclude_id or customer.id != exclude_id):
                matches[str(customer.id)] = CustomerResponse.model_validate(
                    customer,
                )

        if email and email.strip():
            customers = await self.repository.find_by_email(email)
            for c in customers:
                if not exclude_id or c.id != exclude_id:
                    matches[str(c.id)] = CustomerResponse.model_validate(c)

        result = list(matches.values())
        self.log_completed("check_tier1_duplicates", count=len(result))
        return result

    async def get_service_history(
        self,
        customer_id: UUID,
    ) -> ServiceHistorySummary:
        """Get service history summary for a customer.

        Args:
            customer_id: UUID of the customer

        Returns:
            ServiceHistorySummary with job count, last service date, and revenue

        Raises:
            CustomerNotFoundError: If customer not found

        Validates: Requirement 7.1-7.8, 8.1-8.4
        """
        self.log_started("get_service_history", customer_id=str(customer_id))

        # Check customer exists
        customer = await self.repository.get_by_id(customer_id)
        if not customer:
            self.log_rejected("get_service_history", reason="not_found")
            raise CustomerNotFoundError(customer_id)

        # Get service history summary from repository
        summary = await self.repository.get_service_summary(customer_id)

        self.log_completed(
            "get_service_history",
            customer_id=str(customer_id),
            total_jobs=summary.total_jobs if summary else 0,
        )

        # Return summary or default empty summary
        if summary:
            return summary
        return ServiceHistorySummary(
            total_jobs=0,
            last_service_date=None,
            total_revenue=0.0,
        )

    # =========================================================================
    # Task 5.3: Flag Management
    # =========================================================================

    async def update_flags(
        self,
        customer_id: UUID,
        flags: CustomerFlagsUpdate,
    ) -> CustomerResponse:
        """Update customer flags.

        Args:
            customer_id: UUID of the customer
            flags: CustomerFlagsUpdate with flag values to update

        Returns:
            CustomerResponse with updated customer data

        Raises:
            CustomerNotFoundError: If customer not found

        Validates: Requirement 3.1-3.6, 8.1-8.4
        """
        self.log_started("update_flags", customer_id=str(customer_id))

        # Check customer exists
        customer = await self.repository.get_by_id(customer_id)
        if not customer:
            self.log_rejected("update_flags", reason="not_found")
            raise CustomerNotFoundError(customer_id)

        # Build flags dict, excluding unset fields
        flags_data = flags.model_dump(exclude_unset=True)

        # Log flag changes for audit
        self._log_flag_changes(customer, flags_data)

        updated = await self.repository.update_flags(customer_id, flags_data)
        if not updated:
            self.log_rejected("update_flags", reason="update_failed")
            raise CustomerNotFoundError(customer_id)

        self.log_completed("update_flags", customer_id=str(customer_id))
        response: CustomerResponse = CustomerResponse.model_validate(updated)
        return response

    def _log_flag_changes(
        self,
        customer: Customer,
        new_flags: dict[str, Any],
    ) -> None:
        """Log individual flag changes for audit purposes.

        Args:
            customer: Current customer record
            new_flags: Dictionary of new flag values
        """
        for flag_name, new_value in new_flags.items():
            old_value = getattr(customer, flag_name, None)
            if old_value != new_value:
                self.logger.info(
                    "business.customerservice.flag_changed",
                    customer_id=str(customer.id),
                    flag=flag_name,
                    old_value=old_value,
                    new_value=new_value,
                )

    # =========================================================================
    # Task 5.4: Bulk Operations
    # =========================================================================

    async def bulk_update_preferences(
        self,
        customer_ids: list[UUID],
        sms_opt_in: bool | None = None,
        email_opt_in: bool | None = None,
    ) -> dict[str, Any]:
        """Bulk update communication preferences for multiple customers.

        Args:
            customer_ids: List of customer UUIDs to update
            sms_opt_in: New SMS opt-in status (None to skip)
            email_opt_in: New email opt-in status (None to skip)

        Returns:
            Dictionary with updated_count, failed_count, and errors

        Raises:
            BulkOperationError: If record count exceeds limit

        Validates: Requirement 12.3-12.5, 8.1-8.4
        """
        self.log_started("bulk_update_preferences", count=len(customer_ids))

        # Validate record count limit
        if len(customer_ids) > MAX_BULK_RECORDS:
            self.log_rejected(
                "bulk_update_preferences",
                reason="exceeds_limit",
                count=len(customer_ids),
                max_allowed=MAX_BULK_RECORDS,
            )
            msg = f"Bulk operation limited to {MAX_BULK_RECORDS} records"
            raise BulkOperationError(
                msg,
                record_count=len(customer_ids),
                max_allowed=MAX_BULK_RECORDS,
            )

        # Check if there's anything to update
        if sms_opt_in is None and email_opt_in is None:
            self.log_completed(
                "bulk_update_preferences",
                updated_count=0,
                message="no_changes_requested",
            )
            return {
                "updated_count": 0,
                "failed_count": 0,
                "errors": [],
            }

        updated_count, errors = await self.repository.bulk_update_preferences(
            customer_ids=customer_ids,
            sms_opt_in=sms_opt_in,
            email_opt_in=email_opt_in,
        )

        failed_count = len(customer_ids) - updated_count

        self.log_completed(
            "bulk_update_preferences",
            updated_count=updated_count,
            failed_count=failed_count,
        )

        return {
            "updated_count": updated_count,
            "failed_count": failed_count,
            "errors": errors,
        }

    async def export_customers_csv(
        self,
        city: str | None = None,
        limit: int = MAX_BULK_RECORDS,
    ) -> str:
        """Export customers to CSV format.

        Args:
            city: Optional city filter
            limit: Maximum records to export (default 1000)

        Returns:
            CSV string with customer data

        Raises:
            BulkOperationError: If limit exceeds maximum

        Validates: Requirement 12.1-12.2, 12.4, 8.1-8.4
        """
        self.log_started("export_customers_csv", city=city, limit=limit)

        # Validate limit
        if limit > MAX_BULK_RECORDS:
            self.log_rejected(
                "export_customers_csv",
                reason="exceeds_limit",
                limit=limit,
                max_allowed=MAX_BULK_RECORDS,
            )
            msg = f"Export limited to {MAX_BULK_RECORDS} records"
            raise BulkOperationError(
                msg,
                record_count=limit,
                max_allowed=MAX_BULK_RECORDS,
            )

        # Collect all customers using pagination (page_size max is 100)
        all_customers: list[Any] = []
        page = 1
        page_size = 100  # Max allowed by CustomerListParams

        while len(all_customers) < limit:
            params = CustomerListParams(
                page=page,
                page_size=min(page_size, limit - len(all_customers)),
                city=city,
                sort_by="last_name",
                sort_order="asc",
            )

            customers, total = await self.repository.list_with_filters(params)

            if not customers:
                break

            all_customers.extend(customers)
            page += 1

            # Stop if we've fetched all available records
            if len(all_customers) >= total:
                break

        # Generate CSV
        output = io.StringIO()
        writer = csv.writer(output)

        # Write header
        writer.writerow(
            [
                "id",
                "first_name",
                "last_name",
                "phone",
                "email",
                "status",
                "is_priority",
                "is_red_flag",
                "is_slow_payer",
                "is_new_customer",
                "sms_opt_in",
                "email_opt_in",
                "lead_source",
                "created_at",
            ],
        )

        # Write data rows
        for customer in all_customers:
            writer.writerow(
                [
                    str(customer.id),
                    customer.first_name,
                    customer.last_name,
                    customer.phone,
                    customer.email or "",
                    customer.status,
                    customer.is_priority,
                    customer.is_red_flag,
                    customer.is_slow_payer,
                    customer.is_new_customer,
                    customer.sms_opt_in,
                    customer.email_opt_in,
                    customer.lead_source or "",
                    customer.created_at.isoformat() if customer.created_at else "",
                ],
            )

        csv_content = output.getvalue()
        output.close()

        self.log_completed(
            "export_customers_csv",
            exported_count=len(all_customers),
        )

        return csv_content

    # =========================================================================
    # CRM Gap Closure: Duplicate Detection & Merge (Req 7)
    # =========================================================================

    async def find_duplicates(
        self,
        db: AsyncSession,
    ) -> list[DuplicateGroup]:
        """Find potential duplicate customers by phone, email, or similar name.

        Uses pg_trgm similarity() with threshold 0.7 for name matching,
        and exact match for phone/email.

        Args:
            db: Async database session

        Returns:
            List of DuplicateGroup, each containing 2+ potential duplicates

        Validates: CRM Gap Closure Req 7.1
        """
        self.log_started("find_duplicates")

        groups: list[DuplicateGroup] = []
        seen_ids: set[str] = set()

        # 1. Find duplicates by exact phone match
        phone_stmt = (
            select(Customer)
            .where(Customer.is_deleted == False)  # noqa: E712
            .order_by(Customer.phone, Customer.created_at)
        )
        result = await db.execute(phone_stmt)
        all_customers = list(result.scalars().all())

        phone_map: dict[str, list[Customer]] = {}
        for c in all_customers:
            phone_map.setdefault(c.phone, []).append(c)

        for customers in phone_map.values():
            if len(customers) >= 2:
                group_key = "|".join(
                    sorted(str(c.id) for c in customers),
                )
                if group_key not in seen_ids:
                    seen_ids.add(group_key)
                    groups.append(
                        DuplicateGroup(
                            customers=[
                                DuplicateCustomerMatch(
                                    id=c.id,
                                    first_name=c.first_name,
                                    last_name=c.last_name,
                                    phone=c.phone,
                                    email=c.email,
                                    match_type="phone",
                                    similarity_score=None,
                                )
                                for c in customers
                            ],
                        ),
                    )

        # 2. Find duplicates by exact email match
        email_map: dict[str, list[Customer]] = {}
        for c in all_customers:
            if c.email:
                key = c.email.lower()
                email_map.setdefault(key, []).append(c)

        for customers in email_map.values():
            if len(customers) >= 2:
                group_key = "|".join(
                    sorted(str(c.id) for c in customers),
                )
                if group_key not in seen_ids:
                    seen_ids.add(group_key)
                    groups.append(
                        DuplicateGroup(
                            customers=[
                                DuplicateCustomerMatch(
                                    id=c.id,
                                    first_name=c.first_name,
                                    last_name=c.last_name,
                                    phone=c.phone,
                                    email=c.email,
                                    match_type="email",
                                    similarity_score=None,
                                )
                                for c in customers
                            ],
                        ),
                    )

        # 3. Find duplicates by name similarity using pg_trgm

        name_sim_query = text("""
            SELECT c1.id AS id1, c2.id AS id2,
                   similarity(
                       c1.first_name || ' ' || c1.last_name,
                       c2.first_name || ' ' || c2.last_name
                   ) AS sim_score
            FROM customers c1
            JOIN customers c2 ON c1.id < c2.id
            WHERE c1.is_deleted = false
              AND c2.is_deleted = false
              AND similarity(
                  c1.first_name || ' ' || c1.last_name,
                  c2.first_name || ' ' || c2.last_name
              ) >= 0.7
        """)

        try:
            sim_result = await db.execute(name_sim_query)
            sim_rows = sim_result.fetchall()
        except Exception:
            # pg_trgm extension may not be available; skip name matching
            sim_rows = []

        # Build a lookup for customers by ID
        customer_by_id = {c.id: c for c in all_customers}

        for row in sim_rows:
            id1, id2, sim_score = row[0], row[1], float(row[2])
            c1 = customer_by_id.get(id1)
            c2 = customer_by_id.get(id2)
            if not c1 or not c2:
                continue

            group_key = "|".join(sorted([str(id1), str(id2)]))
            if group_key not in seen_ids:
                seen_ids.add(group_key)
                groups.append(
                    DuplicateGroup(
                        customers=[
                            DuplicateCustomerMatch(
                                id=c1.id,
                                first_name=c1.first_name,
                                last_name=c1.last_name,
                                phone=c1.phone,
                                email=c1.email,
                                match_type="name",
                                similarity_score=sim_score,
                            ),
                            DuplicateCustomerMatch(
                                id=c2.id,
                                first_name=c2.first_name,
                                last_name=c2.last_name,
                                phone=c2.phone,
                                email=c2.email,
                                match_type="name",
                                similarity_score=sim_score,
                            ),
                        ],
                    ),
                )

        self.log_completed("find_duplicates", group_count=len(groups))
        return groups

    async def merge_customers(
        self,
        db: AsyncSession,
        primary_id: UUID,
        duplicate_ids: list[UUID],
        actor_id: UUID,
        ip_address: str,
    ) -> CustomerResponse:
        """Merge duplicate customers into a primary customer.

        Single transaction: UPDATE all FK refs → soft-delete duplicates → AuditLog.

        Args:
            db: Async database session
            primary_id: UUID of the customer to keep
            duplicate_ids: UUIDs of customers to merge into primary
            actor_id: UUID of the staff performing the merge
            ip_address: IP address of the request

        Returns:
            CustomerResponse of the primary customer after merge

        Raises:
            CustomerNotFoundError: If primary or any duplicate not found
            MergeConflictError: If merge would create inconsistency

        Validates: CRM Gap Closure Req 7.2, 7.4
        """
        self.log_started(
            "merge_customers",
            primary_id=str(primary_id),
            duplicate_count=len(duplicate_ids),
        )

        # Validate primary customer exists
        primary = await self.repository.get_by_id(primary_id)
        if not primary:
            self.log_rejected("merge_customers", reason="primary_not_found")
            raise CustomerNotFoundError(primary_id)

        if primary_id in duplicate_ids:
            self.log_rejected(
                "merge_customers",
                reason="primary_in_duplicates",
            )
            msg = "Primary customer cannot be in the duplicate list"
            raise MergeConflictError(msg)

        # Validate all duplicates exist
        duplicates: list[Customer] = []
        for dup_id in duplicate_ids:
            dup = await self.repository.get_by_id(dup_id)
            if not dup:
                self.log_rejected(
                    "merge_customers",
                    reason="duplicate_not_found",
                    duplicate_id=str(dup_id),
                )
                raise CustomerNotFoundError(dup_id)
            duplicates.append(dup)

        # Tables with customer_id FK to reassign
        fk_tables: list[tuple[str, str]] = [
            ("jobs", "customer_id"),
            ("invoices", "customer_id"),
            ("properties", "customer_id"),
            ("communications", "customer_id"),
            ("customer_photos", "customer_id"),
            ("sent_messages", "customer_id"),
            ("estimates", "customer_id"),
            ("campaign_recipients", "customer_id"),
            ("leads", "customer_id"),
            ("service_agreements", "customer_id"),
            ("sms_consent_records", "customer_id"),
            ("disclosure_records", "customer_id"),
            ("email_suppression_list", "customer_id"),
        ]

        # Reassign all FK references from duplicates to primary
        for table_name, column_name in fk_tables:
            reassign_sql = text(
                f"UPDATE {table_name} "  # noqa: S608
                f"SET {column_name} = :primary_id "
                f"WHERE {column_name} = ANY(:dup_ids)",
            )
            try:
                await db.execute(
                    reassign_sql,
                    {
                        "primary_id": primary_id,
                        "dup_ids": duplicate_ids,
                    },
                )
            except Exception as exc:
                # Table may not exist yet; log and skip
                self.logger.debug(
                    "customer.customerservice.merge_skip_table",
                    table=table_name,
                    error=str(exc),
                )

        # Merge internal notes from duplicates into primary
        merged_notes_parts: list[str] = []
        if primary.internal_notes:
            merged_notes_parts.append(primary.internal_notes)
        merged_notes_parts.extend(
            f"[Merged from {dup.first_name} {dup.last_name} "
            f"({dup.id})]: {dup.internal_notes}"
            for dup in duplicates
            if dup.internal_notes
        )

        if merged_notes_parts:
            merged_notes = "\n\n".join(merged_notes_parts)
            await db.execute(
                sa_update(Customer)
                .where(Customer.id == primary_id)
                .values(internal_notes=merged_notes),
            )

        # Soft-delete duplicates
        for dup_id in duplicate_ids:
            await db.execute(
                sa_update(Customer)
                .where(Customer.id == dup_id)
                .values(
                    is_deleted=True,
                    deleted_at=datetime.now(),
                ),
            )

        # Create AuditLog entry
        audit_entry = AuditLog(
            actor_id=actor_id,
            actor_role="admin",
            action="customer.merge",
            resource_type="customer",
            resource_id=primary_id,
            details={
                "primary_customer_id": str(primary_id),
                "merged_customer_ids": [str(d) for d in duplicate_ids],
                "merged_customer_names": [
                    f"{d.first_name} {d.last_name}" for d in duplicates
                ],
            },
            ip_address=ip_address,
        )
        db.add(audit_entry)

        await db.flush()

        # Refresh and return primary
        await db.refresh(primary)
        self.log_completed(
            "merge_customers",
            primary_id=str(primary_id),
            merged_count=len(duplicate_ids),
        )
        return CustomerResponse.model_validate(primary)

    # =========================================================================
    # CRM Gap Closure: Internal Notes (Req 8)
    # =========================================================================

    async def update_internal_notes(
        self,
        customer_id: UUID,
        notes: str,
    ) -> CustomerResponse:
        """Update internal_notes field via PATCH.

        Args:
            customer_id: UUID of the customer
            notes: New internal notes content

        Returns:
            CustomerResponse with updated customer data

        Raises:
            CustomerNotFoundError: If customer not found

        Validates: CRM Gap Closure Req 8.4
        """
        self.log_started("update_internal_notes", customer_id=str(customer_id))

        customer = await self.repository.get_by_id(customer_id)
        if not customer:
            self.log_rejected("update_internal_notes", reason="not_found")
            raise CustomerNotFoundError(customer_id)

        updated = await self.repository.update(
            customer_id,
            {"internal_notes": notes},
        )
        if not updated:
            self.log_rejected("update_internal_notes", reason="update_failed")
            raise CustomerNotFoundError(customer_id)

        self.log_completed(
            "update_internal_notes",
            customer_id=str(customer_id),
        )
        return CustomerResponse.model_validate(updated)

    # =========================================================================
    # CRM Gap Closure: Preferred Service Times (Req 11)
    # =========================================================================

    async def update_preferred_service_times(
        self,
        customer_id: UUID,
        preferences: dict[str, Any],
    ) -> CustomerResponse:
        """Update preferred_service_times JSONB field.

        Args:
            customer_id: UUID of the customer
            preferences: Service time preferences dict

        Returns:
            CustomerResponse with updated customer data

        Raises:
            CustomerNotFoundError: If customer not found

        Validates: CRM Gap Closure Req 11.3
        """
        self.log_started(
            "update_preferred_service_times",
            customer_id=str(customer_id),
        )

        customer = await self.repository.get_by_id(customer_id)
        if not customer:
            self.log_rejected(
                "update_preferred_service_times",
                reason="not_found",
            )
            raise CustomerNotFoundError(customer_id)

        updated = await self.repository.update(
            customer_id,
            {"preferred_service_times": preferences},
        )
        if not updated:
            self.log_rejected(
                "update_preferred_service_times",
                reason="update_failed",
            )
            raise CustomerNotFoundError(customer_id)

        self.log_completed(
            "update_preferred_service_times",
            customer_id=str(customer_id),
        )
        return CustomerResponse.model_validate(updated)

    # =========================================================================
    # CRM2: Service Preferences CRUD (Req 7.1-7.6)
    # =========================================================================

    @staticmethod
    def _normalize_prefs(
        raw: dict[str, Any] | list[dict[str, Any]] | None,
    ) -> list[dict[str, Any]]:
        """Normalize preferred_service_times to a list.

        Handles legacy single-dict format and new list format.
        """
        if not raw:
            return []
        if isinstance(raw, list):
            return raw  # type: ignore[return-value]
        # dict case (legacy single-preference format)
        return [raw]

    async def get_service_preferences(
        self,
        customer_id: UUID,
    ) -> list[dict[str, Any]]:
        """Get all service preferences for a customer.

        Validates: CRM2 Req 7.5
        """
        self.log_started("get_service_preferences", customer_id=str(customer_id))
        customer = await self.repository.get_by_id(customer_id)
        if not customer:
            raise CustomerNotFoundError(customer_id)
        prefs = self._normalize_prefs(customer.preferred_service_times)
        self.log_completed("get_service_preferences", customer_id=str(customer_id))
        return prefs

    async def add_service_preference(
        self,
        customer_id: UUID,
        preference: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Add a service preference entry.

        Validates: CRM2 Req 7.1, 7.6
        """
        import uuid as _uuid  # noqa: PLC0415

        self.log_started("add_service_preference", customer_id=str(customer_id))
        customer = await self.repository.get_by_id(customer_id)
        if not customer:
            raise CustomerNotFoundError(customer_id)

        prefs = self._normalize_prefs(customer.preferred_service_times)
        entry = {"id": str(_uuid.uuid4()), **preference}
        prefs.append(entry)

        await self.repository.update(customer_id, {"preferred_service_times": prefs})
        self.log_completed("add_service_preference", customer_id=str(customer_id))
        return prefs

    async def update_service_preference(
        self,
        customer_id: UUID,
        preference_id: str,
        preference: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Update a service preference entry by id.

        Validates: CRM2 Req 7.5
        """
        self.log_started(
            "update_service_preference",
            customer_id=str(customer_id),
            preference_id=preference_id,
        )
        customer = await self.repository.get_by_id(customer_id)
        if not customer:
            raise CustomerNotFoundError(customer_id)

        prefs = self._normalize_prefs(customer.preferred_service_times)

        found = False
        for i, p in enumerate(prefs):
            if p.get("id") == preference_id:
                prefs[i] = {"id": preference_id, **preference}
                found = True
                break

        if not found:
            self.log_rejected("update_service_preference", reason="not_found")
            msg = f"Service preference {preference_id} not found"
            raise ValueError(msg)

        await self.repository.update(customer_id, {"preferred_service_times": prefs})
        self.log_completed("update_service_preference", customer_id=str(customer_id))
        return prefs

    async def delete_service_preference(
        self,
        customer_id: UUID,
        preference_id: str,
    ) -> list[dict[str, Any]]:
        """Delete a service preference entry by id.

        Validates: CRM2 Req 7.5
        """
        self.log_started(
            "delete_service_preference",
            customer_id=str(customer_id),
            preference_id=preference_id,
        )
        customer = await self.repository.get_by_id(customer_id)
        if not customer:
            raise CustomerNotFoundError(customer_id)

        prefs = self._normalize_prefs(customer.preferred_service_times)
        original_len = len(prefs)
        prefs = [p for p in prefs if p.get("id") != preference_id]

        if len(prefs) == original_len:
            self.log_rejected("delete_service_preference", reason="not_found")
            msg = f"Service preference {preference_id} not found"
            raise ValueError(msg)

        await self.repository.update(customer_id, {"preferred_service_times": prefs})
        self.log_completed("delete_service_preference", customer_id=str(customer_id))
        return prefs

    # =========================================================================
    # CRM Gap Closure: Customer Invoice History (Req 10)
    # =========================================================================

    async def get_customer_invoices(
        self,
        db: AsyncSession,
        customer_id: UUID,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        """Get paginated invoice history for a customer, sorted by date desc.

        Args:
            db: Async database session
            customer_id: UUID of the customer
            page: Page number (1-indexed)
            page_size: Number of items per page

        Returns:
            Dict with items, total, page, page_size, total_pages

        Raises:
            CustomerNotFoundError: If customer not found

        Validates: CRM Gap Closure Req 10.1, 10.2
        """
        from grins_platform.models.invoice import Invoice  # noqa: PLC0415
        from grins_platform.schemas.invoice import InvoiceResponse  # noqa: PLC0415

        self.log_started(
            "get_customer_invoices",
            customer_id=str(customer_id),
            page=page,
            page_size=page_size,
        )

        # Verify customer exists
        customer = await self.repository.get_by_id(customer_id)
        if not customer:
            self.log_rejected("get_customer_invoices", reason="not_found")
            raise CustomerNotFoundError(customer_id)

        # Count total invoices
        count_stmt = (
            select(sa_func.count())
            .select_from(Invoice)
            .where(Invoice.customer_id == customer_id)
        )
        count_result = await db.execute(count_stmt)
        total = count_result.scalar() or 0

        # Fetch paginated invoices sorted by date desc
        offset = (page - 1) * page_size
        invoices_stmt = (
            select(Invoice)
            .where(Invoice.customer_id == customer_id)
            .order_by(Invoice.invoice_date.desc(), Invoice.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        result = await db.execute(invoices_stmt)
        invoices = list(result.scalars().all())

        total_pages = (total + page_size - 1) // page_size if total > 0 else 0

        self.log_completed(
            "get_customer_invoices",
            customer_id=str(customer_id),
            count=len(invoices),
            total=total,
        )

        return {
            "items": [InvoiceResponse.model_validate(inv) for inv in invoices],
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
        }

    # =========================================================================
    # CRM Gap Closure: Stripe Payment Methods (Req 56)
    # =========================================================================

    async def get_payment_methods(
        self,
        db: AsyncSession,  # noqa: ARG002
        customer_id: UUID,
    ) -> list[PaymentMethodResponse]:
        """List Stripe saved payment methods via stripe_customer_id.

        Read-only from the agreement flow — does not create or modify
        payment methods.

        Args:
            db: Async database session
            customer_id: UUID of the customer

        Returns:
            List of PaymentMethodResponse

        Raises:
            CustomerNotFoundError: If customer not found

        Validates: CRM Gap Closure Req 56.1, 56.2
        """
        self.log_started(
            "get_payment_methods",
            customer_id=str(customer_id),
        )

        customer = await self.repository.get_by_id(customer_id)
        if not customer:
            self.log_rejected("get_payment_methods", reason="not_found")
            raise CustomerNotFoundError(customer_id)

        if not customer.stripe_customer_id:
            self.log_completed(
                "get_payment_methods",
                customer_id=str(customer_id),
                count=0,
                reason="no_stripe_customer",
            )
            return []

        settings = StripeSettings()
        if not settings.is_configured:
            self.log_rejected(
                "get_payment_methods",
                reason="stripe_not_configured",
            )
            return []

        stripe.api_key = settings.stripe_secret_key

        try:
            payment_methods = stripe.PaymentMethod.list(
                customer=customer.stripe_customer_id,
                type="card",
            )
        except stripe.StripeError as e:
            self.log_failed("get_payment_methods", error=e)
            return []

        # Determine default payment method
        default_pm_id: str | None = None
        try:
            stripe_customer = stripe.Customer.retrieve(
                customer.stripe_customer_id,
            )
            default_source = stripe_customer.get(
                "invoice_settings",
                {},
            )
            if isinstance(default_source, dict):
                default_pm_id = default_source.get(
                    "default_payment_method",
                )
        except stripe.StripeError as exc:
            self.logger.debug(
                "customer.customerservice.default_pm_lookup_failed",
                error=str(exc),
            )

        methods: list[PaymentMethodResponse] = []
        for pm in payment_methods.data:
            card = pm.get("card", {})
            if not isinstance(card, dict):
                continue
            methods.append(
                PaymentMethodResponse(
                    id=pm["id"],
                    brand=card.get("brand", "unknown"),
                    last4=card.get("last4", "????"),
                    exp_month=card.get("exp_month", 0),
                    exp_year=card.get("exp_year", 0),
                    is_default=pm["id"] == default_pm_id if default_pm_id else False,
                ),
            )

        self.log_completed(
            "get_payment_methods",
            customer_id=str(customer_id),
            count=len(methods),
        )
        return methods

    async def charge_customer(
        self,
        db: AsyncSession,  # noqa: ARG002
        customer_id: UUID,
        amount: int,
        description: str,
        invoice_id: UUID | None = None,
    ) -> ChargeResponse:
        """Create Stripe PaymentIntent using default payment method on file.

        Args:
            db: Async database session
            customer_id: UUID of the customer
            amount: Amount in cents to charge
            description: Charge description
            invoice_id: Optional invoice ID to associate

        Returns:
            ChargeResponse with payment intent details

        Raises:
            CustomerNotFoundError: If customer not found
            MergeConflictError: If no Stripe customer or payment method

        Validates: CRM Gap Closure Req 56.3, 56.5, 56.6
        """
        self.log_started(
            "charge_customer",
            customer_id=str(customer_id),
            amount=amount,
        )

        customer = await self.repository.get_by_id(customer_id)
        if not customer:
            self.log_rejected("charge_customer", reason="not_found")
            raise CustomerNotFoundError(customer_id)

        if not customer.stripe_customer_id:
            self.log_rejected(
                "charge_customer",
                reason="no_stripe_customer",
            )
            msg = (
                "Customer has no Stripe account. "
                "Payment methods are set up via the service agreement flow."
            )
            raise MergeConflictError(msg)

        settings = StripeSettings()
        if not settings.is_configured:
            self.log_rejected(
                "charge_customer",
                reason="stripe_not_configured",
            )
            msg = "Stripe is not configured"
            raise MergeConflictError(msg)

        stripe.api_key = settings.stripe_secret_key

        # Get default payment method
        try:
            stripe_customer = stripe.Customer.retrieve(
                customer.stripe_customer_id,
            )
            invoice_settings = stripe_customer.get(
                "invoice_settings",
                {},
            )
            default_pm_id: str | None = None
            if isinstance(invoice_settings, dict):
                default_pm_id = invoice_settings.get(
                    "default_payment_method",
                )
        except stripe.StripeError as e:
            self.log_failed("charge_customer", error=e)
            msg = f"Failed to retrieve Stripe customer: {e}"
            raise MergeConflictError(msg) from e

        if not default_pm_id:
            self.log_rejected(
                "charge_customer",
                reason="no_default_payment_method",
            )
            msg = "Customer has no default payment method on file"
            raise MergeConflictError(msg)

        # Create PaymentIntent
        metadata: dict[str, str] = {
            "customer_id": str(customer_id),
        }
        if invoice_id:
            metadata["invoice_id"] = str(invoice_id)

        try:
            intent = stripe.PaymentIntent.create(
                amount=amount,
                currency="usd",
                customer=customer.stripe_customer_id,
                payment_method=default_pm_id,
                off_session=True,
                confirm=True,
                description=description,
                metadata=metadata,
            )
        except stripe.StripeError as e:
            self.log_failed(
                "charge_customer",
                error=e,
                customer_id=str(customer_id),
                amount=amount,
            )
            msg = f"Payment failed: {e}"
            raise MergeConflictError(msg) from e

        self.log_completed(
            "charge_customer",
            customer_id=str(customer_id),
            payment_intent_id=intent["id"],
            status=intent["status"],
            amount=amount,
        )

        return ChargeResponse(
            payment_intent_id=intent["id"],
            status=intent["status"],
            amount=amount,
            currency="usd",
        )
