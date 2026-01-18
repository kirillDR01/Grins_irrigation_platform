"""Create updated_at trigger function.

Revision ID: 003_updated_at_trigger
Revises: 002_properties
Create Date: 2025-06-13 14:02:00

This migration creates a PostgreSQL trigger function that automatically
updates the updated_at timestamp whenever a row is modified. The trigger
is applied to both customers and properties tables.

Validates: Requirement 1.7
"""

from collections.abc import Sequence
from typing import Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "003_updated_at_trigger"
down_revision: Union[str, None] = "002_properties"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create trigger function and apply to tables."""
    # Create the trigger function
    op.execute("""
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ language 'plpgsql';
    """)

    # Apply trigger to customers table
    op.execute("""
        CREATE TRIGGER update_customers_updated_at
            BEFORE UPDATE ON customers
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
    """)

    # Apply trigger to properties table
    op.execute("""
        CREATE TRIGGER update_properties_updated_at
            BEFORE UPDATE ON properties
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
    """)


def downgrade() -> None:
    """Remove triggers and function."""
    # Drop triggers first
    op.execute("DROP TRIGGER IF EXISTS update_properties_updated_at ON properties;")
    op.execute("DROP TRIGGER IF EXISTS update_customers_updated_at ON customers;")

    # Drop the function
    op.execute("DROP FUNCTION IF EXISTS update_updated_at_column();")
