"""Training management models: courses, plans, instructors, materials, registrations, evaluations, certificates."""
from __future__ import annotations

import uuid
from datetime import date, datetime, timezone

from sqlalchemy import Date, DateTime, ForeignKey, Integer, Numeric, String, Text, Time
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin


class TrainingInstructor(TimestampMixin, Base):
    """Training instructor profiles (internal employees or external)."""
    __tablename__ = "training_instructors"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    employee_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("employees.id"), nullable=True, index=True
    )
    title: Mapped[str | None] = mapped_column(String(200), nullable=True)
    expertise: Mapped[str | None] = mapped_column(Text, nullable=True)
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_external: Mapped[bool] = mapped_column(default=False)
    status: Mapped[str] = mapped_column(String(50), default="active", index=True)

    organization = relationship("Organization", backref="training_instructors")
    employee = relationship("Employee", backref="training_instructors")


class TrainingCourse(TimestampMixin, Base):
    """Training course definitions."""
    __tablename__ = "training_courses"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(String(100), default="general", index=True)
    duration_hours: Mapped[float | None] = mapped_column(Numeric(6, 2), nullable=True)
    max_participants: Mapped[int | None] = mapped_column(Integer, nullable=True)
    credits: Mapped[float | None] = mapped_column(Numeric(6, 2), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="active", index=True)
    cover_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )

    organization = relationship("Organization", backref="training_courses")
    creator = relationship("User", backref="created_training_courses")
    plans = relationship("TrainingPlan", backref="course", lazy="selectin")
    materials = relationship("TrainingMaterial", backref="course", lazy="selectin",
                             order_by="TrainingMaterial.sort_order")


class TrainingPlan(TimestampMixin, Base):
    """Scheduled training sessions / plans."""
    __tablename__ = "training_plans"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    course_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("training_courses.id"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    start_time: Mapped[str | None] = mapped_column(String(10), nullable=True)
    end_time: Mapped[str | None] = mapped_column(String(10), nullable=True)
    location: Mapped[str | None] = mapped_column(String(300), nullable=True)
    instructor_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("training_instructors.id"), nullable=True, index=True
    )
    max_participants: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(
        String(50), default="draft", index=True
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    instructor = relationship("TrainingInstructor", backref="training_plans")


class TrainingMaterial(TimestampMixin, Base):
    """Course materials / resources."""
    __tablename__ = "training_materials"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    course_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("training_courses.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    file_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)


class TrainingRegistration(TimestampMixin, Base):
    """Employee registration for training plans."""
    __tablename__ = "training_registrations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    plan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("training_plans.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    employee_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("employees.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(
        String(50), default="registered", index=True
    )
    registered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    check_in_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    check_out_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    attendance_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    credits_earned: Mapped[float | None] = mapped_column(Numeric(6, 2), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    plan = relationship("TrainingPlan", backref="registrations")
    employee = relationship("Employee", backref="training_registrations")


class TrainingEvaluation(TimestampMixin, Base):
    """Post-training evaluation / survey."""
    __tablename__ = "training_evaluations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    plan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("training_plans.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    employee_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("employees.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    overall_rating: Mapped[int | None] = mapped_column(Integer, nullable=True)
    content_rating: Mapped[int | None] = mapped_column(Integer, nullable=True)
    instructor_rating: Mapped[int | None] = mapped_column(Integer, nullable=True)
    practical_rating: Mapped[int | None] = mapped_column(Integer, nullable=True)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    plan = relationship("TrainingPlan", backref="evaluations")
    employee = relationship("Employee", backref="training_evaluations")


class TrainingCertificate(TimestampMixin, Base):
    """Training certificates issued to employees."""
    __tablename__ = "training_certificates"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    employee_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("employees.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    course_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("training_courses.id"), nullable=False, index=True
    )
    plan_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("training_plans.id"), nullable=True, index=True
    )
    certificate_no: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False
    )
    issued_date: Mapped[date] = mapped_column(Date, nullable=False)
    expiry_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="valid", index=True)
    file_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    employee = relationship("Employee", backref="training_certificates")
    course = relationship("TrainingCourse")
    plan = relationship("TrainingPlan")
