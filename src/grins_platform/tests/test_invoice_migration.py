"""Tests for invoice migrations.

This module tests the invoice-related migrations:
- 20250623_100000_create_invoices_table.py: Creates invoices table and sequence
- 20250624_100000_add_payment_collected_on_site.py: Adds payment_collected_on_site

Tests verify:
- Tables and columns are created correctly
- Indexes are created
- Constraints are enforced
- Sequence exists and works
- Rollback functionality

Requirements: 7.1-7.10, 10.6
"""

import importlib.util
from collections.abc import Generator
from pathlib import Path
from types import ModuleType

import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from grins_platform.database import DatabaseSettings


@pytest.fixture
def sync_engine() -> Engine:
    """Create a sync engine for migration testing."""
    settings = DatabaseSettings()
    sync_url = settings.database_url
    if sync_url.startswith("postgresql+asyncpg://"):
        sync_url = sync_url.replace("postgresql+asyncpg://", "postgresql://", 1)
    return create_engine(sync_url, pool_pre_ping=True)


@pytest.fixture
def sync_session(sync_engine: Engine) -> Generator[Session, None, None]:
    """Create a sync session for testing."""
    session_factory = sessionmaker(bind=sync_engine, expire_on_commit=False)
    session = session_factory()
    try:
        yield session
    finally:
        session.close()


def _load_invoice_migration_module() -> ModuleType:
    """Load the invoices table migration module dynamically."""
    migration_path = (
        Path(__file__).parent.parent
        / "migrations"
        / "versions"
        / "20250623_100000_create_invoices_table.py"
    )
    spec = importlib.util.spec_from_file_location("migration", str(migration_path))
    assert spec is not None
    assert spec.loader is not None
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    return migration


def _load_payment_collected_migration_module() -> ModuleType:
    """Load the payment_collected_on_site migration module dynamically."""
    migration_path = (
        Path(__file__).parent.parent
        / "migrations"
        / "versions"
        / "20250624_100000_add_payment_collected_on_site.py"
    )
    spec = importlib.util.spec_from_file_location("migration", str(migration_path))
    assert spec is not None
    assert spec.loader is not None
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    return migration


