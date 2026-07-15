"""Data import record models."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin


class ImportRecord(TimestampMixin, Base):
    """Data import records."""
    __tablename__ = "import_records"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False, index=True
    )
    import_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    filename: Mapped[str] = mapped_column(String(500), nullable=False)
    total_rows: Mapped[int] = mapped_column(Integer, default=0)
    success_rows: Mapped[int] = mapped_column(Integer, default=0)
    error_rows: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(50), default="pending", index=True)
    errors: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    summary: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    imported_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    organization = relationship("Organization")
    importer = relationship("User", backref="import_records")
