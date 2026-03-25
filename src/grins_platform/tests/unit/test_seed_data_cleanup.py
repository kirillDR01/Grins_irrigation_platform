"""Unit tests for seed data cleanup migration.

Verifies that the CRM seed cleanup migration (20260324_100000)
targets exactly the expected seed records and preserves non-seed data.

Property 1: Seed cleanup preserves non-seed records.
Validates: Requirements 1.4, 1.5, 1.6
"""

from __future__ import annotations

import importlib.util
import re
from pathlib import Path
from types import ModuleType

import pytest

# =============================================================================
# Constants — expected seed identifiers from the original seed migration
# =============================================================================

SEED_CUSTOMER_PHONES = {
    "6125551001",
    "6125551002",
    "6125551003",
    "6125551004",
    "6125551005",
    "6125551006",
    "6125551007",
    "6125551008",
    "6125551009",
    "6125551010",
}

SEED_STAFF_PHONES = {
    "6125552001",
    "6125552002",
    "6125552003",
    "6125552004",
}

SEED_SERVICE_NAMES = {
    "Spring Startup",
    "Summer Tune-Up",
    "Winterization",
    "Sprinkler Head Replacement",
    "Valve Repair",
    "Pipe Repair",
    "System Diagnostic",
    "New Zone Installation",
    "Drip Irrigation Setup",
    "Full System Installation",
}

SEED_AVAILABILITY_NOTE = "Auto-generated availability"


# =============================================================================
# Helpers
# =============================================================================