class TestInvoicesTableMigration:
    """Test suite for invoices table migration (20250623_100000)."""

    def test_invoices_table_exists(self, sync_engine: Engine) -> None:
        """Test that invoices table exists after migration."""
        inspector = inspect(sync_engine)
        tables = inspector.get_table_names()
        assert "invoices" in tables, "invoices table should exist"

    def test_invoices_table_has_id_column(self, sync_engine: Engine) -> None:
        """Test that invoices table has id column (UUID primary key)."""
        inspector = inspect(sync_engine)
        columns = {col["name"]: col for col in inspector.get_columns("invoices")}

        assert "id" in columns, "id column should exist"
        assert "UUID" in str(columns["id"]["type"]).upper()

    def test_invoices_table_has_job_id_column(self, sync_engine: Engine) -> None:
        """Test that invoices table has job_id column."""
        inspector = inspect(sync_engine)
        columns = {col["name"]: col for col in inspector.get_columns("invoices")}

        assert "job_id" in columns, "job_id column should exist"
        assert columns["job_id"]["nullable"] is False

    def test_invoices_table_has_customer_id_column(self, sync_engine: Engine) -> None:
        """Test that invoices table has customer_id column."""
        inspector = inspect(sync_engine)
        columns = {col["name"]: col for col in inspector.get_columns("invoices")}

        assert "customer_id" in columns, "customer_id column should exist"
        assert columns["customer_id"]["nullable"] is False

    def test_invoices_table_has_invoice_number_column(
        self, sync_engine: Engine,
    ) -> None:
        """Test that invoices table has invoice_number column (unique)."""
        inspector = inspect(sync_engine)
        columns = {col["name"]: col for col in inspector.get_columns("invoices")}

        assert "invoice_number" in columns, "invoice_number column should exist"
        assert columns["invoice_number"]["nullable"] is False
        assert str(columns["invoice_number"]["type"]).startswith("VARCHAR")

    def test_invoices_table_has_amount_columns(self, sync_engine: Engine) -> None:
        """Test that invoices table has amount, late_fee_amount, total_amount."""
        inspector = inspect(sync_engine)
        columns = {col["name"]: col for col in inspector.get_columns("invoices")}

        assert "amount" in columns, "amount column should exist"
        assert columns["amount"]["nullable"] is False
        assert "NUMERIC" in str(columns["amount"]["type"]).upper()

        assert "late_fee_amount" in columns, "late_fee_amount column should exist"
        assert columns["late_fee_amount"]["nullable"] is False

        assert "total_amount" in columns, "total_amount column should exist"
        assert columns["total_amount"]["nullable"] is False

    def test_invoices_table_has_date_columns(self, sync_engine: Engine) -> None:
        """Test that invoices table has invoice_date and due_date columns."""
        inspector = inspect(sync_engine)
        columns = {col["name"]: col for col in inspector.get_columns("invoices")}

        assert "invoice_date" in columns, "invoice_date column should exist"
        assert columns["invoice_date"]["nullable"] is False
        assert "DATE" in str(columns["invoice_date"]["type"]).upper()

        assert "due_date" in columns, "due_date column should exist"
        assert columns["due_date"]["nullable"] is False

    def test_invoices_table_has_status_column(self, sync_engine: Engine) -> None:
        """Test that invoices table has status column."""
        inspector = inspect(sync_engine)
        columns = {col["name"]: col for col in inspector.get_columns("invoices")}

        assert "status" in columns, "status column should exist"
        assert columns["status"]["nullable"] is False
        assert str(columns["status"]["type"]).startswith("VARCHAR")

    def test_invoices_table_has_payment_columns(self, sync_engine: Engine) -> None:
        """Test that invoices table has payment-related columns."""
        inspector = inspect(sync_engine)
        columns = {col["name"]: col for col in inspector.get_columns("invoices")}

        assert "payment_method" in columns, "payment_method column should exist"
        assert columns["payment_method"]["nullable"] is True

        assert "payment_reference" in columns, "payment_reference column should exist"
        assert columns["payment_reference"]["nullable"] is True

        assert "paid_at" in columns, "paid_at column should exist"
        assert columns["paid_at"]["nullable"] is True

        assert "paid_amount" in columns, "paid_amount column should exist"
        assert columns["paid_amount"]["nullable"] is True

    def test_invoices_table_has_reminder_columns(self, sync_engine: Engine) -> None:
        """Test that invoices table has reminder-related columns."""
        inspector = inspect(sync_engine)
        columns = {col["name"]: col for col in inspector.get_columns("invoices")}

        assert "reminder_count" in columns, "reminder_count column should exist"
        assert columns["reminder_count"]["nullable"] is False

        assert "last_reminder_sent" in columns, "last_reminder_sent column should exist"
        assert columns["last_reminder_sent"]["nullable"] is True

    def test_invoices_table_has_lien_columns(self, sync_engine: Engine) -> None:
        """Test that invoices table has lien-related columns."""
        inspector = inspect(sync_engine)
        columns = {col["name"]: col for col in inspector.get_columns("invoices")}

        assert "lien_eligible" in columns, "lien_eligible column should exist"
        assert columns["lien_eligible"]["nullable"] is False
        assert str(columns["lien_eligible"]["type"]).upper() == "BOOLEAN"

        assert "lien_warning_sent" in columns, "lien_warning_sent column should exist"
        assert columns["lien_warning_sent"]["nullable"] is True

        assert "lien_filed_date" in columns, "lien_filed_date column should exist"
        assert columns["lien_filed_date"]["nullable"] is True

    def test_invoices_table_has_line_items_column(self, sync_engine: Engine) -> None:
        """Test that invoices table has line_items JSONB column."""
        inspector = inspect(sync_engine)
        columns = {col["name"]: col for col in inspector.get_columns("invoices")}

        assert "line_items" in columns, "line_items column should exist"
        assert columns["line_items"]["nullable"] is True
        assert "JSONB" in str(columns["line_items"]["type"]).upper()

    def test_invoices_table_has_notes_column(self, sync_engine: Engine) -> None:
        """Test that invoices table has notes column."""
        inspector = inspect(sync_engine)
        columns = {col["name"]: col for col in inspector.get_columns("invoices")}

        assert "notes" in columns, "notes column should exist"
        assert columns["notes"]["nullable"] is True

    def test_invoices_table_has_timestamp_columns(self, sync_engine: Engine) -> None:
        """Test that invoices table has created_at and updated_at columns."""
        inspector = inspect(sync_engine)
        columns = {col["name"]: col for col in inspector.get_columns("invoices")}

        assert "created_at" in columns, "created_at column should exist"
        assert columns["created_at"]["nullable"] is False

        assert "updated_at" in columns, "updated_at column should exist"
        assert columns["updated_at"]["nullable"] is False


