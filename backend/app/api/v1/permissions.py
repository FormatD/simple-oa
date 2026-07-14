"""Permission and role API routes."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.database import get_db
from app.models.auth import User
from app.models.permission import Permission, Role, RolePermission
from app.schemas.auth import APIResponse
from app.schemas.permission import (
    PermissionCheckRequest,
    PermissionCheckResponse,
    PermissionResponse,
    RoleCreate,
    RolePermissionUpdate,
    RoleResponse,
    RoleUpdate,
    UserPermissionsResponse,
)

router = APIRouter(prefix="", tags=["permissions"])


# ─── All permissions ──────────────────────────────────────────────


@router.get("/permissions", response_model=APIResponse)
async def list_permissions(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all available permissions."""
    result = await db.execute(select(Permission).order_by(Permission.module, Permission.code))
    permissions = result.scalars().all()
    return APIResponse(data=[
        PermissionResponse(
            id=str(p.id), code=p.code, name=p.name,
            module=p.module, description=p.description,
        ).model_dump()
        for p in permissions
    ])


# ─── Roles ─────────────────────────────────────────────────────────


@router.get("/organizations/{org_id}/roles", response_model=APIResponse)
async def list_roles(
    org_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List roles for an organization."""
    result = await db.execute(
        select(Role).where(Role.organization_id == org_id)
    )
    roles = result.scalars().all()
    return APIResponse(data=[
        RoleResponse(
            id=str(r.id), organization_id=str(r.organization_id),
            name=r.name, display_name=r.display_name,
            description=r.description, is_system=r.is_system,
        ).model_dump()
        for r in roles
    ])


@router.post("/organizations/{org_id}/roles", response_model=APIResponse,
             status_code=status.HTTP_201_CREATED)
async def create_role(
    org_id: uuid.UUID,
    req: RoleCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a role under an organization."""
    existing = await db.execute(
        select(Role).where(Role.name == req.name)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                            detail="Role name already exists")

    role = Role(
        organization_id=org_id,
        name=req.name,
        display_name=req.display_name,
        description=req.description,
    )
    db.add(role)
    await db.flush()
    return APIResponse(data=_role_to_response(role))


@router.get("/organizations/{org_id}/roles/{role_id}", response_model=APIResponse)
async def get_role(
    org_id: uuid.UUID,
    role_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get role details."""
    result = await db.execute(
        select(Role).where(Role.id == role_id, Role.organization_id == org_id)
    )
    role = result.scalar_one_or_none()
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Role not found")
    return APIResponse(data=_role_to_response(role))


@router.put("/organizations/{org_id}/roles/{role_id}", response_model=APIResponse)
async def update_role(
    org_id: uuid.UUID,
    role_id: uuid.UUID,
    req: RoleUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a role."""
    result = await db.execute(
        select(Role).where(Role.id == role_id, Role.organization_id == org_id)
    )
    role = result.scalar_one_or_none()
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Role not found")
    if role.is_system:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Cannot modify system roles")

    update_data = req.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(role, key, value)
    db.add(role)
    return APIResponse(data=_role_to_response(role))


@router.delete("/organizations/{org_id}/roles/{role_id}", response_model=APIResponse)
async def delete_role(
    org_id: uuid.UUID,
    role_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a role."""
    result = await db.execute(
        select(Role).where(Role.id == role_id, Role.organization_id == org_id)
    )
    role = result.scalar_one_or_none()
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Role not found")
    if role.is_system:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Cannot delete system roles")
    await db.delete(role)
    return APIResponse(message="Role deleted")


# ─── Role Permissions ──────────────────────────────────────────────


@router.get("/organizations/{org_id}/roles/{role_id}/permissions",
            response_model=APIResponse)
async def get_role_permissions(
    org_id: uuid.UUID,
    role_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get permissions assigned to a role."""
    result = await db.execute(
        select(Permission)
        .join(RolePermission)
        .where(RolePermission.role_id == role_id)
    )
    permissions = result.scalars().all()
    return APIResponse(data=[
        PermissionResponse(
            id=str(p.id), code=p.code, name=p.name,
            module=p.module, description=p.description,
        ).model_dump()
        for p in permissions
    ])


@router.put("/organizations/{org_id}/roles/{role_id}/permissions",
            response_model=APIResponse)
async def set_role_permissions(
    org_id: uuid.UUID,
    role_id: uuid.UUID,
    req: RolePermissionUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Set permissions for a role (replaces all)."""
    role_result = await db.execute(
        select(Role).where(Role.id == role_id, Role.organization_id == org_id)
    )
    if not role_result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Role not found")

    # Remove existing
    await db.execute(
        RolePermission.__table__.delete().where(
            RolePermission.role_id == role_id
        )
    )

    # Add new
    for perm_id in req.permission_ids:
        rp = RolePermission(role_id=role_id, permission_id=uuid.UUID(perm_id))
        db.add(rp)

    return APIResponse(message="Permissions updated")


# ─── Permission Checks ────────────────────────────────────────────


@router.get("/organizations/{org_id}/permissions/check",
            response_model=APIResponse)
async def check_permission(
    org_id: uuid.UUID,
    permission_code: str,
    user_id: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Check if a user has a specific permission."""
    target_user_id = uuid.UUID(user_id) if user_id else current_user.id

    if current_user.is_superuser:
        return APIResponse(data=PermissionCheckResponse(has_permission=True).model_dump())

    # Resolve user's roles and check for permission
    # TODO: Full role resolution across all departments
    return APIResponse(data=PermissionCheckResponse(has_permission=False).model_dump())


@router.get("/organizations/{org_id}/users/{user_id}/permissions",
            response_model=APIResponse)
async def get_user_permissions(
    org_id: uuid.UUID,
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get all permissions for a user across all departments."""
    # TODO: Full permission resolution
    return APIResponse(data=UserPermissionsResponse(
        user_id=str(user_id),
        permissions=[],
        roles=[],
    ).model_dump())


# ─── Helper ────────────────────────────────────────────────────────

def _role_to_response(role: Role) -> dict:
    return RoleResponse(
        id=str(role.id),
        organization_id=str(role.organization_id),
        name=role.name,
        display_name=role.display_name,
        description=role.description,
        is_system=role.is_system,
    ).model_dump()
