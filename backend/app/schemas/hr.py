"""HR module schemas."""
from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, Field


# ─── Positions ─────────────────────────────────────────

class PositionCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: str | None = None
    sort_order: int = 0


class PositionUpdate(BaseModel):
    name: str | None = Field(None, max_length=200)
    description: str | None = None
    sort_order: int | None = None


class PositionResponse(BaseModel):
    id: str
    organization_id: str
    name: str
    description: str | None = None
    sort_order: int
    created_at: str
    updated_at: str


# ─── Employees ─────────────────────────────────────────

class EmergencyContact(BaseModel):
    name: str
    relationship: str
    phone: str


class EmployeeCreate(BaseModel):
    user_id: str
    employee_no: str = Field(..., min_length=1, max_length=50)
    department_id: str | None = None
    position_id: str | None = None
    reports_to: str | None = None
    hire_date: date
    employment_type: str = "full_time"
    work_location: str | None = None
    emergency_contact: EmergencyContact | None = None


class EmployeeUpdate(BaseModel):
    department_id: str | None = None
    position_id: str | None = None
    reports_to: str | None = None
    employment_type: str | None = None
    work_location: str | None = None
    emergency_contact: EmergencyContact | None = None


class EmployeeBasicResponse(BaseModel):
    id: str
    employee_no: str
    user_id: str
    display_name: str | None = None
    email: str | None = None
    department_id: str | None = None
    department_name: str | None = None
    position_id: str | None = None
    position_name: str | None = None
    reports_to: str | None = None
    status: str
    employment_type: str
    hire_date: str


class EmployeeDetailResponse(EmployeeBasicResponse):
    organization_id: str
    work_location: str | None = None
    emergency_contact: dict | None = None
    created_at: str
    updated_at: str


class EmployeeStatusUpdate(BaseModel):
    status: str = Field(..., pattern=r"^(active|resigned|suspended|probation)$")


# ─── Contracts ─────────────────────────────────────────

class ContractCreate(BaseModel):
    contract_type: str = Field(..., pattern=r"^(probation|fixed|permanent|project)$")
    start_date: date
    end_date: date | None = None
    probation_months: int = 0
    signing_date: date | None = None
    document_url: str | None = None


class ContractUpdate(BaseModel):
    contract_type: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    probation_months: int | None = None
    signing_date: date | None = None
    document_url: str | None = None


class ContractResponse(BaseModel):
    id: str
    employee_id: str
    contract_type: str
    start_date: str
    end_date: str | None = None
    probation_months: int
    signing_date: str | None = None
    document_url: str | None = None
    created_at: str
    updated_at: str


# ─── Attendance ───────────────────────────────────────
# CR E2: check_in/check_out dual column mode

class CheckInRequest(BaseModel):
    timestamp: datetime
    location: dict | None = None  # {"lat": 39.9, "lng": 116.4}
    notes: str | None = None


class CheckOutRequest(BaseModel):
    timestamp: datetime
    location: dict | None = None
    notes: str | None = None


class AttendanceRecordResponse(BaseModel):
    id: str
    employee_id: str
    date: str
    check_in_time: str | None = None
    check_out_time: str | None = None
    check_in_location: dict | None = None
    check_out_location: dict | None = None
    status: str
    overtime_hours: float | None = None
    notes: str | None = None
    created_at: str
    updated_at: str


class AttendanceSummary(BaseModel):
    total_days: int
    present_days: int
    absent_days: int
    late_days: int
    early_leave_days: int
    leave_days: float
    overtime_hours: float


class AttendanceRecordUpdate(BaseModel):
    check_in_time: datetime | None = None
    check_out_time: datetime | None = None
    status: str | None = None
    overtime_hours: float | None = None
    notes: str | None = None


# ─── Leave Types ──────────────────────────────────────

class LeaveTypeCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    paid: bool = False
    requires_approval: bool = True
    max_days_per_year: int | None = None
    min_notice_hours: int = 0


class LeaveTypeUpdate(BaseModel):
    name: str | None = Field(None, max_length=100)
    paid: bool | None = None
    requires_approval: bool | None = None
    max_days_per_year: int | None = None
    min_notice_hours: int | None = None


class LeaveTypeResponse(BaseModel):
    id: str
    organization_id: str
    name: str
    paid: bool
    requires_approval: bool
    max_days_per_year: int | None = None
    min_notice_hours: int
    created_at: str


# ─── Leave Balances ─────────────────────────────────────

class LeaveBalanceResponse(BaseModel):
    id: str
    employee_id: str
    leave_type_id: str
    leave_type_name: str | None = None
    total_days: float
    used_days: float
    pending_days: float
    remaining_days: float
    year: int


# ─── Leave Requests ─────────────────────────────────────
# CR E1: When reports_to is null, auto-escalate

class LeaveRequestCreate(BaseModel):
    leave_type_id: str
    start_date: date
    end_date: date
    reason: str | None = None


class LeaveRequestResponse(BaseModel):
    id: str
    employee_id: str
    employee_name: str | None = None
    employee_no: str | None = None
    leave_type_id: str
    leave_type_name: str | None = None
    start_date: str
    end_date: str
    total_days: float
    reason: str | None = None
    status: str
    approver_id: str | None = None
    approver_name: str | None = None
    proxy_approver_id: str | None = None
    approved_at: str | None = None
    rejection_reason: str | None = None
    created_at: str
    updated_at: str


class LeaveApproveRequest(BaseModel):
    comment: str | None = None


class LeaveRejectRequest(BaseModel):
    reason: str = Field(..., min_length=1)


# ─── Paginated HR Responses ───────────────────────────

class PaginatedEmployeeResponse(BaseModel):
    data: list[EmployeeBasicResponse]
    pagination: dict[str, int]


class PaginatedAttendanceResponse(BaseModel):
    data: list[AttendanceRecordResponse]
    pagination: dict[str, int]


class PaginatedLeaveRequestResponse(BaseModel):
    data: list[LeaveRequestResponse]
    pagination: dict[str, int]
