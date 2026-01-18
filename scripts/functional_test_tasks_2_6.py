#!/usr/bin/env python3
"""
Functional validation script for Tasks 2-6 (Models, Schemas, Repositories, Services, Exceptions).

This script tests the components as a user/developer would interact with them,
validating that the layers work together correctly with a real database.
"""

import asyncio
import sys
from uuid import uuid4

# Add src to path
sys.path.insert(0, "src")


async def test_task_2_models():
    """Task 2: SQLAlchemy Models - Validate model creation and relationships."""
    print("\n" + "=" * 60)
    print("TASK 2: SQLAlchemy Models")
    print("=" * 60)

    try:
        from grins_platform.models import Customer, Property
        from grins_platform.models.enums import CustomerStatus, LeadSource, SystemType, PropertyType

        # Test 2.1: Customer model creation
        print("\n[2.1] Testing Customer model...")
        customer = Customer(
            first_name="John",
            last_name="Doe",
            phone="6125551234",
            email="john.doe@example.com",
            status=CustomerStatus.ACTIVE.value,  # Store as string value
            lead_source=LeadSource.WEBSITE.value,  # Store as string value
        )
        assert customer.first_name == "John"
        assert customer.status == CustomerStatus.ACTIVE.value
        # Note: SQLAlchemy defaults are applied at database level, not in Python
        # When creating a model instance without persisting, defaults may be None
        # This is expected behavior - defaults are server-side
        print("  ✅ Customer model created with correct field values")
        print(f"     (Note: is_priority={customer.is_priority}, sms_opt_in={customer.sms_opt_in})")
        print("     Server-side defaults apply when persisted to database")
    except Exception as e:
        print(f"  ❌ Error in 2.1: {e}")
        import traceback
        traceback.print_exc()
        raise

    # Test 2.2: Property model creation
    print("\n[2.2] Testing Property model...")
    prop = Property(
        customer_id=uuid4(),
        address="123 Main St",
        city="Eden Prairie",
        state="MN",
        zip_code="55344",
        zone_count=8,
        system_type=SystemType.STANDARD.value,  # Store as string value
        property_type=PropertyType.RESIDENTIAL.value,  # Store as string value
        is_primary=True,
    )
    assert prop.zone_count == 8
    assert prop.system_type == SystemType.STANDARD.value
    assert prop.is_primary is True
    print("  ✅ Property model created with correct values")

    # Test 2.3: Enum types
    print("\n[2.3] Testing enum types...")
    assert CustomerStatus.ACTIVE.value == "active"
    assert LeadSource.REFERRAL.value == "referral"
    assert SystemType.LAKE_PUMP.value == "lake_pump"
    assert PropertyType.COMMERCIAL.value == "commercial"
    print("  ✅ All enum types have correct values")

    print("\n✅ TASK 2 PASSED: All models work correctly")
    return True


