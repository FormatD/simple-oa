"""HR API routes: employees, attendance, leave management."""
from __future__ import annotations

import uuid
from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.deps import get_current_user
from app.core.encryption import decrypt_field, encrypt_field
from app.database import get_db
from app.models.auth import User
from app.models.hr import (
    AttendanceRecord,
    Employee,
    EmployeeContract,
    LeaveBalance,
    LeaveRequest,
    LeaveType,
    Position,
)
from app.models.organization import Department
from app.schemas.auth import APIResponse
from app.schemas.hr import (
    AttendanceRecordResponse,
    AttendanceRecordUpdate,
    AttendanceSummary,
    CheckInRequest,
    CheckOutRequest,
    ContractCreate,
    ContractResponse,
    ContractUpdate,
    EmployeeBasicResponse,
    EmployeeCreate,
    EmployeeDetailResponse,
    EmployeeStatusUpdate,
    EmployeeUpdate,
    LeaveApproveRequest,
    LeaveBalanceResponse,
    LeaveRejectRequest,
    LeaveRequestCreate,
    LeaveRequestResponse,
    LeaveTypeCreate,
    LeaveTypeResponse,
    LeaveTypeUpdate,
    PaginatedAttendanceResponse,
    PaginatedEmployeeResponse,
    PaginatedLeaveRequestResponse,
    PositionCreate,
    PositionResponse,
    PositionUpdate,
)

router = APIRouter(prefix="/hr", tags=["hr"])


# ─── Helper functions ───────────────────────────────────────

async def _get_employee_by_id(db: AsyncSession, emp_id: uuid.UUID) -> Employee:
    result = await db.execute(
        select(Employee)
        .options(selectinload(Employee.user), selectinload(Employee.department),
                 selectinload(Employee.position))
        .where(Employee.id == emp_id, Employee.deleted_at.is_(None))
    )
    emp = result.scalar_one_or_none()
    if not emp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")
    return emp


async def _get_org_employee(db: AsyncSession, org_id: uuid.UUID, current_user: User) -> Employee | None:
    """Get the employee record for the current user in an organization."""
    result = await db.execute(
        select(Employee)
        .options(selectinload(Employee.user), selectinload(Employee.department),
                 selectinload(Employee.position))
        .where(Employee.user_id == current_user.id, Employee.organization_id == org_id,
               Employee.deleted_at.is_(None))
    )
    return result.scalar_one_or_none()


def _emp_to_basic(emp: Employee) -> EmployeeBasicResponse:
    return EmployeeBasicResponse(
        id=str(emp.id),
        employee_no=emp.employee_no,
        user_id=str(emp.user_id),
        display_name=emp.user.display_name if emp.user else None,
        email=emp.user.email if emp.user else None,
        department_id=str(emp.department_id) if emp.department_id else None,
        department_name=emp.department.name if emp.department else None,
        position_id=str(emp.position_id) if emp.position_id else None,
        position_name=emp.position.name if emp.position else None,
        reports_to=str(emp.reports_to) if emp.reports_to else None,
        status=emp.status,
        employment_type=emp.employment_type,
        hire_date=emp.hire_date.isoformat(),
    )


def _emp_to_detail(emp: Employee) -> EmployeeDetailResponse:
    base = _emp_to_basic(emp)
    emergency = decrypt_field(emp.emergency_contact) if emp.emergency_contact else None
    return EmployeeDetailResponse(
        **base.model_dump(),
        organization_id=str(emp.organization_id),
        work_location=emp.work_location,
        emergency_contact=emergency,
        created_at=emp.created_at.isoformat() if emp.created_at else "",
        updated_at=emp.updated_at.isoformat() if emp.updated_at else "",
    )


# CR E1: Resolve the approver from reports_to chain
async def _resolve_approver(db: AsyncSession, employee_id: uuid.UUID) -> uuid.UUID | None:
    """Walk up the reports_to chain to find a valid approver.
    Falls back to the first manager up the chain if direct reports_to is null.
    """
    visited = set()
    current_id = employee_id
    while current_id and current_id not in visited:
        visited.add(current_id)
        result = await db.execute(
            select(Employee).where(Employee.id == current_id, Employee.deleted_at.is_(None))
        )
        emp = result.scalar_one_or_none()
        if not emp:
            return None
        if emp.reports_to and emp.reports_to not in visited:
            # Check if the manager is still active
            mgr_result = await db.execute(
                select(Employee).where(Employee.id == emp.reports_to,
                                       Employee.status == "active",
                                       Employee.deleted_at.is_(None))
            )
            mgr = mgr_result.scalar_one_or_none()
            if mgr:
                return mgr.id
            current_id = emp.reports_to
        else:
            break
    return None


