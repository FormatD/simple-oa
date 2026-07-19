"""Notification API routes + WebSocket support."""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect, status
from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.deps import get_current_user
from app.core.redis_queue import publish_notification
from app.core.security import decode_access_token
from app.database import get_db
from app.models.auth import User
from app.models.notification import Notification, NotificationRecipient, NotificationPreference
from app.schemas.auth import APIResponse
from app.schemas.notification import (
    NotificationResponse,
    NotificationCreateRequest,
    PreferenceCreate,
    PreferenceResponse,
    PreferenceUpdate,
    UnreadCountResponse,
)

router = APIRouter(prefix="/notifications", tags=["notifications"])


# ─── WebSocket connection manager ─────────────────────

class ConnectionManager:
    """Manages WebSocket connections for real-time notifications."""

    def __init__(self):
        self.active_connections: dict[str, list[WebSocket]] = {}

    async def connect(self, user_id: str, websocket: WebSocket, subprotocol: str | None = None):
        await websocket.accept(subprotocol=subprotocol)
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        self.active_connections[user_id].append(websocket)

    def disconnect(self, user_id: str, websocket: WebSocket):
        if user_id in self.active_connections:
            self.active_connections[user_id] = [
                ws for ws in self.active_connections[user_id] if ws != websocket
            ]
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]

    async def send_to_user(self, user_id: str, message: dict):
        if user_id in self.active_connections:
            dead_connections = []
            for ws in self.active_connections[user_id]:
                try:
                    await ws.send_json(message)
                except Exception:
                    dead_connections.append(ws)
            for ws in dead_connections:
                self.active_connections[user_id].remove(ws)

    async def broadcast_org(self, org_id: str, message: dict, user_ids: list[str]):
        for uid in user_ids:
            await self.send_to_user(uid, message)


manager = ConnectionManager()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time notifications.
    Connection: ws://host/api/v1/notifications/ws
    JWT token passed via Sec-WebSocket-Protocol header (not query param).
    """
    # Extract JWT from Sec-WebSocket-Protocol header instead of query string
    token = websocket.headers.get("sec-websocket-protocol")
    if not token:
        await websocket.close(code=4001)
        return

    try:
        payload = decode_access_token(token)
        user_id = payload.get("sub")
        if not user_id:
            await websocket.close(code=4001)
            return
    except ValueError:
        await websocket.close(code=4001)
        return

    await manager.connect(user_id, websocket, subprotocol=token)
    try:
        while True:
            data = await websocket.receive_text()
            # Client can send ping to keep alive
            if data == "ping":
                await websocket.send_json({"event": "pong"})
    except WebSocketDisconnect:
        manager.disconnect(user_id, websocket)


# ─── Notification CRUD ───────────────────────────────

async def create_and_send_notification(
    db: AsyncSession,
    org_id: uuid.UUID,
    notif_type: str,
    title: str,
    content: str | None,
    recipient_ids: list[uuid.UUID],
    sender_id: uuid.UUID | None = None,
    source_type: str | None = None,
    source_id: uuid.UUID | None = None,
    metadata: dict | None = None,
) -> Notification:
    """Create a notification and push to recipients via WebSocket."""
    notification = Notification(
        organization_id=org_id,
        type=notif_type,
        title=title,
        content=content,
        sender_id=sender_id,
        source_type=source_type,
        source_id=source_id,
        meta_data=metadata or {},
    )
    db.add(notification)
    await db.flush()

    for rid in recipient_ids:
        recipient = NotificationRecipient(
            notification_id=notification.id,
            user_id=rid,
        )
        db.add(recipient)

    # Push via WebSocket
    event_data = {
        "event": "notification.new",
        "data": {
            "id": str(notification.id),
            "type": notif_type,
            "title": title,
            "content": content,
            "source_type": source_type,
            "source_id": str(source_id) if source_id else None,
            "created_at": notification.created_at.isoformat() if notification.created_at else "",
        },
    }
    for rid in recipient_ids:
        await manager.send_to_user(str(rid), event_data)

    # C2: Also publish to queue Redis for cross-process notification broadcasting
    await publish_notification(event_data)

    return notification


@router.post("", response_model=APIResponse, status_code=201)
async def create_notification(
    req: NotificationCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a notification (system/admin endpoint)."""
    from app.models.organization import OrganizationMember
    result = await db.execute(
        select(OrganizationMember).where(OrganizationMember.user_id == current_user.id)
    )
    member = result.scalar_one_or_none()
    if not member:
        raise HTTPException(400, "Not a member of any organization")

    notification = await create_and_send_notification(
        db=db,
        org_id=member.organization_id,
        notif_type=req.type,
        title=req.title,
        content=req.content,
        recipient_ids=[uuid.UUID(rid) for rid in req.recipient_ids],
        sender_id=uuid.UUID(req.sender_id) if req.sender_id else current_user.id,
        source_type=req.source_type,
        source_id=uuid.UUID(req.source_id) if req.source_id else None,
        meta_data=req.metadata,
    )

    return APIResponse(data={
        "id": str(notification.id),
        "type": notification.type,
        "title": notification.title,
    })


