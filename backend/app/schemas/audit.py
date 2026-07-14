"""Audit log schemas."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class AuditLogResponse(BaseModel):
    id: str
    organization_id: str
    actor_id: str
    actor_name: str | None = None
    actor_email: str | None = None
    action: str
    resource_type: str
    resource_id: str | None = None
    resource_name: str | None = None
    details: dict[str, Any] | None = None
    ip_address: str | None = None
    user_agent: str | None = None
    created_at: str
