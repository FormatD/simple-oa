"""Data import API routes."""
from __future__ import annotations

import csv
import io
import json
import uuid
from datetime import date, datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form, status
from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.core.deps import get_current_user
from app.database import get_db
from app.models.auth import User
from app.models.hr import Employee, Position
from app.models.import_record import ImportRecord
from app.models.organization import Department, OrganizationMember
from app.core.encryption import encrypt_field
from app.schemas.auth import APIResponse
from app.schemas.import_export import (
    ImportConfirmRequest,
    ImportPreviewResponse,
    ImportRecordResponse,
    ImportResultResponse,
    ImportRowPreview,
)

router = APIRouter(prefix="/imports", tags=["imports"])


async def _get_org_id(db: AsyncSession, user_id: Any) -> str | None:
    result = await db.execute(
        select(OrganizationMember).where(OrganizationMember.user_id == user_id)
    )
    membership = result.scalar_one_or_none()
    return str(membership.organization_id) if membership else None


def _parse_csv(content: str) -> list[dict[str, str]]:
    """Parse CSV content into a list of dicts."""
    reader = csv.DictReader(io.StringIO(content))
    return [dict(row) for row in reader]


def _validate_employee_row(row: dict, row_num: int) -> list[str]:
    """Validate a single employee import row."""
    errors = []
    if not row.get("employee_no"):
        errors.append(f"Row {row_num}: employee_no is required")
    if not row.get("email"):
        errors.append(f"Row {row_num}: email is required")
    if not row.get("display_name"):
        errors.append(f"Row {row_num}: display_name is required")
    if not row.get("hire_date"):
        errors.append(f"Row {row_num}: hire_date is required")
    return errors


def _validate_department_row(row: dict, row_num: int) -> list[str]:
    """Validate a single department import row."""
    errors = []
    if not row.get("name"):
        errors.append(f"Row {row_num}: name is required")
    return errors


def _validate_position_row(row: dict, row_num: int) -> list[str]:
    """Validate a single position import row."""
    errors = []
    if not row.get("name"):
        errors.append(f"Row {row_num}: name is required")
    return errors