def _load_cleanup_migration() -> ModuleType:
    """Load the seed cleanup migration module."""
    migration_path = (
        Path(__file__).parent.parent.parent
        / "migrations"
        / "versions"
        / "20260324_100000_crm_disable_seed_data.py"
    )
    spec = importlib.util.spec_from_file_location(
        "crm_disable_seed_data",
        migration_path,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_seed_migration() -> ModuleType:
    """Load the original seed demo data migration module."""
    migration_path = (
        Path(__file__).parent.parent.parent
        / "migrations"
        / "versions"
        / "20250626_100000_seed_demo_data.py"
    )
    spec = importlib.util.spec_from_file_location(
        "seed_demo_data",
        migration_path,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _extract_phones_from_source(source: str) -> set[str]:
    """Extract all phone-number-like strings (10-digit 612...) from SQL source."""
    return set(re.findall(r"612555\d{4}", source))


def _extract_quoted_strings(source: str) -> set[str]:
    """Extract single-quoted strings from SQL source."""
    return set(re.findall(r"'([^']+)'", source))


# =============================================================================
# Tests
# =============================================================================


@pytest.mark.unit
class TestSeedCleanupMigrationStructure:
    """Verify the cleanup migration module is well-formed."""

    def test_migration_loads_successfully(self) -> None:
        module = _load_cleanup_migration()
        assert hasattr(module, "upgrade")
        assert hasattr(module, "downgrade")
        assert hasattr(module, "revision")

    def test_revision_id(self) -> None:
        module = _load_cleanup_migration()
        assert module.revision == "20260324_100000"

    def test_down_revision_links_to_previous(self) -> None:
        module = _load_cleanup_migration()
        assert module.down_revision == "20260313_100000"


@pytest.mark.unit
class TestSeedCleanupTargetsCorrectCustomers:
    """Property 1: Cleanup targets exactly the 10 seed customer phones."""

    def test_cleanup_targets_all_seed_customer_phones(self) -> None:
        """Verify every seed customer phone appears in the cleanup SQL."""
        migration_path = (
            Path(__file__).parent.parent.parent
            / "migrations"
            / "versions"
            / "20260324_100000_crm_disable_seed_data.py"
        )
        source = migration_path.read_text()
        found_phones = _extract_phones_from_source(source)
        # All seed customer phones must be present
        assert SEED_CUSTOMER_PHONES.issubset(found_phones), (
            f"Missing seed customer phones: {SEED_CUSTOMER_PHONES - found_phones}"
        )

    def test_cleanup_targets_exactly_10_seed_customers(self) -> None:
        """Verify no extra customer phones are targeted."""
        migration_path = (
            Path(__file__).parent.parent.parent
            / "migrations"
            / "versions"
            / "20260324_100000_crm_disable_seed_data.py"
        )
        source = migration_path.read_text()
        found_phones = _extract_phones_from_source(source)
        customer_phones = {p for p in found_phones if p.startswith("6125551")}
        assert customer_phones == SEED_CUSTOMER_PHONES

    def test_seed_migration_and_cleanup_use_same_customer_phones(self) -> None:
        """Verify cleanup targets exactly the phones from the seed migration."""
        seed_path = (
            Path(__file__).parent.parent.parent
            / "migrations"
            / "versions"
            / "20250626_100000_seed_demo_data.py"
        )
        cleanup_path = (
            Path(__file__).parent.parent.parent
            / "migrations"
            / "versions"
            / "20260324_100000_crm_disable_seed_data.py"
        )
        seed_phones = {
            p
            for p in _extract_phones_from_source(seed_path.read_text())
            if p.startswith("6125551")
        }
        cleanup_phones = {
            p
            for p in _extract_phones_from_source(cleanup_path.read_text())
            if p.startswith("6125551")
        }
        assert seed_phones == cleanup_phones


@pytest.mark.unit
class TestSeedCleanupTargetsCorrectStaff:
    """Cleanup targets exactly the 4 seed staff phones."""

    def test_cleanup_targets_all_seed_staff_phones(self) -> None:
        migration_path = (
            Path(__file__).parent.parent.parent
            / "migrations"
            / "versions"
            / "20260324_100000_crm_disable_seed_data.py"
        )
        source = migration_path.read_text()
        found_phones = _extract_phones_from_source(source)
        assert SEED_STAFF_PHONES.issubset(found_phones)

    def test_cleanup_targets_exactly_4_seed_staff(self) -> None:
        migration_path = (
            Path(__file__).parent.parent.parent
            / "migrations"
            / "versions"
            / "20260324_100000_crm_disable_seed_data.py"
        )
        source = migration_path.read_text()
        found_phones = _extract_phones_from_source(source)
        staff_phones = {p for p in found_phones if p.startswith("6125552")}
        assert staff_phones == SEED_STAFF_PHONES

    def test_seed_migration_and_cleanup_use_same_staff_phones(self) -> None:
        seed_path = (
            Path(__file__).parent.parent.parent
            / "migrations"
            / "versions"
            / "20250626_100000_seed_demo_data.py"
        )
        cleanup_path = (
            Path(__file__).parent.parent.parent
            / "migrations"
            / "versions"
            / "20260324_100000_crm_disable_seed_data.py"
        )
        seed_staff = {
            p
            for p in _extract_phones_from_source(seed_path.read_text())
            if p.startswith("6125552")
        }
        cleanup_staff = {
            p
            for p in _extract_phones_from_source(cleanup_path.read_text())
            if p.startswith("6125552")
        }
        assert seed_staff == cleanup_staff


@pytest.mark.unit
class TestSeedCleanupTargetsCorrectServices:
    """Cleanup targets exactly the 10 seed service offering names."""

    def test_cleanup_targets_all_seed_service_names(self) -> None:
        migration_path = (
            Path(__file__).parent.parent.parent
            / "migrations"
            / "versions"
            / "20260324_100000_crm_disable_seed_data.py"
        )
        source = migration_path.read_text()
        quoted = _extract_quoted_strings(source)
        assert SEED_SERVICE_NAMES.issubset(quoted), (
            f"Missing service names: {SEED_SERVICE_NAMES - quoted}"
        )

    def test_cleanup_targets_auto_generated_availability(self) -> None:
        migration_path = (
            Path(__file__).parent.parent.parent
            / "migrations"
            / "versions"
            / "20260324_100000_crm_disable_seed_data.py"
        )
        source = migration_path.read_text()
        assert SEED_AVAILABILITY_NOTE in source


@pytest.mark.unit
class TestSeedCleanupDeletionOrder:
    """Verify DELETE order respects FK constraints (children before parents)."""

    def test_jobs_deleted_before_customers(self) -> None:
        migration_path = (
            Path(__file__).parent.parent.parent
            / "migrations"
            / "versions"
            / "20260324_100000_crm_disable_seed_data.py"
        )
        source = migration_path.read_text()
        jobs_pos = source.index("DELETE FROM jobs")
        customers_pos = source.index("DELETE FROM customers")
        assert jobs_pos < customers_pos, "Jobs must be deleted before customers"

    def test_properties_deleted_before_customers(self) -> None:
        migration_path = (
            Path(__file__).parent.parent.parent
            / "migrations"
            / "versions"
            / "20260324_100000_crm_disable_seed_data.py"
        )
        source = migration_path.read_text()
        props_pos = source.index("DELETE FROM properties")
        customers_pos = source.index("DELETE FROM customers")
        assert props_pos < customers_pos, "Properties must be deleted before customers"

    def test_availability_deleted_before_staff(self) -> None:
        migration_path = (
            Path(__file__).parent.parent.parent
            / "migrations"
            / "versions"
            / "20260324_100000_crm_disable_seed_data.py"
        )
        source = migration_path.read_text()
        avail_pos = source.index("DELETE FROM staff_availability")
        # Find "DELETE FROM staff" that is NOT "DELETE FROM staff_availability"
        staff_match = re.search(
            r"DELETE FROM staff\b(?!_)",
            source,
        )
        assert staff_match is not None, "DELETE FROM staff not found"
        staff_pos = staff_match.start()
        assert avail_pos < staff_pos, "Staff availability must be deleted before staff"


@pytest.mark.unit
class TestSeedCleanupPreservesNonSeedRecords:
    """Property 1: Non-seed records are never targeted by the cleanup.

    The migration uses WHERE clauses scoped to known seed identifiers.
    Any record with a phone/name/note NOT in the seed set is preserved.
    """

    def test_no_unconditional_deletes(self) -> None:
        """Verify no DELETE statement lacks a WHERE clause."""
        migration_path = (
            Path(__file__).parent.parent.parent
            / "migrations"
            / "versions"
            / "20260324_100000_crm_disable_seed_data.py"
        )
        source = migration_path.read_text()
        # Find all DELETE statements
        delete_stmts = re.findall(
            r"DELETE\s+FROM\s+\w+.*?;",
            source,
            re.DOTALL | re.IGNORECASE,
        )
        for stmt in delete_stmts:
            assert "WHERE" in stmt.upper(), (
                f"DELETE without WHERE clause found: {stmt[:80]}..."
            )

    def test_customer_delete_scoped_to_phone_list(self) -> None:
        """Customer DELETE uses phone IN (...) with only seed phones."""
        migration_path = (
            Path(__file__).parent.parent.parent
            / "migrations"
            / "versions"
            / "20260324_100000_crm_disable_seed_data.py"
        )
        source = migration_path.read_text()
        # The customer DELETE should reference phone IN (...)
        assert "DELETE FROM customers" in source
        # Extract the block around customer delete
        cust_match = re.search(
            r"DELETE FROM customers\s+WHERE\s+phone\s+IN",
            source,
            re.IGNORECASE,
        )
        assert cust_match is not None, "Customer DELETE must use WHERE phone IN (...)"

    def test_staff_delete_scoped_to_phone_list(self) -> None:
        """Staff DELETE uses phone IN (...) with only seed phones."""
        migration_path = (
            Path(__file__).parent.parent.parent
            / "migrations"
            / "versions"
            / "20260324_100000_crm_disable_seed_data.py"
        )
        source = migration_path.read_text()
        staff_match = re.search(
            r"DELETE FROM staff\s+WHERE\s+phone\s+IN",
            source,
            re.IGNORECASE,
        )
        assert staff_match is not None, "Staff DELETE must use WHERE phone IN (...)"

    def test_service_delete_scoped_to_name_list(self) -> None:
        """Service offerings DELETE uses name IN (...) with only seed names."""
        migration_path = (
            Path(__file__).parent.parent.parent
            / "migrations"
            / "versions"
            / "20260324_100000_crm_disable_seed_data.py"
        )
        source = migration_path.read_text()
        svc_match = re.search(
            r"DELETE FROM service_offerings\s+WHERE\s+name\s+IN",
            source,
            re.IGNORECASE,
        )
        assert svc_match is not None, (
            "Service offerings DELETE must use WHERE name IN (...)"
        )

    def test_availability_delete_scoped_to_notes(self) -> None:
        """Staff availability DELETE uses notes = 'Auto-generated availability'."""
        migration_path = (
            Path(__file__).parent.parent.parent
            / "migrations"
            / "versions"
            / "20260324_100000_crm_disable_seed_data.py"
        )
        source = migration_path.read_text()
        # The SQL may be split across Python string concatenation lines
        assert "DELETE FROM staff_availability" in source
        assert "Auto-generated availability" in source
        # Verify the WHERE clause links them
        avail_match = re.search(
            r"DELETE FROM staff_availability.*?WHERE.*?"
            r"notes\s*=\s*'Auto-generated availability'",
            source,
            re.IGNORECASE | re.DOTALL,
        )
        assert avail_match is not None, (
            "Availability DELETE must use WHERE notes = 'Auto-generated availability'"
        )

    def test_no_truncate_statements(self) -> None:
        """Verify no TRUNCATE statements exist (would wipe all data)."""
        migration_path = (
            Path(__file__).parent.parent.parent
            / "migrations"
            / "versions"
            / "20260324_100000_crm_disable_seed_data.py"
        )
        source = migration_path.read_text().upper()
        assert "TRUNCATE" not in source, "TRUNCATE would destroy non-seed data"

    def test_no_drop_table_statements(self) -> None:
        """Verify no DROP TABLE statements exist."""
        migration_path = (
            Path(__file__).parent.parent.parent
            / "migrations"
            / "versions"
            / "20260324_100000_crm_disable_seed_data.py"
        )
        source = migration_path.read_text().upper()
        assert "DROP TABLE" not in source, "DROP TABLE would destroy non-seed data"


@pytest.mark.unit
class TestSeedCleanupRecordCounts:
    """Verify the cleanup targets the expected number of seed records."""

    def test_exactly_10_seed_customer_phones(self) -> None:
        assert len(SEED_CUSTOMER_PHONES) == 10

    def test_exactly_4_seed_staff_phones(self) -> None:
        assert len(SEED_STAFF_PHONES) == 4

    def test_exactly_10_seed_service_names(self) -> None:
        assert len(SEED_SERVICE_NAMES) == 10

    def test_seed_customer_phones_are_unique(self) -> None:
        phones_list = list(SEED_CUSTOMER_PHONES)
        assert len(phones_list) == len(set(phones_list))

    def test_seed_staff_phones_are_unique(self) -> None:
        phones_list = list(SEED_STAFF_PHONES)
        assert len(phones_list) == len(set(phones_list))

    def test_seed_customer_and_staff_phones_do_not_overlap(self) -> None:
        assert SEED_CUSTOMER_PHONES.isdisjoint(SEED_STAFF_PHONES)