class TestInvoicesTableIndexes:
    """Test suite for invoices table indexes."""

    def test_job_id_index_exists(self, sync_engine: Engine) -> None:
        """Test that index on job_id exists."""
        inspector = inspect(sync_engine)
        indexes = inspector.get_indexes("invoices")

        job_id_index = None
        for idx in indexes:
            if "job_id" in idx.get("column_names", []):
                job_id_index = idx
                break

        assert job_id_index is not None, "Index on job_id should exist"

    def test_customer_id_index_exists(self, sync_engine: Engine) -> None:
        """Test that index on customer_id exists."""
        inspector = inspect(sync_engine)
        indexes = inspector.get_indexes("invoices")

        customer_id_index = None
        for idx in indexes:
            if "customer_id" in idx.get("column_names", []):
                customer_id_index = idx
                break

        assert customer_id_index is not None, "Index on customer_id should exist"

    def test_status_index_exists(self, sync_engine: Engine) -> None:
        """Test that index on status exists."""
        inspector = inspect(sync_engine)
        indexes = inspector.get_indexes("invoices")

        status_index = None
        for idx in indexes:
            if idx.get("column_names") == ["status"]:
                status_index = idx
                break

        assert status_index is not None, "Index on status should exist"

    def test_invoice_date_index_exists(self, sync_engine: Engine) -> None:
        """Test that index on invoice_date exists."""
        inspector = inspect(sync_engine)
        indexes = inspector.get_indexes("invoices")

        date_index = None
        for idx in indexes:
            if idx.get("column_names") == ["invoice_date"]:
                date_index = idx
                break

        assert date_index is not None, "Index on invoice_date should exist"

    def test_due_date_index_exists(self, sync_engine: Engine) -> None:
        """Test that index on due_date exists."""
        inspector = inspect(sync_engine)
        indexes = inspector.get_indexes("invoices")

        date_index = None
        for idx in indexes:
            if idx.get("column_names") == ["due_date"]:
                date_index = idx
                break

        assert date_index is not None, "Index on due_date should exist"

    def test_lien_eligible_index_exists(self, sync_engine: Engine) -> None:
        """Test that index on lien_eligible exists."""
        inspector = inspect(sync_engine)
        indexes = inspector.get_indexes("invoices")

        lien_index = None
        for idx in indexes:
            if idx.get("column_names") == ["lien_eligible"]:
                lien_index = idx
                break

        assert lien_index is not None, "Index on lien_eligible should exist"