async def test_task_3_schemas():
    """Task 3: Pydantic Schemas - Validate request/response schemas."""
    print("\n" + "=" * 60)
    print("TASK 3: Pydantic Schemas")
    print("=" * 60)

    from grins_platform.schemas.customer import (
        CustomerCreate,
        CustomerUpdate,
        CustomerFlagsUpdate,
        CustomerResponse,
    )
    from grins_platform.schemas.property import PropertyCreate, PropertyResponse

    # Test 3.1: CustomerCreate with phone normalization
    print("\n[3.1] Testing CustomerCreate schema with phone normalization...")
    customer_data = CustomerCreate(
        first_name="Jane",
        last_name="Smith",
        phone="(612) 555-4321",  # Various formats should normalize
        email="jane@example.com",
    )
    assert customer_data.phone == "6125554321"  # Normalized
    print(f"  ✅ Phone normalized: '(612) 555-4321' → '{customer_data.phone}'")

    # Test phone normalization idempotence (Property 6)
    customer_data2 = CustomerCreate(
        first_name="Test",
        last_name="User",
        phone="6125554321",  # Already normalized
        email="test@example.com",
    )
    assert customer_data2.phone == "6125554321"
    print("  ✅ Phone normalization is idempotent")

    # Test 3.2: CustomerUpdate with optional fields
    print("\n[3.2] Testing CustomerUpdate schema...")
    update_data = CustomerUpdate(first_name="Janet")
    assert update_data.first_name == "Janet"
    assert update_data.last_name is None  # Optional
    print("  ✅ CustomerUpdate allows partial updates")

    # Test 3.3: PropertyCreate with zone count validation (Property 4)
    print("\n[3.3] Testing PropertyCreate with zone count bounds...")
    prop_data = PropertyCreate(
        address="456 Oak Ave",
        city="Plymouth",
        state="MN",
        zip_code="55441",
        zone_count=12,
    )
    assert prop_data.zone_count == 12
    print("  ✅ Zone count 12 accepted (within 1-50 range)")

    # Test zone count bounds
    try:
        PropertyCreate(
            address="Test",
            city="Test",
            state="MN",
            zip_code="55555",
            zone_count=0,  # Invalid: below minimum
        )
        print("  ❌ Zone count 0 should have been rejected")
        return False
    except ValueError:
        print("  ✅ Zone count 0 correctly rejected (below minimum)")

    try:
        PropertyCreate(
            address="Test",
            city="Test",
            state="MN",
            zip_code="55555",
            zone_count=51,  # Invalid: above maximum
        )
        print("  ❌ Zone count 51 should have been rejected")
        return False
    except ValueError:
        print("  ✅ Zone count 51 correctly rejected (above maximum)")

    # Test 3.4: Email validation
    print("\n[3.4] Testing email validation...")
    try:
        CustomerCreate(
            first_name="Bad",
            last_name="Email",
            phone="6125551111",
            email="not-an-email",
        )
        print("  ❌ Invalid email should have been rejected")
        return False
    except ValueError:
        print("  ✅ Invalid email correctly rejected")

    print("\n✅ TASK 3 PASSED: All schemas validate correctly")
    return True


async def test_task_4_repositories():
    """Task 4: Repository Layer - Validate database operations."""
    print("\n" + "=" * 60)
    print("TASK 4: Repository Layer")
    print("=" * 60)

    from grins_platform.database import get_db_session
    from grins_platform.repositories import CustomerRepository, PropertyRepository
    from grins_platform.models.enums import LeadSource

    async for session in get_db_session():
        customer_repo = CustomerRepository(session)
        property_repo = PropertyRepository(session)

        unique_phone = f"612555{str(uuid4().int)[:4]}"  # Ensure 10 digits, only numbers
        unique_email = f"repo.test.{uuid4().hex[:6]}@example.com"

        # Test 4.1: Create customer
        print("\n[4.1] Testing CustomerRepository.create...")
        created = await customer_repo.create(
            first_name="Repo",
            last_name="Test",
            phone=unique_phone,
            email=unique_email,
            lead_source=LeadSource.WEBSITE.value,
        )
        assert created.id is not None
        print(f"  ✅ Customer created with ID: {created.id}")

        # Test 4.2: Get by ID
        print("\n[4.2] Testing CustomerRepository.get_by_id...")
        fetched = await customer_repo.get_by_id(created.id)
        assert fetched is not None
        assert fetched.first_name == "Repo"
        print(f"  ✅ Customer retrieved: {fetched.first_name} {fetched.last_name}")

        # Test 4.3: Find by phone
        print("\n[4.3] Testing CustomerRepository.find_by_phone...")
        found = await customer_repo.find_by_phone(created.phone)
        assert found is not None
        assert found.id == created.id
        print(f"  ✅ Customer found by phone: {created.phone}")

        # Test 4.4: Create property
        print("\n[4.4] Testing PropertyRepository.create...")
        created_prop = await property_repo.create(
            customer_id=created.id,
            address="789 Test Blvd",
            city="Maple Grove",
            state="MN",
            zip_code="55369",
            zone_count=6,
            is_primary=True,
        )
        assert created_prop.id is not None
        print(f"  ✅ Property created with ID: {created_prop.id}")

        # Test 4.5: Get properties by customer
        print("\n[4.5] Testing PropertyRepository.get_by_customer_id...")
        props = await property_repo.get_by_customer_id(created.id)
        assert len(props) == 1
        assert props[0].address == "789 Test Blvd"
        print(f"  ✅ Found {len(props)} property for customer")

        # Test 4.6: Soft delete
        print("\n[4.6] Testing CustomerRepository.soft_delete...")
        deleted = await customer_repo.soft_delete(created.id)
        assert deleted is True
        # Verify soft delete
        soft_deleted = await customer_repo.get_by_id(created.id, include_deleted=True)
        assert soft_deleted is not None
        assert soft_deleted.deleted_at is not None
        print("  ✅ Customer soft deleted (deleted_at set, data preserved)")

        await session.commit()
        break

    print("\n✅ TASK 4 PASSED: Repository layer works correctly")
    return True


