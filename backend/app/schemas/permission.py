"""Permission & role schemas."""
from __future__ import annotations

from pydantic import BaseModel, Field


class RoleCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, pattern=r"^[a-z_]+$")
    display_name: str = Field(..., min_length=1, max_length=100)
    description: str | None = None


class RoleUpdate(BaseModel):
    display_name: str | None = Field(None, max_length=100)
    description: str | None = None


class RoleResponse(BaseModel):
    id: str
    organization_id: str
    name: str
    display_name: str
    description: str | None = None
    is_system: bool


class PermissionResponse(BaseModel):
    id: str
    code: str
    name: str
    module: str
    description: str | None = None


class RolePermissionUpdate(BaseModel):
    permission_ids: list[str]


class PermissionCheckRequest(BaseModel):
    permission_code: str
    user_id: str | None = None  # If None, check current user
    department_id: str | None = None


class PermissionCheckResponse(BaseModel):
    has_permission: bool


class UserPermissionsResponse(BaseModel):
    user_id: str
    permissions: list[PermissionResponse]
    roles: list[RoleResponse]
    position_level: int | None = None
