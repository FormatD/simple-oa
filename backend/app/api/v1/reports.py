"""Reports and statistics API routes."""
from __future__ import annotations

import io
from datetime import date, datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.core.deps import get_current_user
from app.database import get_db
from app.models.auth import User
from app.models.hr import AttendanceRecord, Employee, LeaveRequest, LeaveType
from app.models.organization import Department, OrganizationMember
from app.models.task import Task
from app.models.training import TrainingCourse
from app.schemas.auth import APIResponse
from app.schemas.import_export import (
    AttendanceSummaryReport,
    DashboardStats,
    ExportRequest,
    HeadcountReport,
    LeaveSummaryReport,
)

router = APIRouter(prefix="/reports", tags=["reports"])


async def _get_org_id(db: AsyncSession, user_id: Any) -> str | None:
    result = await db.execute(
        select(OrganizationMember).where(OrganizationMember.user_id == user_id)
    )
    membership = result.scalar_one_or_none()
    return str(membership.organization_id) if membership else None


@router.get("/dashboard", response_model=APIResponse)
async def get_dashboard_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get aggregate dashboard statistics."""
    org_id = await _get_org_id(db, current_user.id)
    if not org_id:
        return APIResponse(data=DashboardStats(
            total_employees=0, active_employees=0, department_count=0,
            pending_leave_count=0, today_attendance_rate=0.0,
            pending_tasks=0, overdue_tasks=0, training_count=0,
        ))

    # Employee counts
    emp_result = await db.execute(
        select(func.count()).select_from(Employee)
        .where(Employee.organization_id == org_id, Employee.deleted_at.is_(None))
    )
    total_employees = emp_result.scalar() or 0

    active_result = await db.execute(
        select(func.count()).select_from(Employee)
        .where(Employee.organization_id == org_id, Employee.status == "active",
               Employee.deleted_at.is_(None))
    )
    active_employees = active_result.scalar() or 0

    # Department count
    dept_result = await db.execute(
        select(func.count()).select_from(Department)
        .where(Department.organization_id == org_id, Department.deleted_at.is_(None))
    )
    department_count = dept_result.scalar() or 0

    # Pending leave requests
    leave_result = await db.execute(
        select(func.count()).select_from(LeaveRequest)
        .where(LeaveRequest.status == "pending")
    )
    pending_leave_count = leave_result.scalar() or 0

    # Today attendance rate
    today = date.today()
    att_result = await db.execute(
        select(func.count()).select_from(AttendanceRecord)
        .where(AttendanceRecord.date == today)
    )
    today_total = att_result.scalar() or 0

    att_present = await db.execute(
        select(func.count()).select_from(AttendanceRecord)
        .where(AttendanceRecord.date == today,
               AttendanceRecord.status == "present")
    )
    today_present = att_present.scalar() or 0
    today_attendance_rate = (today_present / today_total * 100) if today_total > 0 else 0.0

    # Task counts
    task_pending = await db.execute(
        select(func.count()).select_from(Task)
        .where(Task.organization_id == org_id,
               Task.deleted_at.is_(None),
               Task.status.in_(["todo", "in_progress"]))
    )
    pending_tasks = task_pending.scalar() or 0

    task_overdue = await db.execute(
        select(func.count()).select_from(Task)
        .where(Task.organization_id == org_id,
               Task.deleted_at.is_(None),
               Task.due_date.isnot(None),
               Task.due_date < date.today(),
               Task.status.in_(["todo", "in_progress"]))
    )
    overdue_tasks = task_overdue.scalar() or 0

    # Training count
    training_result = await db.execute(
        select(func.count()).select_from(TrainingCourse)
        .where(TrainingCourse.organization_id == org_id)
    )
    training_count = training_result.scalar() or 0

    return APIResponse(data=DashboardStats(
        total_employees=total_employees,
        active_employees=active_employees,
        department_count=department_count,
        pending_leave_count=pending_leave_count,
        today_attendance_rate=round(today_attendance_rate, 1),
        pending_tasks=pending_tasks,
        overdue_tasks=overdue_tasks,
        training_count=training_count,
    ))


@router.get("/hr/headcount", response_model=APIResponse)
async def get_headcount_report(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get headcount statistics by department."""
    org_id = await _get_org_id(db, current_user.id)
    if not org_id:
        return APIResponse(data=[])

    depts = await db.execute(
        select(Department).where(
            Department.organization_id == org_id,
            Department.deleted_at.is_(None),
        )
    )
    departments = depts.scalars().all()

    report = []
    for dept in departments:
        headcount = await db.execute(
            select(func.count()).select_from(Employee)
            .where(Employee.department_id == dept.id,
                   Employee.deleted_at.is_(None))
        )
        total = headcount.scalar() or 0

        active = await db.execute(
            select(func.count()).select_from(Employee)
            .where(Employee.department_id == dept.id,
                   Employee.status == "active",
                   Employee.deleted_at.is_(None))
        )
        active_count = active.scalar() or 0

        resigned = await db.execute(
            select(func.count()).select_from(Employee)
            .where(Employee.department_id == dept.id,
                   Employee.status == "resigned",
                   Employee.deleted_at.is_(None))
        )
        resigned_count = resigned.scalar() or 0

        report.append(HeadcountReport(
            department=dept.name,
            department_id=str(dept.id),
            headcount=total,
            active=active_count,
            resigned=resigned_count,
        ))

    return APIResponse(data=report)


