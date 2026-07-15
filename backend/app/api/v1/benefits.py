"""Benefits management API routes."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.core.deps import get_current_user
from app.database import get_db
from app.models.auth import User
from app.models.hr import Employee
from app.models.organization import OrganizationMember
from app.models.benefits import BenefitItem, EmployeeBenefit, BenefitClaim
from app.schemas.auth import APIResponse
from app.schemas.benefits import (
    BenefitItemCreate,
    BenefitItemResponse,
    BenefitItemUpdate,
    EmployeeBenefitCreate,
    EmployeeBenefitResponse,
    EmployeeBenefitUpdate,
    BenefitClaimCreate,
    BenefitClaimResponse,
)

router = APIRouter(prefix="/benefits", tags=["benefits"])


async def _get_org_id(db, user_id):
    result = await db.execute(
        select(OrganizationMember).where(OrganizationMember.user_id == user_id)
    )
    membership = result.scalar_one_or_none()
    return str(membership.organization_id) if membership else None


# ─── Benefit Items ───────────────────────────────────────

@router.post("/items", response_model=APIResponse, status_code=status.HTTP_201_CREATED)
async def create_benefit_item(
    req: BenefitItemCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a benefit item."""
    org_id = await _get_org_id(db, current_user.id)
    if not org_id:
        raise HTTPException(status_code=400, detail="User not in any organization")

    item = BenefitItem(
        organization_id=uuid.UUID(org_id),
        name=req.name,
        description=req.description,
        category=req.category,
        annual_budget=req.annual_budget,
        created_by=current_user.id,
    )
    db.add(item)
    await db.flush()

    return APIResponse(data=BenefitItemResponse(
        id=str(item.id),
        organization_id=str(item.organization_id),
        name=item.name,
        description=item.description,
        category=item.category,
        is_active=item.is_active,
        annual_budget=float(item.annual_budget) if item.annual_budget else None,
        created_at=item.created_at.isoformat() if item.created_at else "",
        updated_at=item.updated_at.isoformat() if item.updated_at else "",
    ))