class TestInvoicesTableConstraints:
    """Test suite for invoices table constraints."""

    def test_invoice_number_unique_constraint(self, sync_session: Session) -> None:
        """Test that invoice_number has unique constraint."""
        result = sync_session.execute(
            text("""
                SELECT constraint_name
                FROM information_schema.table_constraints
                WHERE table_name = 'invoices'
                AND constraint_type = 'UNIQUE'
            """),
        )
        constraints = [row[0] for row in result.fetchall()]

        # Check for unique constraint on invoice_number
        has_unique = any("invoice_number" in c for c in constraints)
        assert has_unique, "invoice_number should have unique constraint"

    def test_status_check_constraint(self, sync_session: Session) -> None:
        """Test that status has check constraint for valid values."""
        result = sync_session.execute(
            text("""
                SELECT constraint_name
                FROM information_schema.table_constraints
                WHERE table_name = 'invoices'
                AND constraint_type = 'CHECK'
            """),
        )
        constraints = [row[0] for row in result.fetchall()]

        has_status_check = any("status" in c for c in constraints)
        assert has_status_check, "status should have check constraint"

    def test_payment_method_check_constraint(self, sync_session: Session) -> None:
        """Test that payment_method has check constraint for valid values."""
        result = sync_session.execute(
            text("""
                SELECT constraint_name
                FROM information_schema.table_constraints
                WHERE table_name = 'invoices'
                AND constraint_type = 'CHECK'
            """),
        )
        constraints = [row[0] for row in result.fetchall()]

        has_payment_check = any("payment_method" in c for c in constraints)
        assert has_payment_check, "payment_method should have check constraint"

    def test_positive_amount_check_constraints(self, sync_session: Session) -> None:
        """Test that amount columns have positive value check constraints."""
        result = sync_session.execute(
            text("""
                SELECT constraint_name
                FROM information_schema.table_constraints
                WHERE table_name = 'invoices'
                AND constraint_type = 'CHECK'
            """),
        )
        constraints = [row[0] for row in result.fetchall()]

        has_amount_check = any("positive_amount" in c for c in constraints)
        has_late_fee_check = any("positive_late_fee" in c for c in constraints)
        has_total_check = any("positive_total" in c for c in constraints)

        assert has_amount_check, "amount should have positive check constraint"
        assert has_late_fee_check, "late_fee_amount should have positive check"
        assert has_total_check, "total_amount should have positive check constraint"


class TestInvoiceNumberSequence:
    """Test suite for invoice_number_seq sequence."""

    def test_sequence_exists(self, sync_session: Session) -> None:
        """Test that invoice_number_seq sequence exists."""
        result = sync_session.execute(
            text("""
                SELECT sequence_name
                FROM information_schema.sequences
                WHERE sequence_name = 'invoice_number_seq'
            """),
        )
        row = result.fetchone()
        assert row is not None, "invoice_number_seq sequence should exist"

    def test_sequence_returns_incrementing_values(
        self, sync_session: Session,
    ) -> None:
        """Test that sequence returns incrementing values."""
        result1 = sync_session.execute(
            text("SELECT nextval('invoice_number_seq')"),
        )
        val1 = result1.scalar()

        result2 = sync_session.execute(
            text("SELECT nextval('invoice_number_seq')"),
        )
        val2 = result2.scalar()

        assert val2 == val1 + 1, "Sequence should return incrementing values"


class TestInvoicesTableDefaults:
    """Test suite for invoices table default values."""

    def test_late_fee_amount_default(self, sync_session: Session) -> None:
        """Test that late_fee_amount defaults to 0."""
        result = sync_session.execute(
            text("""
                SELECT column_default
                FROM information_schema.columns
                WHERE table_name = 'invoices'
                AND column_name = 'late_fee_amount'
            """),
        )
        row = result.fetchone()
        assert row is not None
        assert row[0] is not None
        assert "0" in str(row[0])

    def test_status_default(self, sync_session: Session) -> None:
        """Test that status defaults to 'draft'."""
        result = sync_session.execute(
            text("""
                SELECT column_default
                FROM information_schema.columns
                WHERE table_name = 'invoices'
                AND column_name = 'status'
            """),
        )
        row = result.fetchone()
        assert row is not None
        assert row[0] is not None
        assert "draft" in str(row[0]).lower()

    def test_reminder_count_default(self, sync_session: Session) -> None:
        """Test that reminder_count defaults to 0."""
        result = sync_session.execute(
            text("""
                SELECT column_default
                FROM information_schema.columns
                WHERE table_name = 'invoices'
                AND column_name = 'reminder_count'
            """),
        )
        row = result.fetchone()
        assert row is not None
        assert row[0] is not None
        assert "0" in str(row[0])

    def test_lien_eligible_default(self, sync_session: Session) -> None:
        """Test that lien_eligible defaults to false."""
        result = sync_session.execute(
            text("""
                SELECT column_default
                FROM information_schema.columns
                WHERE table_name = 'invoices'
                AND column_name = 'lien_eligible'
            """),
        )
        row = result.fetchone()
        assert row is not None
        assert row[0] is not None
        assert "false" in str(row[0]).lower()


