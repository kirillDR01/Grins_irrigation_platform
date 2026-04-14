"""Customer document model for file storage metadata.

Validates: CRM Changes Update 2 Req 17.3
"""

from datetime import datetime
from typing import TYPE_CHECKING, Optional
from uuid import UUID

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from grins_platform.database import Base

if TYPE_CHECKING:
    from grins_platform.models.customer import Customer


class CustomerDocument(Base):
    """Customer document record linked to S3 storage.

    Validates: CRM Changes Update 2 Req 17.3
    """

    __tablename__ = "customer_documents"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    customer_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=False,
    )
    # Scope signing documents (estimate/contract/signed_contract) to the
    # specific pipeline entry they were uploaded under, so customers with
    # more than one active Sales entry sign the correct document.
    # Nullable for legacy rows — ``_get_signing_document`` falls back to
    # customer-scoped lookup when this is NULL. (bughunt H-7)
    sales_entry_id: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("sales_entries.id", ondelete="SET NULL"),
        nullable=True,
    )
    file_key: Mapped[str] = mapped_column(String(512), nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    document_type: Mapped[str] = mapped_column(String(50), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    uploaded_by: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        nullable=True,
    )

    # Relationships
    customer: Mapped["Customer"] = relationship("Customer", lazy="selectin")

    __table_args__ = (
        Index("ix_customer_documents_customer_id", "customer_id"),
        Index("ix_customer_documents_document_type", "document_type"),
        Index("ix_customer_documents_sales_entry_id", "sales_entry_id"),
    )

    def __repr__(self) -> str:
        return (
            f"<CustomerDocument(id={self.id}, "
            f"file_name='{self.file_name}', type='{self.document_type}')>"
        )
