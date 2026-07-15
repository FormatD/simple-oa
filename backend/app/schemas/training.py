"""Training module schemas."""
from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, Field


class TrainingCourseCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    description: str | None = None
    instructor: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    duration_hours: float | None = None
    max_participants: int | None = None
    location: str | None = None
    category: str | None = None


class TrainingCourseUpdate(BaseModel):
    title: str | None = Field(None, max_length=500)
    description: str | None = None
    instructor: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    duration_hours: float | None = None
    max_participants: int | None = None
    location: str | None = None
    status: str | None = None
    category: str | None = None


class TrainingCourseResponse(BaseModel):
    id: str
    organization_id: str
    title: str
    description: str | None = None
    instructor: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    duration_hours: float | None = None
    max_participants: int | None = None
    location: str | None = None
    status: str
    category: str | None = None
    enrollment_count: int = 0
    created_by: str
    created_at: str
    updated_at: str


class TrainingEnrollRequest(BaseModel):
    employee_ids: list[str] = Field(..., min_length=1)


class TrainingEnrollmentUpdate(BaseModel):
    attended: bool | None = None
    score: float | None = None
    feedback: str | None = None
    status: str | None = None


class TrainingEnrollmentResponse(BaseModel):
    id: str
    course_id: str
    employee_id: str
    employee_name: str | None = None
    employee_no: str | None = None
    status: str
    attended: bool | None = None
    score: float | None = None
    feedback: str | None = None
    completed_at: str | None = None
    created_at: str
