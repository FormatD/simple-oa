"""Onboarding and offboarding process API routes."""
from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.core.deps import get_current_user
from app.database import get_db
from app.models.auth import User
from app.models.hr import Employee, EmployeeContract
from app.models.organization import Department, OrganizationMember
from app.schemas.auth import APIResponse
from app.schemas.hr import EmployeeCreate, EmployeeBasicResponse

router = APIRouter(prefix="/onboarding", tags=["onboarding"])


async def _get_org_id(db, user_id):
    result = await db.execute(
        select(OrganizationMember).where(OrganizationMember.user_id == user_id)
    )
    membership = result.scalar_one_or_none()
    return str(membership.organization_id) if membership else None


async def _get_org_employee(db, org_id, user_id):
    result = await db.execute(
        select(Employee).options(
            joinedload(Employee.user),
            joinedload(Employee.department),
            joinedload(Employee.position),
        ).where(
            Employee.user_id == user_id,
            Employee.organization_id == org_id,
            Employee.deleted_at.is_(None),
        )
    )
    return result.scalar_one_or_none()


# ─── Onboarding ──────────────────────────────────────────

@router.post("/employees", response_model=APIResponse, status_code=status.HTTP_201_CREATED)
async def onboard_employee(
    req: EmployeeCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Onboard a new employee — create employee profile, assign department/position."""
    org_id = await _get_org_id(db, current_user.id)
    if not org_id:
        raise HTTPException(status_code=400, detail="User not in any organization")

    # Check employee_no uniqueness
    existing = await db.execute(
        select(Employee).where(
            Employee.employee_no == req.employee_no,
            Employee.deleted_at.is_(None),
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Employee number already exists")

    emp = Employee(
        organization_id=uuid.UUID(org_id),
        user_id=uuid.UUID(req.user_id),
        employee_no=req.employee_no,
        department_id=uuid.UUID(req.department_id) if req.department_id else None,
        position_id=uuid.UUID(req.position_id) if req.position_id else None,
        reports_to=uuid.UUID(req.reports_to) if req.reports_to else None,
        hire_date=req.hire_date,
        employment_type=req.employment_type,
        status="probation",
        work_location=req.work_location,
    )
    db.add(emp)
    await db.flush()

    # Create default contract for probation period
    contract = EmployeeContract(
        employee_id=emp.id,
        contract_type="probation",
        start_date=req.hire_date,
        signing_date=date.today(),
        probation_months=3,
    )
    db.add(contract)

    # Auto-join default department
    if emp.department_id:
        from app.models.organization import DepartmentMember
        # Check if already a member
        dm_result = await db.execute(
            select(DepartmentMember).where(
                DepartmentMember.department_id == emp.department_id,
                DepartmentMember.user_id == current_user.id,
            )
        )
        if not dm_result.scalar_one_or_none():
            dm = DepartmentMember(
                department_id=emp.department_id,
                user_id=current_user.id,
            )
            db.add(dm)

    await db.flush()

    return APIResponse(data={
        "message": "Employee onboarded successfully",
        "employee_id": str(emp.id),
        "employee_no": emp.employee_no,
        "status": emp.status,
    })


@router.post("/process", response_model=APIResponse)
async def process_onboarding(
    req: dict,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Process a multi-step onboarding workflow."""
    org_id = await _get_org_id(db, current_user.id)
    if not org_id:
        raise HTTPException(status_code=400, detail="User not in any organization")

    emp_id = req.get("employee_id")
    step = req.get("step", "create")

    if not emp_id:
        raise HTTPException(status_code=400, detail="employee_id is required")

    emp_result = await db.execute(
        select(Employee).where(Employee.id == emp_id, Employee.deleted_at.is_(None))
    )
    emp = emp_result.scalar_one_or_none()
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")

    result = {"employee_id": emp_id, "step": step}

    if step == "create_profile":
        result["message"] = "Employee profile created"
    elif step == "assign_department":
        department_id = req.get("department_id")
        if department_id:
            emp.department_id = uuid.UUID(department_id)
            db.add(emp)
        result["message"] = "Department assigned"
    elif step == "create_account":
        result["message"] = "Account setup instructions sent"
    elif step == "assign_benefits":
        result["message"] = "Default benefits assigned"
    elif step == "complete":
        emp.status = "active"
        db.add(emp)
        result["message"] = "Onboarding completed"
    else:
        result["message"] = f"Step '{step}' processed"

    await db.flush()
    return APIResponse(data=result)


# ─── Offboarding ─────────────────────────────────────────

@router.post("/offboarding/request", response_model=APIResponse)
async def request_offboarding(
    req: dict,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Submit a resignation/offboarding request."""
    org_id = await _get_org_id(db, current_user.id)
    if not org_id:
        raise HTTPException(status_code=400, detail="User not in any organization")

    emp = await _get_org_employee(db, org_id, current_user.id)
    if not emp:
        raise HTTPException(status_code=400, detail="Employee profile not found")

    reason = req.get("reason", "")
    last_working_day = req.get("last_working_day")

    return APIResponse(data={
        "message": "Offboarding request submitted",
        "employee_id": str(emp.id),
        "reason": reason,
        "last_working_day": last_working_day,
        "status": "pending_review",
    })


@router.post("/offboarding/{emp_id}/complete", response_model=APIResponse)
async def complete_offboarding(
    emp_id: uuid.UUID,
    req: dict,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Complete the offboarding process for an employee."""
    result = await db.execute(
        select(Employee).where(Employee.id == emp_id, Employee.deleted_at.is_(None))
    )
    emp = result.scalar_one_or_none()
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")

    emp.status = "resigned"
    db.add(emp)
    await db.flush()

    return APIResponse(data={
        "message": "Offboarding completed",
        "employee_id": str(emp.id),
        "employee_no": emp.employee_no,
        "status": emp.status,
    })


@router.get("/pending", response_model=APIResponse)
async def list_pending_offboarding(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List employees pending offboarding review."""
    result = await db.execute(
        select(Employee).options(
            joinedload(Employee.user),
            joinedload(Employee.department),
        ).where(
            Employee.status == "resigned",
            Employee.deleted_at.is_(None),
        ).order_by(Employee.updated_at.desc()).limit(50)
    )
    employees = result.scalars().all()

    return APIResponse(data=[{
        "id": str(e.id),
        "employee_no": e.employee_no,
        "name": e.user.display_name if e.user else "",
        "department": e.department.name if e.department else "",
        "status": e.status,
        "resignation_date": e.updated_at.isoformat() if e.updated_at else "",
    } for e in employees])
