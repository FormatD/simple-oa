"""Wiki/knowledge-base API routes."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.deps import get_current_user
from app.database import get_db
from app.models.auth import User
from app.models.wiki import WikiFolder, WikiPage, WikiPageVersion
from app.schemas.auth import APIResponse
from app.schemas.wiki import (
    WikiFolderCreate,
    WikiFolderResponse,
    WikiFolderUpdate,
    WikiPageCreate,
    WikiPageResponse,
    WikiPageUpdate,
    WikiPageVersionResponse,
    WikiPageVersionResponse,
)

router = APIRouter(prefix="/wiki", tags=["wiki"])


# ─── Helpers ──────────────────────────────────────────

async def _get_org_id(current_user: User, db: AsyncSession) -> uuid.UUID:
    from app.models.organization import OrganizationMember
    result = await db.execute(
        select(OrganizationMember).where(OrganizationMember.user_id == current_user.id)
    )
    member = result.scalar_one_or_none()
    if not member:
        raise HTTPException(400, "Not a member of any organization")
    return member.organization_id


def _folder_to_response(f: WikiFolder, children: list | None = None, page_count: int | None = None) -> WikiFolderResponse:
    return WikiFolderResponse(
        id=str(f.id),
        organization_id=str(f.organization_id),
        parent_id=str(f.parent_id) if f.parent_id else None,
        name=f.name,
        sort_order=f.sort_order or 0,
        created_by=str(f.created_by),
        created_at=f.created_at.isoformat() if f.created_at else "",
        updated_at=f.updated_at.isoformat() if f.updated_at else "",
        children=children,
        page_count=page_count,
    )


def _page_to_response(p: WikiPage) -> WikiPageResponse:
    return WikiPageResponse(
        id=str(p.id),
        organization_id=str(p.organization_id),
        folder_id=str(p.folder_id) if p.folder_id else None,
        title=p.title,
        content=p.content,
        content_html=p.content_html,
        format=p.format,
        version=p.version or 1,
        is_published=p.is_published if p.is_published is not None else True,
        created_by=str(p.created_by),
        creator_name=p.creator.display_name if hasattr(p, 'creator') and p.creator else None,
        last_edited_by=str(p.last_edited_by) if p.last_edited_by else None,
        editor_name=p.editor.display_name if hasattr(p, 'editor') and p.editor else None,
        created_at=p.created_at.isoformat() if p.created_at else "",
        updated_at=p.updated_at.isoformat() if p.updated_at else "",
    )


# ─── Folders ──────────────────────────────────────────

@router.post("/folders", response_model=APIResponse, status_code=201)
async def create_folder(
    req: WikiFolderCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    org_id = await _get_org_id(current_user, db)
    folder = WikiFolder(
        organization_id=org_id,
        parent_id=uuid.UUID(req.parent_id) if req.parent_id else None,
        name=req.name,
        sort_order=req.sort_order,
        created_by=current_user.id,
    )
    db.add(folder)
    await db.flush()
    return APIResponse(data=_folder_to_response(folder))


@router.get("/folders", response_model=APIResponse)
async def list_folders(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get folder tree."""
    org_id = await _get_org_id(current_user, db)

    result = await db.execute(
        select(WikiFolder).where(
            WikiFolder.organization_id == org_id,
            WikiFolder.deleted_at.is_(None),
        ).order_by(WikiFolder.sort_order, WikiFolder.name)
    )
    folders = result.scalars().all()

    # Build tree
    folder_map = {}
    for f in folders:
        page_count = await _get_folder_page_count(db, f.id)
        folder_map[str(f.id)] = _folder_to_response(f, children=[], page_count=page_count)

    tree = []
    for f in folders:
        node = folder_map[str(f.id)]
        if f.parent_id and str(f.parent_id) in folder_map:
            parent = folder_map[str(f.parent_id)]
            if parent.children is None:
                parent.children = []
            parent.children.append(node)
        else:
            tree.append(node)

    return APIResponse(data=tree)


async def _get_folder_page_count(db: AsyncSession, folder_id: uuid.UUID) -> int:
    result = await db.execute(
        select(func.count()).where(
            WikiPage.folder_id == folder_id,
            WikiPage.deleted_at.is_(None),
        )
    )
    return result.scalar() or 0