@router.post("/preview", response_model=APIResponse)
async def preview_import(
    import_type: str = Form(...),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Preview imported data before committing."""
    org_id = await _get_org_id(db, current_user.id)
    if not org_id:
        raise HTTPException(status_code=400, detail="User not in any organization")

    content = await file.read()
    try:
        text = content.decode("utf-8-sig")
        rows = _parse_csv(text)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse file: {str(e)}")

    if not rows:
        raise HTTPException(status_code=400, detail="File is empty")

    validator = {
        "employee": _validate_employee_row,
        "department": _validate_department_row,
        "position": _validate_position_row,
    }.get(import_type)

    if not validator:
        raise HTTPException(status_code=400, detail=f"Unknown import type: {import_type}")

    preview_rows = []
    valid_count = 0
    for i, row in enumerate(rows, start=1):
        errors = validator(row, i)
        is_valid = len(errors) == 0
        if is_valid:
            valid_count += 1
        preview_rows.append(ImportRowPreview(
            row_number=i,
            data=row,
            valid=is_valid,
            errors=errors,
        ))

    return APIResponse(data=ImportPreviewResponse(
        import_type=import_type,
        filename=file.filename or "unknown",
        total_rows=len(rows),
        valid_rows=valid_count,
        error_rows=len(rows) - valid_count,
        rows=preview_rows,
    ))


@router.post("/confirm", response_model=APIResponse)
async def confirm_import(
    req: ImportConfirmRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Confirm and execute data import."""
    org_id = await _get_org_id(db, current_user.id)
    org_uuid = uuid.UUID(org_id) if org_id else None
    if not org_uuid:
        raise HTTPException(status_code=400, detail="User not in any organization")

    success_rows = 0
    error_rows = 0
    row_errors: list[dict[str, Any]] = []
    import_summary: dict[str, Any] = {}

    record = ImportRecord(
        organization_id=org_uuid,
        import_type=req.import_type,
        filename=req.filename,
        total_rows=len(req.rows),
        status="processing",
        imported_by=current_user.id,
    )
    db.add(record)
    await db.flush()

    try:
        if req.import_type == "employee":
            for i, row in enumerate(req.rows, start=1):
                try:
                    # Find or create user placeholder
                    email = row.get("email", "")
                    display_name = row.get("display_name", row.get("name", email))

                    # Check employee_no uniqueness
                    existing = await db.execute(
                        select(Employee).where(
                            Employee.employee_no == row.get("employee_no"),
                            Employee.deleted_at.is_(None),
                        )
                    )
                    if existing.scalar_one_or_none():
                        row_errors.append({"row": i, "error": f"Employee number {row.get('employee_no')} already exists"})
                        error_rows += 1
                        continue

                    # Find department by name
                    dept_id = None
                    if row.get("department"):
                        dept_result = await db.execute(
                            select(Department).where(
                                Department.organization_id == org_uuid,
                                Department.name == row["department"],
                                Department.deleted_at.is_(None),
                            )
                        )
                        dept = dept_result.scalar_one_or_none()
                        if dept:
                            dept_id = dept.id

                    # Find position by name
                    pos_id = None
                    if row.get("position"):
                        pos_result = await db.execute(
                            select(Position).where(
                                Position.organization_id == org_uuid,
                                Position.name == row["position"],
                                Position.deleted_at.is_(None),
                            )
                        )
                        pos = pos_result.scalar_one_or_none()
                        if pos:
                            pos_id = pos.id

                    emp = Employee(
                        organization_id=org_uuid,
                        user_id=current_user.id,
                        employee_no=row.get("employee_no", f"IMP-{uuid.uuid4().hex[:8].upper()}"),
                        department_id=dept_id,
                        position_id=pos_id,
                        hire_date=datetime.strptime(row.get("hire_date", "2026-01-01"), "%Y-%m-%d").date(),
                        employment_type=row.get("employment_type", "full_time"),
                        status=row.get("status", "active"),
                        work_location=row.get("work_location"),
                    )
                    db.add(emp)
                    success_rows += 1
                except Exception as e:
                    row_errors.append({"row": i, "error": str(e)})
                    error_rows += 1

        elif req.import_type == "department":
            for i, row in enumerate(req.rows, start=1):
                try:
                    # Check for duplicate name
                    existing = await db.execute(
                        select(Department).where(
                            Department.organization_id == org_uuid,
                            Department.name == row.get("name"),
                            Department.deleted_at.is_(None),
                        )
                    )
                    if existing.scalar_one_or_none():
                        row_errors.append({"row": i, "error": f"Department '{row.get('name')}' already exists"})
                        error_rows += 1
                        continue

                    dept = Department(
                        organization_id=org_uuid,
                        name=row.get("name", ""),
                    )
                    # Handle parent relationship
                    if row.get("parent_name"):
                        parent_result = await db.execute(
                            select(Department).where(
                                Department.organization_id == org_uuid,
                                Department.name == row["parent_name"],
                                Department.deleted_at.is_(None),
                            )
                        )
                        parent = parent_result.scalar_one_or_none()
                        if parent:
                            dept.parent_id = parent.id

                    db.add(dept)
                    success_rows += 1
                except Exception as e:
                    row_errors.append({"row": i, "error": str(e)})
                    error_rows += 1

        elif req.import_type == "position":
            for i, row in enumerate(req.rows, start=1):
                try:
                    pos = Position(
                        organization_id=org_uuid,
                        name=row.get("name", ""),
                        description=row.get("description"),
                        sort_order=int(row.get("sort_order", 0)),
                    )
                    db.add(pos)
                    success_rows += 1
                except Exception as e:
                    row_errors.append({"row": i, "error": str(e)})
                    error_rows += 1

        import_summary = {
            "import_type": req.import_type,
            "total_rows": len(req.rows),
            "success_rows": success_rows,
            "error_rows": error_rows,
        }

        record.success_rows = success_rows
        record.error_rows = error_rows
        record.status = "completed" if error_rows == 0 else "completed_with_errors"
        record.errors = {"rows": row_errors} if row_errors else None
        record.summary = import_summary
        record.completed_at = datetime.now(timezone.utc)
        db.add(record)
        await db.flush()

    except Exception as e:
        record.status = "failed"
        record.errors = {"error": str(e)}
        db.add(record)
        await db.flush()
        raise HTTPException(status_code=500, detail=f"Import failed: {str(e)}")

    return APIResponse(data=ImportResultResponse(
        id=str(record.id),
        import_type=record.import_type,
        filename=record.filename,
        total_rows=record.total_rows,
        success_rows=record.success_rows,
        error_rows=record.error_rows,
        status=record.status,
        errors=[{"row": e["row"], "error": e["error"]} for e in row_errors] if row_errors else None,
        summary=import_summary,
        created_at=record.created_at.isoformat() if record.created_at else "",
    ))


@router.get("/records", response_model=APIResponse)
async def list_import_records(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List import records."""
    org_id = await _get_org_id(db, current_user.id)
    if not org_id:
        return APIResponse(data={"data": [], "pagination": {"page": page, "page_size": page_size, "total": 0}})

    query = select(ImportRecord).where(
        ImportRecord.organization_id == org_id,
    ).order_by(ImportRecord.created_at.desc())

    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    records = result.scalars().all()

    return APIResponse(data={
        "data": [ImportRecordResponse(
            id=str(r.id),
            import_type=r.import_type,
            filename=r.filename,
            total_rows=r.total_rows,
            success_rows=r.success_rows,
            error_rows=r.error_rows,
            status=r.status,
            summary=r.summary,
            imported_by=str(r.imported_by),
            created_at=r.created_at.isoformat() if r.created_at else "",
        ) for r in records],
        "pagination": {"page": page, "page_size": page_size, "total": total},
    })
