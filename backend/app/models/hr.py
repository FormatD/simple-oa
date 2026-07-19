"""HR models: employee, attendance, leave management."""
from __future__ import annotations

import uuid
from datetime import date, datetime, timezone

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin


class Position(TimestampMixin, Base):
    """HR position definitions (no permission meaning)."""
    __tablename__ = "positions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    organization = relationship("Organization", backref="positions")


class Employee(TimestampMixin, Base):
    """Employee profiles."""
    __tablename__ = "employees"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    employee_no: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False
    )
    department_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("departments.id"), nullable=True, index=True
    )
    position_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("positions.id"), nullable=True, index=True
    )
    reports_to: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("employees.id"), nullable=True, index=True
    )
    hire_date: Mapped[date] = mapped_column(Date, nullable=False)
    employment_type: Mapped[str] = mapped_column(
        String(50), default="full_time"
    )
    status: Mapped[str] = mapped_column(
        String(50), default="active", index=True
    )
    work_location: Mapped[str | None] = mapped_column(String(200), nullable=True)
    # R6: Field-level encryption — emergency_contact stored encrypted at application level
    emergency_contact: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    user = relationship("User", backref="employee_profile")
    department = relationship("Department", backref="employees")
    position = relationship("Position", backref="employees")
    manager = relationship("Employee", backref="subordinates", remote_side="Employee.id")


class EmployeeContract(TimestampMixin, Base):
    """Employee contracts."""
    __tablename__ = "employee_contracts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    employee_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("employees.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    contract_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    probation_months: Mapped[int] = mapped_column(Integer, default=0)
    signing_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    document_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    employee = relationship("Employee", backref="contracts")


class AttendanceRecord(TimestampMixin, Base):
    """Attendance check-in/out records.
    CR E2: check_in_time / check_out_time dual column mode.
    """
    __tablename__ = "attendance_records"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    employee_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("employees.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    date: Mapped[date] = mapped_column(Date, nullable=False)
    check_in_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    check_out_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    check_in_location: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    check_out_location: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="present", index=True)
    overtime_hours: Mapped[float | None] = mapped_column(Numeric(5, 2), default=0)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    employee = relationship("Employee", backref="attendance_records")


class LeaveType(TimestampMixin, Base):
    """Leave/absence types."""
    __tablename__ = "leave_types"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    paid: Mapped[bool] = mapped_column(Boolean, default=False)
    requires_approval: Mapped[bool] = mapped_column(Boolean, default=True)
    max_days_per_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    min_notice_hours: Mapped[int] = mapped_column(Integer, default=0)

    organization = relationship("Organization", backref="leave_types")


class LeaveBalance(TimestampMixin, Base):
    """Leave balance per employee per year."""
    __tablename__ = "leave_balances"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    employee_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("employees.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    leave_type_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("leave_types.id", ondelete="CASCADE"),
        nullable=False,
    )
    total_days: Mapped[float] = mapped_column(Numeric(6, 2), nullable=False, default=0)
    used_days: Mapped[float] = mapped_column(Numeric(6, 2), nullable=False, default=0)
    pending_days: Mapped[float] = mapped_column(Numeric(6, 2), nullable=False, default=0)
    year: Mapped[int] = mapped_column(Integer, nullable=False)

    employee = relationship("Employee", backref="leave_balances")
    leave_type = relationship("LeaveType")


class LeaveRequest(TimestampMixin, Base):
    """Leave requests with approval chain.
    CR E1: When reports_to is null, auto-escalate to next manager.
    """
    __tablename__ = "leave_requests"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    employee_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("employees.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    leave_type_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("leave_types.id"), nullable=False
    )
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    total_days: Mapped[float] = mapped_column(Numeric(6, 2), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(50), default="pending", index=True
    )
    # CR E1: approver_id resolved from reports_to chain
    approver_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("employees.id"), nullable=True, index=True
    )
    # CR E1: proxy_approver for delegation support
    proxy_approver_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("employees.id"), nullable=True
    )
    approved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    employee = relationship("Employee", backref="leave_requests", foreign_keys=[employee_id])
    leave_type = relationship("LeaveType")
    approver = relationship("Employee", foreign_keys=[approver_id])


# ─── R10: Interviewer Availability ────────────────────

class InterviewerAvailability(TimestampMixin, Base):
    """Interviewer availability tracking (R10)."""
    __tablename__ = "interviewer_availability"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    employee_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("employees.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    date: Mapped[date] = mapped_column(Date, nullable=False)
    time_slot: Mapped[str] = mapped_column(
        String(20), nullable=False  # morning, afternoon, evening
    )
    status: Mapped[str] = mapped_column(
        String(20), default="available",  # available, busy, out_of_office
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    employee = relationship("Employee", backref="interviewer_availability")
