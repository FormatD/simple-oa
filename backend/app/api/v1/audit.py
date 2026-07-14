"""Audit log API routes - CR R9: Monthly partition strategy."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.deps import get_current_user
from app.database import get_db
from app.models.auth import User
from app.models.audit import AuditLog
from app.schemas.auth import APIResponse
from app.schemas.audit import AuditLogResponse

router = APIRouter(prefix="/audit-logs", tags=["audit"])


@router.get("", response_model=APIResponse)
async def list_audit_logs(
    actor_id: str | None = Query(None),
    action: str | None = Query(None),
    resource_type: str | None = Query(None),
    date_from: str | None = Query(None, alias="date_from"),
    date_to: str | None = Query(None, alias="date_to"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List audit logs with filtering.
    
    CR R9: Audit logs use monthly partition strategy.
    When querying by date range, the query planner routes to the
    appropriate monthly partitions automatically.
    """
    from app.models.organization import OrganizationMember
    result = await db.execute(
        select(OrganizationMember).where(OrganizationMember.user_id == current_user.id)
    )
    member = result.scalar_one_or_none()
    if not member:
        raise HTTPException(400, "Not a member of any organization")
    org_id = member.organization_id

    query = select(AuditLog).options(
        selectinload(AuditLog.actor)
    ).where(
        AuditLog.organization_id == org_id,
    )

    if actor_id:
        query = query.where(AuditLog.actor_id == uuid.UUID(actor_id))
    if action:
        query = query.where(AuditLog.action == action)
    if resource_type:
        query = query.where(AuditLog.resource_type == resource_type)
    if date_from:
        from datetime import datetime, timezone
        dt_from = datetime.fromisoformat(date_from.replace("Z", "+00:00"))
        query = query.where(AuditLog.created_at >= dt_from)
    if date_to:
        from datetime import datetime, timezone
        dt_to = datetime.fromisoformat(date_to.replace("Z", "+00:00"))
        query = query.where(AuditLog.created_at <= dt_to)

    # Count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    query = query.order_by(AuditLog.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    logs = result.scalars().all()

    return APIResponse(
        data=[
            AuditLogResponse(
                id=str(log.id),
                organization_id=str(log.organization_id),
                actor_id=str(log.actor_id),
                actor_name=log.actor.display_name if log.actor else None,
                actor_email=log.actor.email if log.actor else None,
                action=log.action,
                resource_type=log.resource_type,
                resource_id=str(log.resource_id) if log.resource_id else None,
                resource_name=log.resource_name,
                details=log.details,
                ip_address=log.ip_address,
                user_agent=log.user_agent,
                created_at=log.created_at.isoformat() if log.created_at else "",
            )
            for log in logs
        ],
        pagination={"page": page, "page_size": page_size, "total": total},
    )


@router.get("/{log_id}", response_model=APIResponse)
async def get_audit_log(
    log_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get audit log detail."""
    from app.models.organization import OrganizationMember
    result = await db.execute(
        select(OrganizationMember).where(OrganizationMember.user_id == current_user.id)
    )
    member = result.scalar_one_or_none()
    if not member:
        raise HTTPException(400, "Not a member of any organization")
    org_id = member.organization_id

    result = await db.execute(
        select(AuditLog).options(selectinload(AuditLog.actor))
        .where(AuditLog.id == log_id, AuditLog.organization_id == org_id)
    )
    log = result.scalar_one_or_none()
    if not log:
        raise HTTPException(404, "Audit log not found")

    return APIResponse(data=AuditLogResponse(
        id=str(log.id),
        organization_id=str(log.organization_id),
        actor_id=str(log.actor_id),
        actor_name=log.actor.display_name if log.actor else None,
        actor_email=log.actor.email if log.actor else None,
        action=log.action,
        resource_type=log.resource_type,
        resource_id=str(log.resource_id) if log.resource_id else None,
        resource_name=log.resource_name,
        details=log.details,
        ip_address=log.ip_address,
        user_agent=log.user_agent,
        created_at=log.created_at.isoformat() if log.created_at else "",
    ))