@router.put("/folders/{folder_id}", response_model=APIResponse)
async def update_folder(
    folder_id: uuid.UUID,
    req: WikiFolderUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    org_id = await _get_org_id(current_user, db)
    result = await db.execute(
        select(WikiFolder).where(
            WikiFolder.id == folder_id,
            WikiFolder.organization_id == org_id,
            WikiFolder.deleted_at.is_(None),
        )
    )
    folder = result.scalar_one_or_none()
    if not folder:
        raise HTTPException(404, "Folder not found")

    update_data = req.model_dump(exclude_unset=True)
    for key, val in update_data.items():
        if key == "parent_id" and val:
            val = uuid.UUID(val)
        setattr(folder, key, val)

    return APIResponse(data=_folder_to_response(folder))


@router.delete("/folders/{folder_id}", response_model=APIResponse)
async def delete_folder(
    folder_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    org_id = await _get_org_id(current_user, db)
    result = await db.execute(
        select(WikiFolder).where(
            WikiFolder.id == folder_id,
            WikiFolder.organization_id == org_id,
            WikiFolder.deleted_at.is_(None),
        )
    )
    folder = result.scalar_one_or_none()
    if not folder:
        raise HTTPException(404, "Folder not found")

    # Check for child folders
    children_result = await db.execute(
        select(func.count()).where(
            WikiFolder.parent_id == folder_id,
            WikiFolder.deleted_at.is_(None),
        )
    )
    if children_result.scalar() > 0:
        raise HTTPException(400, "Cannot delete folder with child folders")

    folder.deleted_at = datetime.now(timezone.utc)
    return APIResponse(message="Folder deleted")


# ─── Pages ────────────────────────────────────────────

@router.post("/pages", response_model=APIResponse, status_code=201)
async def create_page(
    req: WikiPageCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    org_id = await _get_org_id(current_user, db)
    page = WikiPage(
        organization_id=org_id,
        folder_id=uuid.UUID(req.folder_id) if req.folder_id else None,
        title=req.title,
        content=req.content,
        content_html=req.content_html,
        format=req.format,
        version=1,
        created_by=current_user.id,
        last_edited_by=current_user.id,
    )
    db.add(page)
    await db.flush()
    return APIResponse(data=_page_to_response(page))


@router.get("/pages/{page_id}", response_model=APIResponse)
async def get_page(
    page_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    org_id = await _get_org_id(current_user, db)
    result = await db.execute(
        select(WikiPage).options(selectinload(WikiPage.creator), selectinload(WikiPage.editor))
        .where(
            WikiPage.id == page_id,
            WikiPage.organization_id == org_id,
            WikiPage.deleted_at.is_(None),
        )
    )
    page = result.scalar_one_or_none()
    if not page:
        raise HTTPException(404, "Page not found")
    return APIResponse(data=_page_to_response(page))


@router.put("/pages/{page_id}", response_model=APIResponse)
async def update_page(
    page_id: uuid.UUID,
    req: WikiPageUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    org_id = await _get_org_id(current_user, db)
    result = await db.execute(
        select(WikiPage).where(
            WikiPage.id == page_id,
            WikiPage.organization_id == org_id,
            WikiPage.deleted_at.is_(None),
        )
    )
    page = result.scalar_one_or_none()
    if not page:
        raise HTTPException(404, "Page not found")

    # Save current version before updating
    version_record = WikiPageVersion(
        page_id=page.id,
        version=page.version,
        title=page.title,
        content=page.content,
        content_html=page.content_html,
        change_note=req.change_note,
        edited_by=current_user.id,
    )
    db.add(version_record)

    update_data = req.model_dump(exclude_unset=True, exclude={"change_note"})
    for key, val in update_data.items():
        if key == "folder_id" and val:
            val = uuid.UUID(val)
        setattr(page, key, val)

    page.version = (page.version or 1) + 1
    page.last_edited_by = current_user.id

    return APIResponse(data=_page_to_response(page))


@router.delete("/pages/{page_id}", response_model=APIResponse)
async def delete_page(
    page_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    org_id = await _get_org_id(current_user, db)
    result = await db.execute(
        select(WikiPage).where(
            WikiPage.id == page_id,
            WikiPage.organization_id == org_id,
            WikiPage.deleted_at.is_(None),
        )
    )
    page = result.scalar_one_or_none()
    if not page:
        raise HTTPException(404, "Page not found")

    page.deleted_at = datetime.now(timezone.utc)
    return APIResponse(message="Page deleted")


@router.get("/search", response_model=APIResponse)
async def search_pages(
    q: str = Query(..., min_length=1),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Search wiki pages."""
    org_id = await _get_org_id(current_user, db)
    result = await db.execute(
        select(WikiPage).options(selectinload(WikiPage.creator), selectinload(WikiPage.editor))
        .where(
            WikiPage.organization_id == org_id,
            WikiPage.deleted_at.is_(None),
            or_(
                WikiPage.title.ilike(f"%{q}%"),
                WikiPage.content.ilike(f"%{q}%"),
            ),
        )
        .order_by(WikiPage.updated_at.desc())
        .limit(50)
    )
    pages = result.scalars().all()
    return APIResponse(data=[_page_to_response(p) for p in pages])


# ─── Versions ─────────────────────────────────────────

@router.get("/pages/{page_id}/versions", response_model=APIResponse)
async def list_versions(
    page_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    org_id = await _get_org_id(current_user, db)
    result = await db.execute(
        select(WikiPage).where(
            WikiPage.id == page_id,
            WikiPage.organization_id == org_id,
            WikiPage.deleted_at.is_(None),
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(404, "Page not found")

    result = await db.execute(
        select(WikiPageVersion).options(selectinload(WikiPageVersion.editor))
        .where(WikiPageVersion.page_id == page_id)
        .order_by(WikiPageVersion.version.desc())
        .limit(100)
    )
    versions = result.scalars().all()

    return APIResponse(data=[
        WikiPageVersionResponse(
            id=str(v.id),
            page_id=str(v.page_id),
            version=v.version,
            title=v.title,
            content=v.content,
            content_html=v.content_html,
            change_note=v.change_note,
            edited_by=str(v.edited_by),
            editor_name=v.editor.display_name if v.editor else None,
            created_at=v.created_at.isoformat() if v.created_at else "",
        )
        for v in versions
    ])


@router.get("/pages/{page_id}/versions/{version}", response_model=APIResponse)
async def get_version(
    page_id: uuid.UUID,
    version: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    org_id = await _get_org_id(current_user, db)
    result = await db.execute(
        select(WikiPage).where(
            WikiPage.id == page_id,
            WikiPage.organization_id == org_id,
            WikiPage.deleted_at.is_(None),
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(404, "Page not found")

    result = await db.execute(
        select(WikiPageVersion).options(selectinload(WikiPageVersion.editor))
        .where(WikiPageVersion.page_id == page_id, WikiPageVersion.version == version)
    )
    v = result.scalar_one_or_none()
    if not v:
        raise HTTPException(404, "Version not found")

    return APIResponse(data=WikiPageVersionResponse(
        id=str(v.id),
        page_id=str(v.page_id),
        version=v.version,
        title=v.title,
        content=v.content,
        content_html=v.content_html,
        change_note=v.change_note,
        edited_by=str(v.edited_by),
        editor_name=v.editor.display_name if v.editor else None,
        created_at=v.created_at.isoformat() if v.created_at else "",
    ))


@router.post("/pages/{page_id}/versions/{version}/restore", response_model=APIResponse)
async def restore_version(
    page_id: uuid.UUID,
    version: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    org_id = await _get_org_id(current_user, db)
    result = await db.execute(
        select(WikiPage).where(
            WikiPage.id == page_id,
            WikiPage.organization_id == org_id,
            WikiPage.deleted_at.is_(None),
        )
    )
    page = result.scalar_one_or_none()
    if not page:
        raise HTTPException(404, "Page not found")

    result = await db.execute(
        select(WikiPageVersion).where(WikiPageVersion.page_id == page_id, WikiPageVersion.version == version)
    )
    v = result.scalar_one_or_none()
    if not v:
        raise HTTPException(404, "Version not found")

    # Save current version
    current_version = WikiPageVersion(
        page_id=page.id,
        version=page.version,
        title=page.title,
        content=page.content,
        content_html=page.content_html,
        change_note=f"Restored from version {version}",
        edited_by=current_user.id,
    )
    db.add(current_version)

    page.title = v.title
    page.content = v.content
    page.content_html = v.content_html
    page.version = (page.version or 1) + 1
    page.last_edited_by = current_user.id

    return APIResponse(data=_page_to_response(page))