@router.get("/hr/attendance-summary", response_model=APIResponse)
async def get_attendance_summary_report(
    date_from: date | None = None,
    date_to: date | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get attendance summary for a date range."""
    org_id = await _get_org_id(db, current_user.id)
    if not org_id:
        return APIResponse(data=[])

    if not date_to:
        date_to = date.today()
    if not date_from:
        date_from = date_to.replace(day=1)

    status_counts = await db.execute(
        select(
            AttendanceRecord.status,
            func.count().label("count"),
        ).select_from(AttendanceRecord)
        .where(
            AttendanceRecord.date >= date_from,
            AttendanceRecord.date <= date_to,
        )
        .group_by(AttendanceRecord.status)
    )
    counts = {row.status: row.count for row in status_counts}

    total = sum(counts.values()) or 1
    present = counts.get("present", 0)
    late = counts.get("late", 0)
    absent = counts.get("absent", 0)

    avg_ot = await db.execute(
        select(func.avg(AttendanceRecord.overtime_hours))
        .where(
            AttendanceRecord.date >= date_from,
            AttendanceRecord.date <= date_to,
        )
    )
    avg_hours = float(avg_ot.scalar() or 0)

    return APIResponse(data=AttendanceSummaryReport(
        period=f"{date_from.isoformat()}/{date_to.isoformat()}",
        total_days=(date_to - date_from).days + 1,
        total_employees=total,
        present_rate=round(present / total * 100, 1),
        late_rate=round(late / total * 100, 1),
        absent_rate=round(absent / total * 100, 1),
        avg_overtime_hours=round(avg_hours, 1),
    ))


@router.get("/hr/leave-summary", response_model=APIResponse)
async def get_leave_summary_report(
    year: int | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get leave summary by type for a given year."""
    org_id = await _get_org_id(db, current_user.id)
    if not org_id:
        return APIResponse(data=[])

    if not year:
        year = date.today().year

    leave_types = await db.execute(
        select(LeaveType).where(LeaveType.organization_id == org_id)
    )
    types = leave_types.scalars().all()

    report = []
    for lt in types:
        stats = await db.execute(
            select(
                func.sum(LeaveRequest.total_days).label("total"),
                func.count(LeaveRequest.id).label("count"),
            ).where(
                LeaveRequest.leave_type_id == lt.id,
                func.extract("year", LeaveRequest.start_date) == year,
            )
        )
        row = stats.one()
        total_days = float(row.total or 0)

        approved = await db.execute(
            select(func.sum(LeaveRequest.total_days))
            .where(
                LeaveRequest.leave_type_id == lt.id,
                LeaveRequest.status == "approved",
                func.extract("year", LeaveRequest.start_date) == year,
            )
        )
        approved_days = float(approved.scalar() or 0)

        pending = await db.execute(
            select(func.sum(LeaveRequest.total_days))
            .where(
                LeaveRequest.leave_type_id == lt.id,
                LeaveRequest.status == "pending",
                func.extract("year", LeaveRequest.start_date) == year,
            )
        )
        pending_days = float(pending.scalar() or 0)

        report.append(LeaveSummaryReport(
            leave_type=lt.name,
            leave_type_id=str(lt.id),
            total_days=total_days,
            approved_days=approved_days,
            pending_days=pending_days,
            employee_count=row.count or 0,
        ))

    return APIResponse(data=report)


@router.post("/export", response_model=APIResponse)
async def export_data(
    req: ExportRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Export data in the requested format."""
    org_id = await _get_org_id(db, current_user.id)
    if not org_id:
        raise HTTPException(status_code=400, detail="User not in any organization")

    # Build export based on report_type
    export_data: list[dict[str, Any]] = []
    if req.report_type == "employees":
        result = await db.execute(
            select(Employee).options(
                joinedload(Employee.user),
                joinedload(Employee.department),
                joinedload(Employee.position),
            ).where(
                Employee.organization_id == org_id,
                Employee.deleted_at.is_(None),
            )
        )
        employees = result.scalars().all()
        export_data = [{
            "employee_no": e.employee_no,
            "name": e.user.display_name if e.user else "",
            "email": e.user.email if e.user else "",
            "department": e.department.name if e.department else "",
            "position": e.position.name if e.position else "",
            "status": e.status,
            "hire_date": e.hire_date.isoformat() if e.hire_date else "",
        } for e in employees]
    elif req.report_type == "headcount":
        depts = await db.execute(
            select(Department).where(
                Department.organization_id == org_id,
                Department.deleted_at.is_(None),
            )
        )
        for dept in depts.scalars().all():
            total = (await db.execute(
                select(func.count()).select_from(Employee)
                .where(Employee.department_id == dept.id, Employee.deleted_at.is_(None))
            )).scalar() or 0
            export_data.append({
                "department": dept.name,
                "headcount": total,
            })
    elif req.report_type == "training":
        result = await db.execute(
            select(TrainingCourse)
            .where(TrainingCourse.organization_id == org_id)
            .order_by(TrainingCourse.created_at.desc())
        )
        for c in result.scalars().all():
            export_data.append({
                "title": c.title,
                "instructor": c.instructor or "",
                "status": c.status,
                "start_date": c.start_date.isoformat() if c.start_date else "",
                "end_date": c.end_date.isoformat() if c.end_date else "",
                "location": c.location or "",
            })

    filename = f"{req.report_type}_export"
    if req.format == "excel":
        content_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        filename += ".xlsx"
    else:
        content_type = "application/pdf"
        filename += ".pdf"

    return APIResponse(data={
        "filename": filename,
        "content_type": content_type,
        "data": export_data,
    })