async def test_task_5_services():
    """Task 5: Service Layer - Validate business logic."""
    print("\n" + "=" * 60)
    print("TASK 5: Service Layer")
    print("=" * 60)

    from grins_platform.database import get_db_session
    from grins_platform.repositories import CustomerRepository, PropertyRepository
    from grins_platform.services import CustomerService, PropertyService
    from grins_platform.schemas.customer import CustomerCreate, CustomerFlagsUpdate
    from grins_platform.schemas.property import PropertyCreate
    from grins_platform.exceptions import DuplicateCustomerError

    async for session in get_db_session():
        # Create repositories
        customer_repo = CustomerRepository(session)
        property_repo = PropertyRepository(session)
        
        # Create services with repositories
        customer_service = CustomerService(customer_repo)
        property_service = PropertyService(property_repo)

        unique_phone = f"612555{str(uuid4().int)[:4]}"  # Ensure 10 digits, only numbers
        unique_email = f"svc.test.{uuid4().hex[:6]}@example.com"

        # Test 5.1: Create customer via service
        print("\n[5.1] Testing CustomerService.create_customer...")
        customer_data = CustomerCreate(
            first_name="Service",
            last_name="Test",
            phone=unique_phone,
            email=unique_email,
        )
        customer = await customer_service.create_customer(customer_data)
        assert customer.id is not None
        assert customer.sms_opt_in is False  # Property 5: defaults to opted-out
        assert customer.email_opt_in is False  # Property 5: defaults to opted-out
        print(f"  ✅ Customer created via service: {customer.id}")
        print("  ✅ Communication preferences default to opted-out (Property 5)")

        # Test 5.2: Duplicate phone detection (Property 1)
        print("\n[5.2] Testing duplicate phone detection (Property 1)...")
        duplicate_data = CustomerCreate(
            first_name="Duplicate",
            last_name="Phone",
            phone=unique_phone,  # Same phone
            email="different@example.com",
        )
        try:
            await customer_service.create_customer(duplicate_data)
            print("  ❌ Duplicate phone should have been rejected")
            return False
        except DuplicateCustomerError:
            print("  ✅ Duplicate phone correctly rejected")

        # Test 5.3: Add property via service
        print("\n[5.3] Testing PropertyService.add_property...")
        prop_data = PropertyCreate(
            address="Service Test Rd",
            city="Brooklyn Park",
            state="MN",
            zip_code="55443",
            zone_count=10,
            is_primary=True,
        )
        prop = await property_service.add_property(customer.id, prop_data)
        assert prop.id is not None
        assert prop.is_primary is True
        print(f"  ✅ Property added via service: {prop.id}")

        # Test 5.4: Primary property uniqueness (Property 3)
        print("\n[5.4] Testing primary property uniqueness (Property 3)...")
        prop2_data = PropertyCreate(
            address="Second Property Ln",
            city="Rogers",
            state="MN",
            zip_code="55374",
            zone_count=5,
            is_primary=True,  # Setting as primary should clear first
        )
        prop2 = await property_service.add_property(customer.id, prop2_data)
        assert prop2.is_primary is True

        # Verify first property is no longer primary
        props = await property_service.get_customer_properties(customer.id)
        primary_count = sum(1 for p in props if p.is_primary)
        assert primary_count == 1, f"Expected 1 primary, got {primary_count}"
        print("  ✅ Only one primary property per customer (Property 3)")

        # Test 5.5: Update customer flags
        print("\n[5.5] Testing CustomerService.update_flags...")
        flags_update = CustomerFlagsUpdate(
            is_priority=True,
            is_red_flag=False,
        )
        updated = await customer_service.update_flags(customer.id, flags_update)
        assert updated.is_priority is True, f"Expected is_priority=True, got {updated.is_priority}"
        print("  ✅ Customer flags updated successfully")

        # Test 5.6: List customers with pagination
        print("\n[5.6] Testing CustomerService.list_customers...")
        from grins_platform.schemas.customer import CustomerListParams
        list_params = CustomerListParams(page=1, page_size=10)
        result = await customer_service.list_customers(list_params)
        assert result.total >= 1, f"Expected at least 1 customer, got {result.total}"
        print(f"  ✅ Listed {result.total} customers with pagination")

        await session.commit()
        break

    print("\n✅ TASK 5 PASSED: Service layer works correctly")
    return True