class TestPaymentCollectedOnSiteMigration:
    """Test suite for payment_collected_on_site migration (20250624_100000)."""

    def test_jobs_table_has_payment_collected_on_site_column(
        self, sync_engine: Engine,
    ) -> None:
        """Test that jobs table has payment_collected_on_site column."""
        inspector = inspect(sync_engine)
        columns = {col["name"]: col for col in inspector.get_columns("jobs")}

        assert (
            "payment_collected_on_site" in columns
        ), "payment_collected_on_site column should exist"
        assert columns["payment_collected_on_site"]["nullable"] is False
        assert str(columns["payment_collected_on_site"]["type"]).upper() == "BOOLEAN"

    def test_payment_collected_on_site_default(self, sync_session: Session) -> None:
        """Test that payment_collected_on_site defaults to false."""
        result = sync_session.execute(
            text("""
                SELECT column_default
                FROM information_schema.columns
                WHERE table_name = 'jobs'
                AND column_name = 'payment_collected_on_site'
            """),
        )
        row = result.fetchone()
        assert row is not None
        assert row[0] is not None
        assert "false" in str(row[0]).lower()


class TestInvoiceMigrationRollback:
    """Test suite for migration rollback functionality."""

    def test_invoice_migration_has_downgrade_function(self) -> None:
        """Test that invoice migration file has downgrade function."""
        migration = _load_invoice_migration_module()

        assert hasattr(migration, "downgrade")
        assert callable(migration.downgrade)

    def test_invoice_migration_has_upgrade_function(self) -> None:
        """Test that invoice migration file has upgrade function."""
        migration = _load_invoice_migration_module()

        assert hasattr(migration, "upgrade")
        assert callable(migration.upgrade)

    def test_invoice_migration_revision_chain(self) -> None:
        """Test that invoice migration has correct revision chain."""
        migration = _load_invoice_migration_module()

        assert migration.revision == "20250623_100000"
        assert migration.down_revision == "20250622_100000"

    def test_payment_collected_migration_has_downgrade_function(self) -> None:
        """Test that payment_collected migration has downgrade function."""
        migration = _load_payment_collected_migration_module()

        assert hasattr(migration, "downgrade")
        assert callable(migration.downgrade)

    def test_payment_collected_migration_has_upgrade_function(self) -> None:
        """Test that payment_collected migration has upgrade function."""
        migration = _load_payment_collected_migration_module()

        assert hasattr(migration, "upgrade")
        assert callable(migration.upgrade)

    def test_payment_collected_migration_revision_chain(self) -> None:
        """Test that payment_collected migration has correct revision chain."""
        migration = _load_payment_collected_migration_module()

        assert migration.revision == "20250624_100000"
        assert migration.down_revision == "20250623_100000"


class TestAllInvoiceColumnsPresent:
    """Test that all expected invoice columns are present."""

    def test_all_invoice_columns_present(self, sync_engine: Engine) -> None:
        """Test that all invoice columns are present."""
        inspector = inspect(sync_engine)
        columns = {col["name"] for col in inspector.get_columns("invoices")}

        expected_columns = {
            "id",
            "job_id",
            "customer_id",
            "invoice_number",
            "amount",
            "late_fee_amount",
            "total_amount",
            "invoice_date",
            "due_date",
            "status",
            "payment_method",
            "payment_reference",
            "paid_at",
            "paid_amount",
            "reminder_count",
            "last_reminder_sent",
            "lien_eligible",
            "lien_warning_sent",
            "lien_filed_date",
            "line_items",
            "notes",
            "created_at",
            "updated_at",
        }

        missing = expected_columns - columns
        assert not missing, f"Missing invoice columns: {missing}"