# ─── Positions ──────────────────────────────────────────────

@router.post("/positions", response_model=APIResponse, status_code=status.HTTP_201_CREATED)
async def create_position(
    req: PositionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new HR position."""
    # For simplicity, use the first org the user belongs to
    from app.models.organization import OrganizationMember
    org_result = await db.execute(
        select(OrganizationMember).where(OrganizationMember.user_id == current_user.id)
    )
    membership = org_result.scalar_one_or_none()
    if not membership:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User not in any organization")

    position = Position(
        organization_id=membership.organization_id,
        name=req.name,
        description=req.description,
        sort_order=req.sort_order,
    )
    db.add(position)
    await db.flush()

    return APIResponse(data=PositionResponse(
        id=str(position.id),
        organization_id=str(position.organization_id),
        name=position.name,
        description=position.description,
        sort_order=position.sort_order,
        created_at=position.created_at.isoformat() if position.created_at else "",
        updated_at=position.updated_at.isoformat() if position.updated_at else "",
    ))


@router.get("/positions", response_model=APIResponse)
async def list_positions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List positions for the user's organization."""
    from app.models.organization import OrganizationMember
    org_result = await db.execute(
        select(OrganizationMember).where(OrganizationMember.user_id == current_user.id)
    )
    membership = org_result.scalar_one_or_none()
    if not membership:
        return APIResponse(data=[])

    result = await db.execute(
        select(Position).where(
            Position.organization_id == membership.organization_id,
            Position.deleted_at.is_(None),
        ).order_by(Position.sort_order)
    )
    positions = result.scalars().all()
    return APIResponse(data=[PositionResponse(
        id=str(p.id), organization_id=str(p.organization_id),
        name=p.name, description=p.description,
        sort_order=p.sort_order,
        created_at=p.created_at.isoformat() if p.created_at else "",
        updated_at=p.updated_at.isoformat() if p.updated_at else "",
    ) for p in positions])


# ─── Employees ─────────────────────────────────────────────

@router.post("/employees", response_model=APIResponse, status_code=status.HTTP_201_CREATED)
async def create_employee(
    req: EmployeeCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new employee profile."""
    from app.models.organization import OrganizationMember
    org_result = await db.execute(
        select(OrganizationMember).where(OrganizationMember.user_id == current_user.id)
    )
    membership = org_result.scalar_one_or_none()
    if not membership:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User not in any organization")

    # Check if employee_no already exists
    existing = await db.execute(
        select(Employee).where(Employee.employee_no == req.employee_no,
                               Employee.deleted_at.is_(None))
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Employee number already exists")

    # R6: Encrypt emergency contact before storing
    encrypted_contact = encrypt_field(req.emergency_contact.model_dump()) if req.emergency_contact else None

    emp = Employee(
        organization_id=membership.organization_id,
        user_id=uuid.UUID(req.user_id),
        employee_no=req.employee_no,
        department_id=uuid.UUID(req.department_id) if req.department_id else None,
        position_id=uuid.UUID(req.position_id) if req.position_id else None,
        reports_to=uuid.UUID(req.reports_to) if req.reports_to else None,
        hire_date=req.hire_date,
        employment_type=req.employment_type,
        work_location=req.work_location,
        emergency_contact=encrypted_contact,
    )
    db.add(emp)
    await db.flush()

    # Reload with relationships
    emp = await _get_employee_by_id(db, emp.id)
    return APIResponse(data=_emp_to_detail(emp))


@router.get("/employees", response_model=APIResponse)
async def list_employees(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    department_id: str | None = None,
    position_id: str | None = None,
    status: str | None = None,
    employment_type: str | None = None,
    search: str | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List employees with filtering support."""
    from app.models.organization import OrganizationMember
    org_result = await db.execute(
        select(OrganizationMember).where(OrganizationMember.user_id == current_user.id)
    )
    membership = org_result.scalar_one_or_none()
    if not membership:
        return APIResponse(data={"data": [], "pagination": {"page": page, "page_size": page_size, "total": 0}})

    query = select(Employee).options(
        selectinload(Employee.user), selectinload(Employee.department), selectinload(Employee.position)
    ).where(
        Employee.organization_id == membership.organization_id,
        Employee.deleted_at.is_(None),
    )

    if department_id:
        query = query.where(Employee.department_id == uuid.UUID(department_id))
    if position_id:
        query = query.where(Employee.position_id == uuid.UUID(position_id))
    if status:
        statuses = [s.strip() for s in status.split(",")]
        query = query.where(Employee.status.in_(statuses))
    if employment_type:
        query = query.where(Employee.employment_type == employment_type)
    if search:
        query = query.join(User, Employee.user_id == User.id).where(
            or_(
                Employee.employee_no.ilike(f"%{search}%"),
                User.display_name.ilike(f"%{search}%"),
                User.email.ilike(f"%{search}%"),
            )
        )

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Paginate
    query = query.order_by(Employee.hire_date.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    employees = result.scalars().all()

    return APIResponse(data={
        "data": [_emp_to_basic(e) for e in employees],
        "pagination": {"page": page, "page_size": page_size, "total": total},
    })


@router.get("/employees/{emp_id}", response_model=APIResponse)
async def get_employee(
    emp_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get employee details."""
    emp = await _get_employee_by_id(db, emp_id)
    return APIResponse(data=_emp_to_detail(emp))


@router.put("/employees/{emp_id}", response_model=APIResponse)
async def update_employee(
    emp_id: uuid.UUID,
    req: EmployeeUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update employee information."""
    emp = await _get_employee_by_id(db, emp_id)

    if req.department_id is not None:
        emp.department_id = uuid.UUID(req.department_id)
    if req.position_id is not None:
        emp.position_id = uuid.UUID(req.position_id)
    if req.reports_to is not None:
        emp.reports_to = uuid.UUID(req.reports_to)
    if req.employment_type is not None:
        emp.employment_type = req.employment_type
    if req.work_location is not None:
        emp.work_location = req.work_location
    if req.emergency_contact is not None:
        # R6: Encrypt before storing
        emp.emergency_contact = encrypt_field(req.emergency_contact.model_dump())

    db.add(emp)
    await db.flush()

    emp = await _get_employee_by_id(db, emp_id)
    return APIResponse(data=_emp_to_detail(emp))


@router.put("/employees/{emp_id}/status", response_model=APIResponse)
async def update_employee_status(
    emp_id: uuid.UUID,
    req: EmployeeStatusUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update employee status."""
    emp = await _get_employee_by_id(db, emp_id)
    emp.status = req.status
    db.add(emp)
    await db.flush()
    return APIResponse(data={"message": "Status updated"})


# ─── Employee Contracts ────────────────────────────────────

@router.post("/employees/{emp_id}/contracts", response_model=APIResponse,
             status_code=status.HTTP_201_CREATED)
async def create_contract(
    emp_id: uuid.UUID,
    req: ContractCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Add a contract to an employee."""
    emp = await _get_employee_by_id(db, emp_id)
    contract = EmployeeContract(
        employee_id=emp.id,
        contract_type=req.contract_type,
        start_date=req.start_date,
        end_date=req.end_date,
        probation_months=req.probation_months,
        signing_date=req.signing_date,
        document_url=req.document_url,
    )
    db.add(contract)
    await db.flush()
    return APIResponse(data=ContractResponse(
        id=str(contract.id),
        employee_id=str(contract.employee_id),
        contract_type=contract.contract_type,
        start_date=contract.start_date.isoformat(),
        end_date=contract.end_date.isoformat() if contract.end_date else None,
        probation_months=contract.probation_months,
        signing_date=contract.signing_date.isoformat() if contract.signing_date else None,
        document_url=contract.document_url,
        created_at=contract.created_at.isoformat() if contract.created_at else "",
        updated_at=contract.updated_at.isoformat() if contract.updated_at else "",
    ))


@router.get("/employees/{emp_id}/contracts", response_model=APIResponse)
async def list_contracts(
    emp_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List contracts for an employee."""
    emp = await _get_employee_by_id(db, emp_id)
    result = await db.execute(
        select(EmployeeContract).where(EmployeeContract.employee_id == emp.id)
        .order_by(EmployeeContract.start_date.desc())
    )
    contracts = result.scalars().all()
    return APIResponse(data=[ContractResponse(
        id=str(c.id), employee_id=str(c.employee_id),
        contract_type=c.contract_type,
        start_date=c.start_date.isoformat(),
        end_date=c.end_date.isoformat() if c.end_date else None,
        probation_months=c.probation_months,
        signing_date=c.signing_date.isoformat() if c.signing_date else None,
        document_url=c.document_url,
        created_at=c.created_at.isoformat() if c.created_at else "",
        updated_at=c.updated_at.isoformat() if c.updated_at else "",
    ) for c in contracts])


# ─── Attendance (CR E2: check_in/check_out dual column) ──

@router.post("/attendance/check-in", response_model=APIResponse,
             status_code=status.HTTP_201_CREATED)
async def check_in(
    req: CheckInRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Check in for the current user (GPS location supported)."""
    from app.models.organization import OrganizationMember
    org_result = await db.execute(
        select(OrganizationMember).where(OrganizationMember.user_id == current_user.id)
    )
    membership = org_result.scalar_one_or_none()
    if not membership:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User not in any organization")

    emp = await _get_org_employee(db, membership.organization_id, current_user)
    if not emp:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Employee profile not found")

    today = req.timestamp.date()
    # CR E2: Check if already checked in today
    result = await db.execute(
        select(AttendanceRecord).where(
            AttendanceRecord.employee_id == emp.id,
            AttendanceRecord.date == today,
        )
    )
    record = result.scalar_one_or_none()

    if record:
        if record.check_in_time:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                                detail="Already checked in today")
        record.check_in_time = req.timestamp
        record.check_in_location = req.location
        if req.notes:
            record.notes = req.notes
    else:
        record = AttendanceRecord(
            employee_id=emp.id,
            date=today,
            check_in_time=req.timestamp,
            check_in_location=req.location,
            notes=req.notes,
        )
        db.add(record)

    await db.flush()
    return APIResponse(data=_attendance_to_response(record))


@router.post("/attendance/check-out", response_model=APIResponse)
async def check_out(
    req: CheckOutRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Check out for the current user."""
    from app.models.organization import OrganizationMember
    org_result = await db.execute(
        select(OrganizationMember).where(OrganizationMember.user_id == current_user.id)
    )
    membership = org_result.scalar_one_or_none()
    if not membership:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User not in any organization")

    emp = await _get_org_employee(db, membership.organization_id, current_user)
    if not emp:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Employee profile not found")

    today = req.timestamp.date()
    result = await db.execute(
        select(AttendanceRecord).where(
            AttendanceRecord.employee_id == emp.id,
            AttendanceRecord.date == today,
        )
    )
    record = result.scalar_one_or_none()

    if not record or not record.check_in_time:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Must check in before check out")

    if record.check_out_time:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                            detail="Already checked out today")

    record.check_out_time = req.timestamp
    record.check_out_location = req.location
    if req.notes:
        record.notes = (record.notes or "") + ("; " + req.notes if record.notes else req.notes)

    # Auto-calculate status
    if not record.status or record.status == "present":
        # Could add late detection logic here based on configured work hours
        pass

    db.add(record)
    await db.flush()
    return APIResponse(data=_attendance_to_response(record))


@router.get("/attendance", response_model=APIResponse)
async def list_attendance(
    employee_id: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    status: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List attendance records with filtering."""
    from app.models.organization import OrganizationMember
    org_result = await db.execute(
        select(OrganizationMember).where(OrganizationMember.user_id == current_user.id)
    )
    membership = org_result.scalar_one_or_none()
    if not membership:
        return APIResponse(data={"data": [], "pagination": {"page": page, "page_size": page_size, "total": 0}})

    emp = await _get_org_employee(db, membership.organization_id, current_user)
    if not emp:
        return APIResponse(data={"data": [], "pagination": {"page": page, "page_size": page_size, "total": 0}})

    query = select(AttendanceRecord).where(
        AttendanceRecord.employee_id == (uuid.UUID(employee_id) if employee_id else emp.id)
    )

    if date_from:
        query = query.where(AttendanceRecord.date >= date.fromisoformat(date_from))
    if date_to:
        query = query.where(AttendanceRecord.date <= date.fromisoformat(date_to))
    if status:
        statuses = [s.strip() for s in status.split(",")]
        query = query.where(AttendanceRecord.status.in_(statuses))

    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    query = query.order_by(AttendanceRecord.date.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    records = result.scalars().all()

    return APIResponse(data={
        "data": [_attendance_to_response(r) for r in records],
        "pagination": {"page": page, "page_size": page_size, "total": total},
    })


@router.get("/attendance/my", response_model=APIResponse)
async def my_attendance(
    date_from: str | None = None,
    date_to: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get current user's attendance records."""
    from app.models.organization import OrganizationMember
    org_result = await db.execute(
        select(OrganizationMember).where(OrganizationMember.user_id == current_user.id)
    )
    membership = org_result.scalar_one_or_none()
    if not membership:
        return APIResponse(data={"data": [], "pagination": {"page": page, "page_size": page_size, "total": 0}})

    emp = await _get_org_employee(db, membership.organization_id, current_user)
    if not emp:
        return APIResponse(data={"data": [], "pagination": {"page": page, "page_size": page_size, "total": 0}})

    query = select(AttendanceRecord).where(AttendanceRecord.employee_id == emp.id)
    if date_from:
        query = query.where(AttendanceRecord.date >= date.fromisoformat(date_from))
    if date_to:
        query = query.where(AttendanceRecord.date <= date.fromisoformat(date_to))

    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    query = query.order_by(AttendanceRecord.date.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    records = result.scalars().all()

    return APIResponse(data={
        "data": [_attendance_to_response(r) for r in records],
        "pagination": {"page": page, "page_size": page_size, "total": total},
    })


@router.get("/attendance/summary", response_model=APIResponse)
async def attendance_summary(
    employee_id: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get attendance summary statistics."""
    from app.models.organization import OrganizationMember
    org_result = await db.execute(
        select(OrganizationMember).where(OrganizationMember.user_id == current_user.id)
    )
    membership = org_result.scalar_one_or_none()
    if not membership:
        return APIResponse(data=AttendanceSummary(
            total_days=0, present_days=0, absent_days=0,
            late_days=0, early_leave_days=0, leave_days=0, overtime_hours=0,
        ))

    emp = await _get_org_employee(db, membership.organization_id, current_user)
    if not emp:
        return APIResponse(data=AttendanceSummary(
            total_days=0, present_days=0, absent_days=0,
            late_days=0, early_leave_days=0, leave_days=0, overtime_hours=0,
        ))

    query = select(AttendanceRecord).where(
        AttendanceRecord.employee_id == (uuid.UUID(employee_id) if employee_id else emp.id)
    )
    if date_from:
        query = query.where(AttendanceRecord.date >= date.fromisoformat(date_from))
    if date_to:
        query = query.where(AttendanceRecord.date <= date.fromisoformat(date_to))

    result = await db.execute(query)
    records = result.scalars().all()

    summary = AttendanceSummary(
        total_days=len(records),
        present_days=sum(1 for r in records if r.status == "present"),
        absent_days=sum(1 for r in records if r.status == "absent"),
        late_days=sum(1 for r in records if r.status == "late"),
        early_leave_days=sum(1 for r in records if r.status == "early_leave"),
        leave_days=sum(1 for r in records if r.status == "leave"),
        overtime_hours=sum(float(r.overtime_hours or 0) for r in records),
    )
    return APIResponse(data=summary)


def _attendance_to_response(r: AttendanceRecord) -> AttendanceRecordResponse:
    return AttendanceRecordResponse(
        id=str(r.id),
        employee_id=str(r.employee_id),
        date=r.date.isoformat(),
        check_in_time=r.check_in_time.isoformat() if r.check_in_time else None,
        check_out_time=r.check_out_time.isoformat() if r.check_out_time else None,
        check_in_location=r.check_in_location,
        check_out_location=r.check_out_location,
        status=r.status,
        overtime_hours=float(r.overtime_hours) if r.overtime_hours else None,
        notes=r.notes,
        created_at=r.created_at.isoformat() if r.created_at else "",
        updated_at=r.updated_at.isoformat() if r.updated_at else "",
    )


@router.put("/attendance/{record_id}", response_model=APIResponse)
async def update_attendance_record(
    record_id: uuid.UUID,
    req: AttendanceRecordUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Correct or update an attendance record."""
    result = await db.execute(select(AttendanceRecord).where(AttendanceRecord.id == record_id))
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attendance record not found")

    if req.check_in_time is not None:
        record.check_in_time = req.check_in_time
    if req.check_out_time is not None:
        record.check_out_time = req.check_out_time
    if req.status is not None:
        record.status = req.status
    if req.overtime_hours is not None:
        record.overtime_hours = req.overtime_hours
    if req.notes is not None:
        record.notes = req.notes

    db.add(record)
    await db.flush()
    return APIResponse(data=_attendance_to_response(record))


# ─── Leave Types ──────────────────────────────────────────

@router.post("/leave-types", response_model=APIResponse, status_code=status.HTTP_201_CREATED)
async def create_leave_type(
    req: LeaveTypeCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new leave type (admin only)."""
    from app.models.organization import OrganizationMember
    org_result = await db.execute(
        select(OrganizationMember).where(OrganizationMember.user_id == current_user.id)
    )
    membership = org_result.scalar_one_or_none()
    if not membership:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User not in any organization")

    lt = LeaveType(
        organization_id=membership.organization_id,
        name=req.name,
        paid=req.paid,
        requires_approval=req.requires_approval,
        max_days_per_year=req.max_days_per_year,
        min_notice_hours=req.min_notice_hours,
    )
    db.add(lt)
    await db.flush()
    return APIResponse(data=_leave_type_to_response(lt))


@router.get("/leave-types", response_model=APIResponse)
async def list_leave_types(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List leave types."""
    from app.models.organization import OrganizationMember
    org_result = await db.execute(
        select(OrganizationMember).where(OrganizationMember.user_id == current_user.id)
    )
    membership = org_result.scalar_one_or_none()
    if not membership:
        return APIResponse(data=[])

    result = await db.execute(
        select(LeaveType).where(LeaveType.organization_id == membership.organization_id)
    )
    types = result.scalars().all()
    return APIResponse(data=[_leave_type_to_response(lt) for lt in types])


def _leave_type_to_response(lt: LeaveType) -> LeaveTypeResponse:
    return LeaveTypeResponse(
        id=str(lt.id),
        organization_id=str(lt.organization_id),
        name=lt.name,
        paid=lt.paid,
        requires_approval=lt.requires_approval,
        max_days_per_year=lt.max_days_per_year,
        min_notice_hours=lt.min_notice_hours,
        created_at=lt.created_at.isoformat() if lt.created_at else "",
    )


# ─── Leave Balances ──────────────────────────────────────

@router.get("/leave-balances", response_model=APIResponse)
async def my_leave_balances(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get current user's leave balances."""
    from app.models.organization import OrganizationMember
    org_result = await db.execute(
        select(OrganizationMember).where(OrganizationMember.user_id == current_user.id)
    )
    membership = org_result.scalar_one_or_none()
    if not membership:
        return APIResponse(data=[])

    emp = await _get_org_employee(db, membership.organization_id, current_user)
    if not emp:
        return APIResponse(data=[])

    result = await db.execute(
        select(LeaveBalance)
        .options(selectinload(LeaveBalance.leave_type))
        .where(LeaveBalance.employee_id == emp.id)
    )
    balances = result.scalars().all()

    return APIResponse(data=[LeaveBalanceResponse(
        id=str(b.id),
        employee_id=str(b.employee_id),
        leave_type_id=str(b.leave_type_id),
        leave_type_name=b.leave_type.name if b.leave_type else None,
        total_days=float(b.total_days),
        used_days=float(b.used_days),
        pending_days=float(b.pending_days),
        remaining_days=float(b.total_days) - float(b.used_days) - float(b.pending_days),
        year=b.year,
    ) for b in balances])


@router.get("/leave-balances/{emp_id}", response_model=APIResponse)
async def employee_leave_balances(
    emp_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get an employee's leave balances (for managers)."""
    emp = await _get_employee_by_id(db, emp_id)
    result = await db.execute(
        select(LeaveBalance)
        .options(selectinload(LeaveBalance.leave_type))
        .where(LeaveBalance.employee_id == emp.id)
    )
    balances = result.scalars().all()

    return APIResponse(data=[LeaveBalanceResponse(
        id=str(b.id),
        employee_id=str(b.employee_id),
        leave_type_id=str(b.leave_type_id),
        leave_type_name=b.leave_type.name if b.leave_type else None,
        total_days=float(b.total_days),
        used_days=float(b.used_days),
        pending_days=float(b.pending_days),
        remaining_days=float(b.total_days) - float(b.used_days) - float(b.pending_days),
        year=b.year,
    ) for b in balances])


# ─── Leave Requests (CR E1: approval chain fallback) ────

@router.post("/leave-requests", response_model=APIResponse, status_code=status.HTTP_201_CREATED)
async def create_leave_request(
    req: LeaveRequestCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Submit a leave request. CR E1: auto-resolve approver via reports_to chain."""
    from app.models.organization import OrganizationMember
    org_result = await db.execute(
        select(OrganizationMember).where(OrganizationMember.user_id == current_user.id)
    )
    membership = org_result.scalar_one_or_none()
    if not membership:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User not in any organization")

    emp = await _get_org_employee(db, membership.organization_id, current_user)
    if not emp:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Employee profile not found")

    # Verify leave type exists
    lt_result = await db.execute(
        select(LeaveType).where(LeaveType.id == uuid.UUID(req.leave_type_id))
    )
    lt = lt_result.scalar_one_or_none()
    if not lt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Leave type not found")

    # Calculate total days (including start and end)
    total_days = (req.end_date - req.start_date).days + 1
    if total_days <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid date range")

    # CR E1: Resolve approver through reports_to chain
    approver_id = await _resolve_approver(db, emp.id)

    leave_req = LeaveRequest(
        employee_id=emp.id,
        leave_type_id=uuid.UUID(req.leave_type_id),
        start_date=req.start_date,
        end_date=req.end_date,
        total_days=total_days,
        reason=req.reason,
        status="pending",
        approver_id=approver_id,
    )
    db.add(leave_req)

    # Update pending days in balance
    balance_result = await db.execute(
        select(LeaveBalance).where(
            LeaveBalance.employee_id == emp.id,
            LeaveBalance.leave_type_id == uuid.UUID(req.leave_type_id),
            LeaveBalance.year == req.start_date.year,
        )
    )
    balance = balance_result.scalar_one_or_none()
    if balance:
        balance.pending_days = float(balance.pending_days) + total_days
        db.add(balance)

    await db.flush()
    return APIResponse(data=await _leave_request_to_response(db, leave_req))


@router.get("/leave-requests", response_model=APIResponse)
async def list_leave_requests(
    status_filter: str | None = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List leave requests (current user's, or all if manager)."""
    from app.models.organization import OrganizationMember
    org_result = await db.execute(
        select(OrganizationMember).where(OrganizationMember.user_id == current_user.id)
    )
    membership = org_result.scalar_one_or_none()
    if not membership:
        return APIResponse(data={"data": [], "pagination": {"page": page, "page_size": page_size, "total": 0}})

    emp = await _get_org_employee(db, membership.organization_id, current_user)
    if not emp:
        return APIResponse(data={"data": [], "pagination": {"page": page, "page_size": page_size, "total": 0}})

    query = select(LeaveRequest).options(
        selectinload(LeaveRequest.employee).selectinload(Employee.user),
        selectinload(LeaveRequest.leave_type),
        selectinload(LeaveRequest.approver),
    ).where(
        or_(
            LeaveRequest.employee_id == emp.id,
            LeaveRequest.approver_id == emp.id,
            LeaveRequest.proxy_approver_id == emp.id,
        )
    )

    if status_filter:
        statuses = [s.strip() for s in status_filter.split(",")]
        query = query.where(LeaveRequest.status.in_(statuses))

    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    query = query.order_by(LeaveRequest.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    requests = result.scalars().all()

    results = []
    for lr in requests:
        results.append(await _leave_request_to_response(db, lr))

    return APIResponse(data={
        "data": results,
        "pagination": {"page": page, "page_size": page_size, "total": total},
    })


@router.get("/leave-requests/pending", response_model=APIResponse)
async def list_pending_approvals(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List leave requests pending my approval."""
    from app.models.organization import OrganizationMember
    org_result = await db.execute(
        select(OrganizationMember).where(OrganizationMember.user_id == current_user.id)
    )
    membership = org_result.scalar_one_or_none()
    if not membership:
        return APIResponse(data={"data": [], "pagination": {"page": page, "page_size": page_size, "total": 0}})

    emp = await _get_org_employee(db, membership.organization_id, current_user)
    if not emp:
        return APIResponse(data={"data": [], "pagination": {"page": page, "page_size": page_size, "total": 0}})

    query = select(LeaveRequest).options(
        selectinload(LeaveRequest.employee).selectinload(Employee.user),
        selectinload(LeaveRequest.leave_type),
    ).where(
        LeaveRequest.status == "pending",
        or_(
            LeaveRequest.approver_id == emp.id,
            LeaveRequest.proxy_approver_id == emp.id,
        )
    )

    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    query = query.order_by(LeaveRequest.created_at.asc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    requests = result.scalars().all()

    results = []
    for lr in requests:
        results.append(await _leave_request_to_response(db, lr))

    return APIResponse(data={
        "data": results,
        "pagination": {"page": page, "page_size": page_size, "total": total},
    })


@router.get("/leave-requests/{req_id}", response_model=APIResponse)
async def get_leave_request(
    req_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get leave request details."""
    result = await db.execute(
        select(LeaveRequest).options(
            selectinload(LeaveRequest.employee).selectinload(Employee.user),
            selectinload(LeaveRequest.leave_type),
            selectinload(LeaveRequest.approver),
        ).where(LeaveRequest.id == req_id)
    )
    lr = result.scalar_one_or_none()
    if not lr:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Leave request not found")

    return APIResponse(data=await _leave_request_to_response(db, lr))


@router.put("/leave-requests/{req_id}/approve", response_model=APIResponse)
async def approve_leave_request(
    req_id: uuid.UUID,
    req: LeaveApproveRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Approve a leave request (approver only)."""
    result = await db.execute(
        select(LeaveRequest).options(
            selectinload(LeaveRequest.employee).selectinload(Employee.user),
            selectinload(LeaveRequest.leave_type),
        ).where(LeaveRequest.id == req_id)
    )
    lr = result.scalar_one_or_none()
    if not lr:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Leave request not found")
    if lr.status != "pending":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Leave request is already {lr.status}")

    lr.status = "approved"
    lr.approved_at = datetime.now(timezone.utc)
    db.add(lr)

    # Update balance: move pending to used
    balance_result = await db.execute(
        select(LeaveBalance).where(
            LeaveBalance.employee_id == lr.employee_id,
            LeaveBalance.leave_type_id == lr.leave_type_id,
            LeaveBalance.year == lr.start_date.year,
        )
    )
    balance = balance_result.scalar_one_or_none()
    if balance:
        balance.pending_days = max(0, float(balance.pending_days) - float(lr.total_days))
        balance.used_days = float(balance.used_days) + float(lr.total_days)
        db.add(balance)

    await db.flush()
    return APIResponse(data=await _leave_request_to_response(db, lr))


@router.put("/leave-requests/{req_id}/reject", response_model=APIResponse)
async def reject_leave_request(
    req_id: uuid.UUID,
    req: LeaveRejectRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Reject a leave request."""
    result = await db.execute(
        select(LeaveRequest).options(
            selectinload(LeaveRequest.employee).selectinload(Employee.user),
            selectinload(LeaveRequest.leave_type),
        ).where(LeaveRequest.id == req_id)
    )
    lr = result.scalar_one_or_none()
    if not lr:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Leave request not found")
    if lr.status != "pending":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Leave request is already {lr.status}")

    lr.status = "rejected"
    lr.rejection_reason = req.reason
    db.add(lr)

    # Update balance: remove pending days
    balance_result = await db.execute(
        select(LeaveBalance).where(
            LeaveBalance.employee_id == lr.employee_id,
            LeaveBalance.leave_type_id == lr.leave_type_id,
            LeaveBalance.year == lr.start_date.year,
        )
    )
    balance = balance_result.scalar_one_or_none()
    if balance:
        balance.pending_days = max(0, float(balance.pending_days) - float(lr.total_days))
        db.add(balance)

    await db.flush()
    return APIResponse(data=await _leave_request_to_response(db, lr))


@router.delete("/leave-requests/{req_id}", response_model=APIResponse)
async def cancel_leave_request(
    req_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Cancel a leave request (only if pending)."""
    result = await db.execute(
        select(LeaveRequest).where(LeaveRequest.id == req_id)
    )
    lr = result.scalar_one_or_none()
    if not lr:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Leave request not found")
    if lr.status != "pending":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Can only cancel pending requests")

    lr.status = "cancelled"
    db.add(lr)

    # Remove pending days
    balance_result = await db.execute(
        select(LeaveBalance).where(
            LeaveBalance.employee_id == lr.employee_id,
            LeaveBalance.leave_type_id == lr.leave_type_id,
            LeaveBalance.year == lr.start_date.year,
        )
    )
    balance = balance_result.scalar_one_or_none()
    if balance:
        balance.pending_days = max(0, float(balance.pending_days) - float(lr.total_days))
        db.add(balance)

    await db.flush()
    return APIResponse(data={"message": "Leave request cancelled"})


async def _leave_request_to_response(db: AsyncSession, lr: LeaveRequest) -> LeaveRequestResponse:
    """Convert a LeaveRequest to response model with loaded relationships."""
    emp_name = None
    emp_no = None
    if lr.employee and lr.employee.user:
        emp_name = lr.employee.user.display_name
        emp_no = lr.employee.employee_no

    approver_name = None
    if lr.approver and lr.approver.user:
        approver_name = lr.approver.user.display_name

    return LeaveRequestResponse(
        id=str(lr.id),
        employee_id=str(lr.employee_id),
        employee_name=emp_name,
        employee_no=emp_no,
        leave_type_id=str(lr.leave_type_id),
        leave_type_name=lr.leave_type.name if lr.leave_type else None,
        start_date=lr.start_date.isoformat(),
        end_date=lr.end_date.isoformat(),
        total_days=float(lr.total_days),
        reason=lr.reason,
        status=lr.status,
        approver_id=str(lr.approver_id) if lr.approver_id else None,
        approver_name=approver_name,
        proxy_approver_id=str(lr.proxy_approver_id) if lr.proxy_approver_id else None,
        approved_at=lr.approved_at.isoformat() if lr.approved_at else None,
        rejection_reason=lr.rejection_reason,
        created_at=lr.created_at.isoformat() if lr.created_at else "",
        updated_at=lr.updated_at.isoformat() if lr.updated_at else "",
    )