async def test_task_6_exceptions():
    """Task 6: Custom Exceptions - Validate exception handling."""
    print("\n" + "=" * 60)
    print("TASK 6: Custom Exceptions")
    print("=" * 60)

    from grins_platform.exceptions import (
        CustomerError,
        CustomerNotFoundError,
        DuplicateCustomerError,
        PropertyNotFoundError,
        ValidationError,
    )
    from uuid import uuid4

    # Test 6.1: Exception hierarchy
    print("\n[6.1] Testing exception hierarchy...")
    assert issubclass(CustomerNotFoundError, CustomerError)
    assert issubclass(DuplicateCustomerError, CustomerError)
    assert issubclass(PropertyNotFoundError, CustomerError)
    assert issubclass(ValidationError, CustomerError)
    print("  ✅ All exceptions inherit from CustomerError")

    # Test 6.2: CustomerNotFoundError
    print("\n[6.2] Testing CustomerNotFoundError...")
    test_id = uuid4()
    error = CustomerNotFoundError(test_id)
    assert str(test_id) in str(error)
    print(f"  ✅ CustomerNotFoundError: {error}")

    # Test 6.3: DuplicateCustomerError
    print("\n[6.3] Testing DuplicateCustomerError...")
    error = DuplicateCustomerError("6125551234")
    assert "6125551234" in str(error)
    print(f"  ✅ DuplicateCustomerError: {error}")

    # Test 6.4: PropertyNotFoundError
    print("\n[6.4] Testing PropertyNotFoundError...")
    prop_id = uuid4()
    error = PropertyNotFoundError(prop_id)
    assert str(prop_id) in str(error)
    print(f"  ✅ PropertyNotFoundError: {error}")

    # Test 6.5: ValidationError
    print("\n[6.5] Testing ValidationError...")
    error = ValidationError("phone", "Invalid phone format")
    assert "phone" in str(error)
    print(f"  ✅ ValidationError: {error}")

    print("\n✅ TASK 6 PASSED: All exceptions work correctly")
    return True


async def main():
    """Run all functional tests."""
    print("\n" + "=" * 60)
    print("FUNCTIONAL VALIDATION: Tasks 2-6")
    print("Testing as a user/developer would interact with the system")
    print("=" * 60)

    results = {}

    try:
        results["Task 2: Models"] = await test_task_2_models()
    except Exception as e:
        print(f"\n❌ TASK 2 FAILED: {e}")
        results["Task 2: Models"] = False

    try:
        results["Task 3: Schemas"] = await test_task_3_schemas()
    except Exception as e:
        print(f"\n❌ TASK 3 FAILED: {e}")
        results["Task 3: Schemas"] = False

    try:
        results["Task 4: Repositories"] = await test_task_4_repositories()
    except Exception as e:
        print(f"\n❌ TASK 4 FAILED: {e}")
        results["Task 4: Repositories"] = False

    try:
        results["Task 5: Services"] = await test_task_5_services()
    except Exception as e:
        print(f"\n❌ TASK 5 FAILED: {e}")
        results["Task 5: Services"] = False

    try:
        results["Task 6: Exceptions"] = await test_task_6_exceptions()
    except Exception as e:
        print(f"\n❌ TASK 6 FAILED: {e}")
        results["Task 6: Exceptions"] = False

    # Summary
    print("\n" + "=" * 60)
    print("VALIDATION SUMMARY")
    print("=" * 60)
    all_passed = True
    for task, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"  {task}: {status}")
        if not passed:
            all_passed = False

    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 ALL FUNCTIONAL TESTS PASSED!")
        print("Tasks 2-6 validated end-to-end with real database.")
    else:
        print("⚠️  SOME TESTS FAILED - Review output above")
    print("=" * 60)

    return 0 if all_passed else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
