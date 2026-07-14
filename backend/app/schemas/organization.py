"""Organization & department schemas."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class OrganizationCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    slug: str = Field(..., min_length=1, max_length=100, pattern=r"^[a-z0-9-]+$")
    description: str | None = None
    logo_url: str | None = None


class OrganizationUpdate(BaseModel):
    name: str | None = Field(None, max_length=200)
    description: str | None = None
    logo_url: str | None = None
    settings: dict[str, Any] | None = None


class OrganizationResponse(BaseModel):
    id: str
    name: str
    slug: str
    logo_url: str | None = None
    description: str | None = None
    owner_id: str
    is_active: bool
    created_at: str
    updated_at: str


class DepartmentCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    parent_id: str | None = None
    sort_order: int = 0


class DepartmentUpdate(BaseModel):
    name: str | None = Field(None, max_length=200)
    parent_id: str | None = None
    sort_order: int | None = None


class DepartmentResponse(BaseModel):
    id: str
    organization_id: str
    parent_id: str | None = None
    name: str
    path: str | None = None
    sort_order: int
    children: list[DepartmentResponse] | None = None
    member_count: int = 0


class AddOrgMemberRequest(BaseModel):
    user_id: str


class OrgMemberResponse(BaseModel):
    id: str
    user_id: str
    display_name: str | None = None
    email: str | None = None
    joined_at: str


class AddDepartmentMemberRequest(BaseModel):
    user_id: str
    role_id: str | None = None


class DepartmentMemberResponse(BaseModel):
    id: str
    user_id: str
    display_name: str | None = None
    email: str | None = None
    role_id: str | None = None
    role_name: str | None = None


class DepartmentMemberRoleUpdate(BaseModel):
    role_id: str | None = None
