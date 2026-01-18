# Implement Migration

Generate an Alembic migration from the design document schema.

## Instructions

1. **Read Design Document**: 
   - Find the relevant design.md in `.kiro/specs/{feature}/`
   - Extract the SQL schema definition for the requested table

2. **Generate Migration File**:
   - Create in `src/grins_platform/migrations/versions/`
   - Use naming convention: `{YYYYMMDD}_{HHMMSS}_{description}.py`
   - Follow Alembic async patterns used in existing migrations

3. **Migration Template**:

```python
"""Create {table_name} table.

Revision ID: {auto-generated}
Revises: {previous revision}
Create Date: {timestamp}
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers
revision: str = "{generate unique id}"
down_revision: str | None = "{previous revision}"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "{table_name}",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        # ... columns from design doc ...
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
    )
    
    # Create indexes
    op.create_index("idx_{table}_{column}", "{table_name}", ["{column}"])
    
    # Add check constraints if needed
    # op.create_check_constraint(...)


def downgrade() -> None:
    op.drop_table("{table_name}")
```

4. **Include from Design Doc**:
   - All columns with correct types
   - Primary keys and foreign keys
   - Indexes as specified
   - Check constraints for enums
   - Default values

5. **Verify Migration**:
   - Check syntax is correct
   - Ensure foreign key references exist
   - Verify constraint names are unique

## Usage

```
@implement-migration service_offerings
@implement-migration jobs
@implement-migration staff
@implement-migration job_status_history
```

## Related Prompts
- `@implement-model` - Create SQLAlchemy model after migration
- `@quality-check` - Verify migration syntax