@router.get("", response_model=APIResponse)
async def list_notifications(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    unread_only: bool = Query(False),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List notifications for the current user."""
    query = (
        select(Notification, NotificationRecipient.is_read, NotificationRecipient.read_at)
        .join(NotificationRecipient, NotificationRecipient.notification_id == Notification.id)
        .where(NotificationRecipient.user_id == current_user.id)
        .order_by(Notification.created_at.desc())
    )

    if unread_only:
        query = query.where(NotificationRecipient.is_read == False)

    total_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(total_query)
    total = total_result.scalar() or 0

    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    rows = result.all()

    return APIResponse(
        data=[
            NotificationResponse(
                id=str(n.id),
                organization_id=str(n.organization_id),
                type=n.type,
                title=n.title,
                content=n.content,
                sender_id=str(n.sender_id) if n.sender_id else None,
                source_type=n.source_type,
                source_id=str(n.source_id) if n.source_id else None,
                extra_data=n.meta_data,
                is_read=is_read,
                read_at=read_at.isoformat() if read_at else None,
                created_at=n.created_at.isoformat() if n.created_at else "",
            )
            for n, is_read, read_at in rows
        ],
        pagination={"page": page, "page_size": page_size, "total": total},
    )


@router.get("/unread-count", response_model=APIResponse)
async def get_unread_count(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get unread notification count."""
    result = await db.execute(
        select(func.count()).where(
            NotificationRecipient.user_id == current_user.id,
            NotificationRecipient.is_read == False,
        )
    )
    count = result.scalar() or 0
    return APIResponse(data={"count": count})


@router.put("/{notif_id}/read", response_model=APIResponse)
async def mark_read(
    notif_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Mark a single notification as read."""
    result = await db.execute(
        select(NotificationRecipient).where(
            NotificationRecipient.notification_id == notif_id,
            NotificationRecipient.user_id == current_user.id,
        )
    )
    recipient = result.scalar_one_or_none()
    if not recipient:
        raise HTTPException(404, "Notification not found")

    recipient.is_read = True
    recipient.read_at = datetime.now(timezone.utc)
    return APIResponse(message="Marked as read")


@router.put("/read-all", response_model=APIResponse)
async def mark_all_read(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Mark all notifications as read."""
    await db.execute(
        update(NotificationRecipient)
        .where(
            NotificationRecipient.user_id == current_user.id,
            NotificationRecipient.is_read == False,
        )
        .values(is_read=True, read_at=datetime.now(timezone.utc))
    )
    return APIResponse(message="All marked as read")


# ─── Preferences ──────────────────────────────────────

@router.get("/preferences", response_model=APIResponse)
async def get_preferences(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get notification preferences."""
    result = await db.execute(
        select(NotificationPreference).where(NotificationPreference.user_id == current_user.id)
    )
    prefs = result.scalars().all()
    return APIResponse(data=[
        PreferenceResponse(
            id=str(p.id),
            user_id=str(p.user_id),
            notification_type=p.notification_type,
            channel_in_app=p.channel_in_app,
            channel_email=p.channel_email,
            digest=p.digest,
        )
        for p in prefs
    ])


@router.put("/preferences", response_model=APIResponse)
async def upsert_preferences(
    prefs: list[PreferenceCreate],
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Upsert notification preferences."""
    results = []
    for pref in prefs:
        result = await db.execute(
            select(NotificationPreference).where(
                NotificationPreference.user_id == current_user.id,
                NotificationPreference.notification_type == pref.notification_type,
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            existing.channel_in_app = pref.channel_in_app
            existing.channel_email = pref.channel_email
            existing.digest = pref.digest
        else:
            existing = NotificationPreference(
                user_id=current_user.id,
                notification_type=pref.notification_type,
                channel_in_app=pref.channel_in_app,
                channel_email=pref.channel_email,
                digest=pref.digest,
            )
            db.add(existing)
        results.append(existing)

    await db.flush()
    return APIResponse(data=[
        PreferenceResponse(
            id=str(p.id),
            user_id=str(p.user_id),
            notification_type=p.notification_type,
            channel_in_app=p.channel_in_app,
            channel_email=p.channel_email,
            digest=p.digest,
        )
        for p in results
    ])
