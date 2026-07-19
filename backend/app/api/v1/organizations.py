"""Organization and department API routes."""
from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.deps import get_current_user
from app.database import get_db
from app.models.auth import User
from app.models.organization import (
    Department,
    DepartmentMember,
    Organization,
    OrganizationMember,
)
from app.models.permission import Role
from app.schemas.auth import APIResponse
from app.schemas.organization import (
    AddDepartmentMemberRequest,
    AddOrgMemberRequest,
    DepartmentCreate,
    DepartmentMemberResponse,
    DepartmentMemberRoleUpdate,
    DepartmentResponse,
    DepartmentUpdate,
    OrganizationCreate,
    OrgMemberResponse,
    OrganizationResponse,
    OrganizationUpdate,
)

router = APIRouter(prefix="/organizations", tags=["organizations"])


@router.post("", response_model=APIResponse, status_code=status.HTTP_201_CREATED)
async def create_organization(
    req: OrganizationCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new organization."""
    existing = await db.execute(
        select(Organization).where(Organization.slug == req.slug)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Organization slug already exists",
        )

    org = Organization(
        name=req.name,
        slug=req.slug,
        description=req.description,
        logo_url=req.logo_url,
        owner_id=current_user.id,
    )
    db.add(org)
    await db.flush()

    # Add creator as organization member
    member = OrganizationMember(
        organization_id=org.id,
        user_id=current_user.id,
    )
    db.add(member)
    await db.flush()

    return APIResponse(data=_org_to_response(org))


@router.get("", response_model=APIResponse)
async def list_organizations(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List organizations for the current user."""
    result = await db.execute(
        select(Organization)
        .join(OrganizationMember)
        .where(OrganizationMember.user_id == current_user.id)
    )
    orgs = result.scalars().all()
    return APIResponse(data=[_org_to_response(o) for o in orgs])


@router.get("/{org_id}", response_model=APIResponse)
async def get_organization(
    org_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get organization details."""
    result = await db.execute(
        select(Organization).where(Organization.id == org_id)
    )
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Organization not found")
    return APIResponse(data=_org_to_response(org))


@router.put("/{org_id}", response_model=APIResponse)
async def update_organization(
    org_id: uuid.UUID,
    req: OrganizationUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update organization."""
    result = await db.execute(
        select(Organization).where(Organization.id == org_id)
    )
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Organization not found")
    if org.owner_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Only the owner can update the organization")

    update_data = req.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(org, key, value)
    db.add(org)
    return APIResponse(data=_org_to_response(org))


@router.delete("/{org_id}", response_model=APIResponse)
async def delete_organization(
    org_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete an organization."""
    result = await db.execute(
        select(Organization).where(Organization.id == org_id)
    )
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Organization not found")
    if org.owner_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Only the owner can delete the organization")
    org.is_active = False
    org.deleted_at = func.now()
    db.add(org)
    return APIResponse(message="Organization deleted")


# ─── Department routes ──────────────────────────────────────────


@router.post("/{org_id}/departments", response_model=APIResponse,
             status_code=status.HTTP_201_CREATED)
async def create_department(
    org_id: uuid.UUID,
    req: DepartmentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a department under an organization."""
    result = await db.execute(
        select(Organization).where(Organization.id == org_id)
    )
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Organization not found")

    parent_dept = None
    if req.parent_id:
        result = await db.execute(
            select(Department).where(
                Department.id == req.parent_id,
                Department.organization_id == org_id,
            )
        )
        parent_dept = result.scalar_one_or_none()
        if not parent_dept:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail="Parent department not found")

    dept = Department(
        organization_id=org_id,
        parent_id=req.parent_id,
        name=req.name,
        sort_order=req.sort_order,
    )
    db.add(dept)
    await db.flush()

    # Build path
    if parent_dept:
        dept.path = f"{parent_dept.path}.{dept.id}" if parent_dept.path else str(dept.id)
    else:
        dept.path = str(dept.id)
    db.add(dept)

    return APIResponse(data=await _dept_to_response(db, dept))


@router.get("/{org_id}/departments", response_model=APIResponse)
async def list_departments(
    org_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get department tree for an organization."""
    result = await db.execute(
        select(Department)
        .where(
            Department.organization_id == org_id,
            Department.deleted_at.is_(None),
        )
        .order_by(Department.sort_order, Department.name)
    )
    all_depts = result.scalars().all()
    tree = _build_dept_tree(all_depts, None)
    return APIResponse(data=tree)


@router.get("/{org_id}/departments/{dept_id}", response_model=APIResponse)
async def get_department(
    org_id: uuid.UUID,
    dept_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get department details."""
    result = await db.execute(
        select(Department).where(
            Department.id == dept_id,
            Department.organization_id == org_id,
        )
    )
    dept = result.scalar_one_or_none()
    if not dept:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Department not found")
    return APIResponse(data=await _dept_to_response(db, dept))


@router.put("/{org_id}/departments/{dept_id}", response_model=APIResponse)
async def update_department(
    org_id: uuid.UUID,
    dept_id: uuid.UUID,
    req: DepartmentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a department."""
    result = await db.execute(
        select(Department).where(
            Department.id == dept_id,
            Department.organization_id == org_id,
        )
    )
    dept = result.scalar_one_or_none()
    if not dept:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Department not found")
    update_data = req.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(dept, key, value)
    db.add(dept)
    return APIResponse(data=await _dept_to_response(db, dept))


@router.delete("/{org_id}/departments/{dept_id}", response_model=APIResponse)
async def delete_department(
    org_id: uuid.UUID,
    dept_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Soft-delete a department."""
    result = await db.execute(
        select(Department).where(
            Department.id == dept_id,
            Department.organization_id == org_id,
        )
    )
    dept = result.scalar_one_or_none()
    if not dept:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Department not found")
    dept.deleted_at = func.now()
    db.add(dept)
    return APIResponse(message="Department deleted")


# ─── Organization Members ────────────────────────────────────────


@router.post("/{org_id}/members", response_model=APIResponse,
             status_code=status.HTTP_201_CREATED)
async def add_org_member(
    org_id: uuid.UUID,
    req: AddOrgMemberRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Add a member to an organization."""
    result = await db.execute(
        select(Organization).where(Organization.id == org_id)
    )
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Organization not found")

    existing = await db.execute(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == org_id,
            OrganizationMember.user_id == uuid.UUID(req.user_id),
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                            detail="User is already a member")

    member = OrganizationMember(
        organization_id=org_id,
        user_id=uuid.UUID(req.user_id),
    )
    db.add(member)
    await db.flush()
    return APIResponse(message="Member added successfully")


@router.get("/{org_id}/members", response_model=APIResponse)
async def list_org_members(
    org_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List organization members."""
    result = await db.execute(
        select(OrganizationMember)
        .where(OrganizationMember.organization_id == org_id)
    )
    members = result.scalars().all()
    return APIResponse(data=[
        OrgMemberResponse(
            id=str(m.id),
            user_id=str(m.user_id),
            joined_at=m.joined_at.isoformat(),
        ).model_dump()
        for m in members
    ])


@router.delete("/{org_id}/members/{user_id}", response_model=APIResponse)
async def remove_org_member(
    org_id: uuid.UUID,
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Remove a member from an organization."""
    result = await db.execute(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == org_id,
            OrganizationMember.user_id == user_id,
        )
    )
    member = result.scalar_one_or_none()
    if not member:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Member not found")
    await db.delete(member)
    return APIResponse(message="Member removed")


# ─── Department Members ──────────────────────────────────────────


@router.post("/{org_id}/departments/{dept_id}/members",
             response_model=APIResponse, status_code=status.HTTP_201_CREATED)
async def add_department_member(
    org_id: uuid.UUID,
    dept_id: uuid.UUID,
    req: AddDepartmentMemberRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Add a member to a department with optional role."""
    dept_result = await db.execute(
        select(Department).where(
            Department.id == dept_id,
            Department.organization_id == org_id,
        )
    )
    dept = dept_result.scalar_one_or_none()
    if not dept:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Department not found")

    existing = await db.execute(
        select(DepartmentMember).where(
            DepartmentMember.department_id == dept_id,
            DepartmentMember.user_id == uuid.UUID(req.user_id),
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                            detail="User already in this department")

    member = DepartmentMember(
        department_id=dept_id,
        user_id=uuid.UUID(req.user_id),
        role_id=uuid.UUID(req.role_id) if req.role_id else None,
    )
    db.add(member)
    await db.flush()
    return APIResponse(message="Member added to department")


@router.get("/{org_id}/departments/{dept_id}/members",
            response_model=APIResponse)
async def list_department_members(
    org_id: uuid.UUID,
    dept_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List department members."""
    result = await db.execute(
        select(DepartmentMember)
        .where(DepartmentMember.department_id == dept_id)
    )
    members = result.scalars().all()

    resp = []
    for m in members:
        role_name = None
        if m.role_id:
            role_result = await db.execute(
                select(Role).where(Role.id == m.role_id)
            )
            role = role_result.scalar_one_or_none()
            role_name = role.display_name if role else None
        resp.append(DepartmentMemberResponse(
            id=str(m.id),
            user_id=str(m.user_id),
            role_id=str(m.role_id) if m.role_id else None,
            role_name=role_name,
        ).model_dump())

    return APIResponse(data=resp)


@router.put("/{org_id}/departments/{dept_id}/members/{user_id}/role",
            response_model=APIResponse)
async def update_member_role(
    org_id: uuid.UUID,
    dept_id: uuid.UUID,
    user_id: uuid.UUID,
    req: DepartmentMemberRoleUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Change a department member's role."""
    result = await db.execute(
        select(DepartmentMember).where(
            DepartmentMember.department_id == dept_id,
            DepartmentMember.user_id == user_id,
        )
    )
    member = result.scalar_one_or_none()
    if not member:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Member not found in this department")
    member.role_id = uuid.UUID(req.role_id) if req.role_id else None
    db.add(member)
    return APIResponse(message="Role updated")


@router.delete("/{org_id}/departments/{dept_id}/members/{user_id}",
               response_model=APIResponse)
async def remove_department_member(
    org_id: uuid.UUID,
    dept_id: uuid.UUID,
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Remove a member from a department."""
    result = await db.execute(
        select(DepartmentMember).where(
            DepartmentMember.department_id == dept_id,
            DepartmentMember.user_id == user_id,
        )
    )
    member = result.scalar_one_or_none()
    if not member:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Member not found")
    await db.delete(member)
    return APIResponse(message="Member removed from department")



@router.get("/{org_id}/departments/children", response_model=APIResponse)
async def list_department_children(
    org_id: uuid.UUID,
    parent_id: uuid.UUID | None = Query(None, description="Parent department ID (null for root nodes)"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lazy-load department children (P3). Returns only direct children of parent_id."""
    query = select(Department).where(
        Department.organization_id == org_id,
        Department.deleted_at.is_(None),
    )

    if parent_id is None:
        query = query.where(Department.parent_id.is_(None))
    else:
        query = query.where(Department.parent_id == parent_id)

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    query = query.order_by(Department.sort_order, Department.name)
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    depts = result.scalars().all()

    # M3: Batch count children using GROUP BY to avoid N+1
    tree_data = []
    if depts:
        dept_ids = [d.id for d in depts]
        child_counts = await db.execute(
            select(Department.parent_id, func.count().label("cnt"))
            .where(
                Department.parent_id.in_(dept_ids),
                Department.deleted_at.is_(None),
            )
            .group_by(Department.parent_id)
        )
        child_count_map = {str(row.parent_id): row.cnt for row in child_counts.all()}

        for dept in depts:
            has_children = child_count_map.get(str(dept.id), 0) > 0
            tree_data.append({
                "id": str(dept.id),
                "organization_id": str(dept.organization_id),
                "parent_id": str(dept.parent_id) if dept.parent_id else None,
                "name": dept.name,
                "path": dept.path,
                "sort_order": dept.sort_order,
                "has_children": has_children,
                "member_count": 0,
            })

    return APIResponse(data={
        "data": tree_data,
        "pagination": {"page": page, "page_size": page_size, "total": total},
    })


# ─── Helpers ──────────────────────────────────────────────────────


def _org_to_response(org: Organization) -> dict:
    return OrganizationResponse(
        id=str(org.id),
        name=org.name,
        slug=org.slug,
        logo_url=org.logo_url,
        description=org.description,
        owner_id=str(org.owner_id),
        is_active=org.is_active,
        created_at=org.created_at.isoformat() if org.created_at else "",
        updated_at=org.updated_at.isoformat() if org.updated_at else "",
    ).model_dump()


async def _dept_to_response(
    db: AsyncSession, dept: Department
) -> dict:
    # Count members
    count_result = await db.execute(
        select(func.count(DepartmentMember.id))
        .where(DepartmentMember.department_id == dept.id)
    )
    member_count = count_result.scalar() or 0

    return DepartmentResponse(
        id=str(dept.id),
        organization_id=str(dept.organization_id),
        parent_id=str(dept.parent_id) if dept.parent_id else None,
        name=dept.name,
        path=dept.path,
        sort_order=dept.sort_order,
        member_count=member_count,
    ).model_dump()


def _build_dept_tree(
    departments: list[Department], parent_id: uuid.UUID | None
) -> list[dict]:
    """Build department tree recursively."""
    tree = []
    for dept in departments:
        if dept.parent_id == parent_id or (parent_id is None and dept.parent_id is None):
            children = _build_dept_tree(departments, dept.id)
            node = {
                "id": str(dept.id),
                "organization_id": str(dept.organization_id),
                "parent_id": str(dept.parent_id) if dept.parent_id else None,
                "name": dept.name,
                "path": dept.path,
                "sort_order": dept.sort_order,
                "children": children if children else None,
            }
            tree.append(node)
    return tree
