"""
Customer service for business logic operations.

This module provides the CustomerService class for all customer-related
business operations including CRUD, lookups, flag management, and bulk operations.

Validates: Requirement 1.1-1.6, 3.1-3.6, 4.1-4.7, 6.6, 8.1-8.4, 11.1-11.6, 12.1-12.5
"""

from __future__ import annotations

import csv
import io
from typing import TYPE_CHECKING, Any

from grins_platform.exceptions import (
    BulkOperationError,
    CustomerNotFoundError,
    DuplicateCustomerError,
)
from grins_platform.log_config import LoggerMixin
from grins_platform.schemas.customer import (
    CustomerCreate,
    CustomerDetailResponse,
    CustomerFlagsUpdate,
    CustomerListParams,
    CustomerResponse,
    CustomerUpdate,
    PaginatedCustomerResponse,
    ServiceHistorySummary,
    normalize_phone,
)

if TYPE_CHECKING:
    from uuid import UUID

    from grins_platform.models.customer import Customer
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

    DOMAIN = "business"

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
        customer_responses = [
            CustomerResponse.model_validate(c) for c in customers
        ]

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
        writer.writerow([
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
        ])

        # Write data rows
        for customer in all_customers:
            writer.writerow([
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
            ])

        csv_content = output.getvalue()
        output.close()

        self.log_completed(
            "export_customers_csv",
            exported_count=len(all_customers),
        )

        return csv_content