@router.get("/items", response_model=APIResponse)
async def list_benefit_items(
    category: str | None = None,
    active_only: bool = Query(False),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List benefit items."""
    org_id = await _get_org_id(db, current_user.id)
    if not org_id:
        return APIResponse(data=[])

    query = select(BenefitItem).where(BenefitItem.organization_id == org_id)
    if category:
        query = query.where(BenefitItem.category == category)
    if active_only:
        query = query.where(BenefitItem.is_active == True)

    query = query.order_by(BenefitItem.created_at.desc())
    result = await db.execute(query)
    items = result.scalars().all()

    return APIResponse(data=[BenefitItemResponse(
        id=str(i.id),
        organization_id=str(i.organization_id),
        name=i.name,
        description=i.description,
        category=i.category,
        is_active=i.is_active,
        annual_budget=float(i.annual_budget) if i.annual_budget else None,
        created_at=i.created_at.isoformat() if i.created_at else "",
        updated_at=i.updated_at.isoformat() if i.updated_at else "",
    ) for i in items])


@router.put("/items/{item_id}", response_model=APIResponse)
async def update_benefit_item(
    item_id: uuid.UUID,
    req: BenefitItemUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a benefit item."""
    result = await db.execute(select(BenefitItem).where(BenefitItem.id == item_id))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Benefit item not found")

    if req.name is not None:
        item.name = req.name
    if req.description is not None:
        item.description = req.description
    if req.category is not None:
        item.category = req.category
    if req.is_active is not None:
        item.is_active = req.is_active
    if req.annual_budget is not None:
        item.annual_budget = req.annual_budget

    db.add(item)
    await db.flush()
    return APIResponse(data={"message": "Benefit item updated"})


# ─── Employee Benefits ──────────────────────────────────

@router.post("/employee-benefits", response_model=APIResponse, status_code=status.HTTP_201_CREATED)
async def assign_employee_benefit(
    req: EmployeeBenefitCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Assign a benefit to the current user's employee profile."""
    org_id = await _get_org_id(db, current_user.id)
    if not org_id:
        raise HTTPException(status_code=400, detail="User not in any organization")

    emp_result = await db.execute(
        select(Employee).where(
            Employee.user_id == current_user.id,
            Employee.organization_id == org_id,
            Employee.deleted_at.is_(None),
        )
    )
    emp = emp_result.scalar_one_or_none()
    if not emp:
        raise HTTPException(status_code=400, detail="Employee profile not found")

    eb = EmployeeBenefit(
        employee_id=emp.id,
        benefit_item_id=uuid.UUID(req.benefit_item_id),
        effective_date=req.effective_date,
        expiry_date=req.expiry_date,
        amount=req.amount,
        details=req.details,
    )
    db.add(eb)
    await db.flush()

    return APIResponse(data={"message": "Benefit assigned", "id": str(eb.id)})


@router.get("/employee-benefits", response_model=APIResponse)
async def list_employee_benefits(
    employee_id: str | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List employee benefit assignments."""
    org_id = await _get_org_id(db, current_user.id)
    if not org_id:
        return APIResponse(data=[])

    query = select(EmployeeBenefit).options(
        joinedload(EmployeeBenefit.benefit_item),
        joinedload(EmployeeBenefit.employee).joinedload(Employee.user),
    )

    if employee_id:
        query = query.where(EmployeeBenefit.employee_id == uuid.UUID(employee_id))
    else:
        emp_result = await db.execute(
            select(Employee).where(
                Employee.user_id == current_user.id,
                Employee.organization_id == org_id,
                Employee.deleted_at.is_(None),
            )
        )
        emp = emp_result.scalar_one_or_none()
        if emp:
            query = query.where(EmployeeBenefit.employee_id == emp.id)
        else:
            return APIResponse(data=[])

    query = query.order_by(EmployeeBenefit.created_at.desc())
    result = await db.execute(query)
    benefits = result.scalars().all()

    return APIResponse(data=[EmployeeBenefitResponse(
        id=str(b.id),
        employee_id=str(b.employee_id),
        employee_name=b.employee.user.display_name if b.employee and b.employee.user else None,
        benefit_item_id=str(b.benefit_item_id),
        benefit_item_name=b.benefit_item.name if b.benefit_item else None,
        effective_date=b.effective_date.isoformat(),
        expiry_date=b.expiry_date.isoformat() if b.expiry_date else None,
        amount=float(b.amount) if b.amount else None,
        is_active=b.is_active,
        created_at=b.created_at.isoformat() if b.created_at else "",
    ) for b in benefits])


# ─── Benefit Claims ─────────────────────────────────────

@router.post("/claims", response_model=APIResponse, status_code=status.HTTP_201_CREATED)
async def create_benefit_claim(
    req: BenefitClaimCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Submit a benefit claim."""
    org_id = await _get_org_id(db, current_user.id)
    if not org_id:
        raise HTTPException(status_code=400, detail="User not in any organization")

    emp_result = await db.execute(
        select(Employee).where(
            Employee.user_id == current_user.id,
            Employee.organization_id == org_id,
            Employee.deleted_at.is_(None),
        )
    )
    emp = emp_result.scalar_one_or_none()
    if not emp:
        raise HTTPException(status_code=400, detail="Employee profile not found")

    claim = BenefitClaim(
        employee_id=emp.id,
        benefit_item_id=uuid.UUID(req.benefit_item_id),
        claim_date=req.claim_date,
        amount=req.amount,
        description=req.description,
        receipt_url=req.receipt_url,
        status="pending",
    )
    db.add(claim)
    await db.flush()

    return APIResponse(data={"message": "Claim submitted", "id": str(claim.id)})


@router.get("/claims", response_model=APIResponse)
async def list_benefit_claims(
    status_filter: str | None = Query(None, alias="status"),
    employee_id: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List benefit claims."""
    org_id = await _get_org_id(db, current_user.id)
    if not org_id:
        return APIResponse(data={"data": [], "pagination": {"page": page, "page_size": page_size, "total": 0}})

    query = select(BenefitClaim).options(
        joinedload(BenefitClaim.employee).joinedload(Employee.user),
        joinedload(BenefitClaim.benefit_item),
    )

    if employee_id:
        query = query.where(BenefitClaim.employee_id == uuid.UUID(employee_id))
    else:
        # Show claims for the current user
        emp_result = await db.execute(
            select(Employee).where(
                Employee.user_id == current_user.id,
                Employee.organization_id == org_id,
                Employee.deleted_at.is_(None),
            )
        )
        emp = emp_result.scalar_one_or_none()
        if emp:
            query = query.where(BenefitClaim.employee_id == emp.id)
        else:
            return APIResponse(data={"data": [], "pagination": {"page": page, "page_size": page_size, "total": 0}})

    if status_filter:
        statuses = [s.strip() for s in status_filter.split(",")]
        query = query.where(BenefitClaim.status.in_(statuses))

    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    query = query.order_by(BenefitClaim.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    claims = result.scalars().all()

    return APIResponse(data={
        "data": [BenefitClaimResponse(
            id=str(c.id),
            employee_id=str(c.employee_id),
            employee_name=c.employee.user.display_name if c.employee and c.employee.user else None,
            benefit_item_id=str(c.benefit_item_id),
            benefit_item_name=c.benefit_item.name if c.benefit_item else None,
            claim_date=c.claim_date.isoformat(),
            amount=float(c.amount),
            description=c.description,
            status=c.status,
            approved_by=str(c.approved_by) if c.approved_by else None,
            approved_at=c.approved_at.isoformat() if c.approved_at else None,
            receipt_url=c.receipt_url,
            created_at=c.created_at.isoformat() if c.created_at else "",
        ) for c in claims],
        "pagination": {"page": page, "page_size": page_size, "total": total},
    })


@router.put("/claims/{claim_id}/approve", response_model=APIResponse)
async def approve_benefit_claim(
    claim_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Approve a benefit claim."""
    result = await db.execute(select(BenefitClaim).where(BenefitClaim.id == claim_id))
    claim = result.scalar_one_or_none()
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    if claim.status != "pending":
        raise HTTPException(status_code=400, detail=f"Claim is already {claim.status}")

    claim.status = "approved"
    claim.approved_at = datetime.now(timezone.utc)

    # Find approver
    org_id = await _get_org_id(db, current_user.id)
    if org_id:
        emp_result = await db.execute(
            select(Employee).where(
                Employee.user_id == current_user.id,
                Employee.organization_id == org_id,
                Employee.deleted_at.is_(None),
            )
        )
        emp = emp_result.scalar_one_or_none()
        if emp:
            claim.approved_by = emp.id

    db.add(claim)
    await db.flush()
    return APIResponse(data={"message": "Claim approved"})


@router.put("/claims/{claim_id}/reject", response_model=APIResponse)
async def reject_benefit_claim(
    claim_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Reject a benefit claim."""
    result = await db.execute(select(BenefitClaim).where(BenefitClaim.id == claim_id))
    claim = result.scalar_one_or_none()
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    if claim.status != "pending":
        raise HTTPException(status_code=400, detail=f"Claim is already {claim.status}")

    claim.status = "rejected"
    db.add(claim)
    await db.flush()
    return APIResponse(data={"message": "Claim rejected"})
