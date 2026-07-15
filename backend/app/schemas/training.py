"""Training module Pydantic schemas."""
from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, Field


# ─── Training Instructors ─────────────────────────────

class InstructorCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    employee_id: str | None = None
    title: str | None = None
    expertise: str | None = None
    bio: str | None = None
    phone: str | None = None
    email: str | None = None
    is_external: bool = False


class InstructorUpdate(BaseModel):
    name: str | None = Field(None, max_length=200)
    employee_id: str | None = None
    title: str | None = None
    expertise: str | None = None
    bio: str | None = None
    phone: str | None = None
    email: str | None = None
    is_external: bool | None = None
    status: str | None = None


class InstructorResponse(BaseModel):
    id: str
    organization_id: str
    name: str
    employee_id: str | None = None
    title: str | None = None
    expertise: str | None = None
    bio: str | None = None
    phone: str | None = None
    email: str | None = None
    is_external: bool
    status: str
    created_at: str
    updated_at: str


# ─── Training Courses ─────────────────────────────────

class CourseCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=300)
    description: str | None = None
    category: str = "general"
    duration_hours: float | None = None
    max_participants: int | None = None
    credits: float | None = None
    cover_url: str | None = None


class CourseUpdate(BaseModel):
    title: str | None = Field(None, max_length=300)
    description: str | None = None
    category: str | None = None
    duration_hours: float | None = None
    max_participants: int | None = None
    credits: float | None = None
    cover_url: str | None = None
    status: str | None = None


class CourseResponse(BaseModel):
    id: str
    organization_id: str
    title: str
    description: str | None = None
    category: str
    duration_hours: float | None = None
    max_participants: int | None = None
    credits: float | None = None
    status: str
    cover_url: str | None = None
    created_by: str
    created_at: str
    updated_at: str


class CourseDetailResponse(CourseResponse):
    """Course detail with nested plans and materials."""
    plans: list[PlanBriefResponse] = []
    materials: list[MaterialResponse] = []


# ─── Training Plans ───────────────────────────────────

class PlanCreate(BaseModel):
    course_id: str
    title: str = Field(..., min_length=1, max_length=300)
    start_date: date
    end_date: date
    start_time: str | None = None
    end_time: str | None = None
    location: str | None = None
    instructor_id: str | None = None
    max_participants: int | None = None
    notes: str | None = None


class PlanUpdate(BaseModel):
    title: str | None = Field(None, max_length=300)
    start_date: date | None = None
    end_date: date | None = None
    start_time: str | None = None
    end_time: str | None = None
    location: str | None = None
    instructor_id: str | None = None
    max_participants: int | None = None
    status: str | None = None
    notes: str | None = None


class PlanResponse(BaseModel):
    id: str
    course_id: str
    course_title: str | None = None
    title: str
    start_date: str
    end_date: str
    start_time: str | None = None
    end_time: str | None = None
    location: str | None = None
    instructor_id: str | None = None
    instructor_name: str | None = None
    max_participants: int | None = None
    registered_count: int = 0
    status: str
    notes: str | None = None
    created_at: str
    updated_at: str


class PlanBriefResponse(BaseModel):
    id: str
    title: str
    start_date: str
    end_date: str
    status: str


# ─── Training Materials ───────────────────────────────

class MaterialCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=300)
    type: str = Field(..., pattern=r"^(ppt|pdf|video|document|link|other)$")
    file_url: str | None = None
    description: str | None = None
    sort_order: int = 0


class MaterialUpdate(BaseModel):
    name: str | None = Field(None, max_length=300)
    type: str | None = None
    file_url: str | None = None
    description: str | None = None
    sort_order: int | None = None


class MaterialResponse(BaseModel):
    id: str
    course_id: str
    name: str
    type: str
    file_url: str | None = None
    description: str | None = None
    sort_order: int
    created_at: str
    updated_at: str


# ─── Training Registrations ──────────────────────────

class RegistrationCreate(BaseModel):
    plan_id: str


class RegistrationCheckIn(BaseModel):
    notes: str | None = None


class RegistrationCheckOut(BaseModel):
    notes: str | None = None


class RegistrationUpdate(BaseModel):
    status: str | None = None
    attendance_status: str | None = None
    credits_earned: float | None = None
    notes: str | None = None


class RegistrationResponse(BaseModel):
    id: str
    plan_id: str
    plan_title: str | None = None
    employee_id: str
    employee_name: str | None = None
    employee_no: str | None = None
    status: str
    registered_at: str
    check_in_time: str | None = None
    check_out_time: str | None = None
    attendance_status: str | None = None
    credits_earned: float | None = None
    notes: str | None = None
    created_at: str
    updated_at: str


# ─── Training Evaluations ────────────────────────────

class EvaluationCreate(BaseModel):
    plan_id: str
    overall_rating: int = Field(..., ge=1, le=5)
    content_rating: int | None = Field(None, ge=1, le=5)
    instructor_rating: int | None = Field(None, ge=1, le=5)
    practical_rating: int | None = Field(None, ge=1, le=5)
    comment: str | None = None


class EvaluationResponse(BaseModel):
    id: str
    plan_id: str
    plan_title: str | None = None
    employee_id: str
    employee_name: str | None = None
    overall_rating: int | None = None
    content_rating: int | None = None
    instructor_rating: int | None = None
    practical_rating: int | None = None
    comment: str | None = None
    submitted_at: str


# ─── Training Certificates ───────────────────────────

class CertificateIssue(BaseModel):
    employee_id: str
    course_id: str
    plan_id: str | None = None
    issued_date: date
    expiry_date: date | None = None
    file_url: str | None = None


class CertificateResponse(BaseModel):
    id: str
    employee_id: str
    employee_name: str | None = None
    employee_no: str | None = None
    course_id: str
    course_title: str | None = None
    plan_id: str | None = None
    plan_title: str | None = None
    certificate_no: str
    issued_date: str
    expiry_date: str | None = None
    status: str
    file_url: str | None = None
    created_at: str
    updated_at: str


# ─── Paginated Responses ─────────────────────────────

class CertificateUpdate(BaseModel):
    """For updating certificate status or fields."""
    status: str | None = Field(None, pattern=r"^(valid|expired|revoked)$")
    expiry_date: date | None = None
    file_url: str | None = None


class PaginatedCourseResponse(BaseModel):
    data: list[CourseResponse]
    pagination: dict[str, int]


class PaginatedPlanResponse(BaseModel):
    data: list[PlanResponse]
    pagination: dict[str, int]


class PaginatedRegistrationResponse(BaseModel):
    data: list[RegistrationResponse]
    pagination: dict[str, int]


class PaginatedCertificateResponse(BaseModel):
    data: list[CertificateResponse]
    pagination: dict[str, int]


class PaginatedInstructorResponse(BaseModel):
    data: list[InstructorResponse]
    pagination: dict[str, int]
