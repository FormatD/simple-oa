"""File upload API routes."""
from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query, status
from fastapi.responses import FileResponse
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.database import get_db
from app.models.auth import User
from app.models.upload import Upload
from app.schemas.auth import APIResponse
from app.schemas.upload import UploadResponse

router = APIRouter(prefix="/uploads", tags=["uploads"])

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "storage", "uploads")


def _ensure_upload_dir():
    os.makedirs(UPLOAD_DIR, exist_ok=True)


def _upload_to_response(u: Upload) -> UploadResponse:
    return UploadResponse(
        id=str(u.id),
        organization_id=str(u.organization_id),
        user_id=str(u.user_id),
        filename=u.filename,
        original_filename=u.original_filename,
        mime_type=u.mime_type,
        size=u.size,
        url=f"/api/v1/uploads/{u.id}/download",
        created_at=u.created_at.isoformat() if u.created_at else "",
        updated_at=u.updated_at.isoformat() if u.updated_at else "",
    )


@router.post("", response_model=APIResponse, status_code=201)
async def upload_file(
    file: UploadFile = File(...),
    source_type: str | None = None,
    source_id: str | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Upload a file."""
    from app.models.organization import OrganizationMember
    result = await db.execute(
        select(OrganizationMember).where(OrganizationMember.user_id == current_user.id)
    )
    member = result.scalar_one_or_none()
    if not member:
        raise HTTPException(400, "Not a member of any organization")

    # Validate file size (50MB max)
    MAX_SIZE = 50 * 1024 * 1024
    contents = await file.read()
    if len(contents) > MAX_SIZE:
        raise HTTPException(400, "File too large (max 50MB)")

    _ensure_upload_dir()
    ext = os.path.splitext(file.filename or "file")[1]
    filename = f"{uuid.uuid4().hex}{ext}"
    filepath = os.path.join(UPLOAD_DIR, filename)

    with open(filepath, "wb") as f:
        f.write(contents)

    upload = Upload(
        organization_id=member.organization_id,
        user_id=current_user.id,
        filename=filename,
        original_filename=file.filename or "unknown",
        mime_type=file.content_type or "application/octet-stream",
        size=len(contents),
        storage_path=filepath,
        is_temp=not (source_type and source_id),
        source_type=source_type,
        source_id=uuid.UUID(source_id) if source_id else None,
    )
    db.add(upload)
    await db.flush()

    return APIResponse(data=_upload_to_response(upload))


@router.get("", response_model=APIResponse)
async def list_uploads(
    source_type: str | None = Query(None),
    source_id: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List uploaded files."""
    from app.models.organization import OrganizationMember
    result = await db.execute(
        select(OrganizationMember).where(OrganizationMember.user_id == current_user.id)
    )
    member = result.scalar_one_or_none()
    if not member:
        return APIResponse(data=[])
    org_id = member.organization_id

    query = select(Upload).where(
        Upload.organization_id == org_id,
        Upload.deleted_at.is_(None),
    )

    if source_type:
        query = query.where(Upload.source_type == source_type)
    if source_id:
        query = query.where(Upload.source_id == uuid.UUID(source_id))

    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    query = query.order_by(Upload.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    uploads = result.scalars().all()

    return APIResponse(
        data=[_upload_to_response(u) for u in uploads],
        pagination={"page": page, "page_size": page_size, "total": total},
    )


@router.get("/{upload_id}", response_model=APIResponse)
async def get_upload(
    upload_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get file info."""
    from app.models.organization import OrganizationMember
    result = await db.execute(
        select(OrganizationMember).where(OrganizationMember.user_id == current_user.id)
    )
    member = result.scalar_one_or_none()
    if not member:
        raise HTTPException(400, "Not a member of any organization")
    org_id = member.organization_id

    result = await db.execute(
        select(Upload).where(Upload.id == upload_id, Upload.organization_id == org_id)
    )
    upload = result.scalar_one_or_none()
    if not upload:
        raise HTTPException(404, "Upload not found")

    return APIResponse(data=_upload_to_response(upload))


@router.get("/{upload_id}/download")
async def download_file(
    upload_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Download/preview a file."""
    from app.models.organization import OrganizationMember
    result = await db.execute(
        select(OrganizationMember).where(OrganizationMember.user_id == current_user.id)
    )
    member = result.scalar_one_or_none()
    if not member:
        raise HTTPException(400, "Not a member of any organization")
    org_id = member.organization_id

    result = await db.execute(
        select(Upload).where(Upload.id == upload_id, Upload.organization_id == org_id)
    )
    upload = result.scalar_one_or_none()
    if not upload:
        raise HTTPException(404, "Upload not found")

    if not os.path.exists(upload.storage_path):
        raise HTTPException(404, "File not found on disk")

    media_type = upload.mime_type or "application/octet-stream"
    return FileResponse(
        path=upload.storage_path,
        media_type=media_type,
        filename=upload.original_filename,
    )


@router.delete("/{upload_id}", response_model=APIResponse)
async def delete_upload(
    upload_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a file."""
    from app.models.organization import OrganizationMember
    result = await db.execute(
        select(OrganizationMember).where(OrganizationMember.user_id == current_user.id)
    )
    member = result.scalar_one_or_none()
    if not member:
        raise HTTPException(400, "Not a member of any organization")
    org_id = member.organization_id

    result = await db.execute(
        select(Upload).where(Upload.id == upload_id, Upload.organization_id == org_id)
    )
    upload = result.scalar_one_or_none()
    if not upload:
        raise HTTPException(404, "Upload not found")

    # Delete from disk
    if os.path.exists(upload.storage_path):
        os.remove(upload.storage_path)

    await db.delete(upload)
    return APIResponse(message="File deleted")
