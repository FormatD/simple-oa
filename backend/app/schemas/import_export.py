"""Data import and report schemas."""
from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, Field


# ─── Data Import ─────────────────────────────────────────

class ImportPreviewRequest(BaseModel):
    import_type: str = Field(..., pattern=r"^(employee|department|position)$")
    rows: list[dict[str, Any]]


class ImportRowPreview(BaseModel):
    row_number: int
    data: dict[str, Any]
    valid: bool
    errors: list[str] = []


class ImportPreviewResponse(BaseModel):
    import_type: str
    filename: str
    total_rows: int
    valid_rows: int
    error_rows: int
    rows: list[ImportRowPreview]


class ImportConfirmRequest(BaseModel):
    import_type: str
    filename: str
    rows: list[dict[str, Any]]


class ImportResultResponse(BaseModel):
    id: str
    import_type: str
    filename: str
    total_rows: int
    success_rows: int
    error_rows: int
    status: str
    errors: list[dict[str, Any]] | None = None
    summary: dict[str, Any] | None = None
    created_at: str


class ImportRecordResponse(BaseModel):
    id: str
    import_type: str
    filename: str
    total_rows: int
    success_rows: int
    error_rows: int
    status: str
    summary: dict[str, Any] | None = None
    imported_by: str
    created_at: str


# ─── Reports ─────────────────────────────────────────────

class DashboardStats(BaseModel):
    total_employees: int
    active_employees: int
    department_count: int
    pending_leave_count: int
    today_attendance_rate: float
    pending_tasks: int
    overdue_tasks: int
    training_count: int


class HeadcountReport(BaseModel):
    department: str
    department_id: str
    headcount: int
    active: int
    resigned: int


class AttendanceSummaryReport(BaseModel):
    period: str
    total_days: int
    total_employees: int
    present_rate: float
    late_rate: float
    absent_rate: float
    avg_overtime_hours: float


class LeaveSummaryReport(BaseModel):
    leave_type: str
    leave_type_id: str
    total_days: float
    approved_days: float
    pending_days: float
    employee_count: int


class ExportRequest(BaseModel):
    report_type: str = Field(..., pattern=r"^(headcount|attendance|leave|employees|training)$")
    format: str = Field("excel", pattern=r"^(excel|pdf)$")
    date_from: date | None = None
    date_to: date | None = None
    department_id: str | None = None
