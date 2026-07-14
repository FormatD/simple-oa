"""Notification module schemas."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class NotificationResponse(BaseModel):
    id: str
    organization_id: str
    type: str
    title: str
    content: str | None = None
    sender_id: str | None = None
    sender_name: str | None = None
    source_type: str | None = None
    source_id: str | None = None
    meta_data: dict[str, Any] | None = None
    is_read: bool
    read_at: str | None = None
    created_at: str


class UnreadCountResponse(BaseModel):
    count: int


class PreferenceCreate(BaseModel):
    notification_type: str
    channel_in_app: bool = True
    channel_email: bool = False
    digest: str = "instant"


class PreferenceUpdate(BaseModel):
    channel_in_app: bool | None = None
    channel_email: bool | None = None
    digest: str | None = Field(None, pattern=r"^(instant|hourly|daily|weekly)$")


class PreferenceResponse(BaseModel):
    id: str
    user_id: str
    notification_type: str
    channel_in_app: bool
    channel_email: bool
    digest: str


class WebSocketEvent(BaseModel):
    event: str
    data: dict[str, Any]


class NotificationCreateRequest(BaseModel):
    type: str = Field(..., max_length=100)
    title: str = Field(..., max_length=500)
    content: str | None = None
    recipient_ids: list[str] = Field(..., min_length=1)
    sender_id: str | None = None
    source_type: str | None = Field(None, max_length=50)
    source_id: str | None = None
    meta_data: dict[str, Any] | None = None
