"""Wiki module schemas."""
from __future__ import annotations

from pydantic import BaseModel, Field


class WikiFolderCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    parent_id: str | None = None
    sort_order: int = 0


class WikiFolderUpdate(BaseModel):
    name: str | None = Field(None, max_length=200)
    parent_id: str | None = None
    sort_order: int | None = None


class WikiFolderResponse(BaseModel):
    id: str
    organization_id: str
    parent_id: str | None = None
    name: str
    sort_order: int
    created_by: str
    created_at: str
    updated_at: str
    children: list[WikiFolderResponse] | None = None
    page_count: int | None = None


class WikiPageCreate(BaseModel):
    folder_id: str | None = None
    title: str = Field(..., min_length=1, max_length=500)
    content: str | None = None
    content_html: str | None = None
    format: str = "markdown"
    change_note: str | None = None


class WikiPageUpdate(BaseModel):
    title: str | None = Field(None, max_length=500)
    content: str | None = None
    content_html: str | None = None
    folder_id: str | None = None
    is_published: bool | None = None
    change_note: str | None = None


class WikiPageResponse(BaseModel):
    id: str
    organization_id: str
    folder_id: str | None = None
    title: str
    content: str | None = None
    content_html: str | None = None
    format: str
    version: int
    is_published: bool
    created_by: str
    creator_name: str | None = None
    last_edited_by: str | None = None
    editor_name: str | None = None
    created_at: str
    updated_at: str


class WikiPageVersionResponse(BaseModel):
    id: str
    page_id: str
    version: int
    title: str
    content: str | None = None
    content_html: str | None = None
    change_note: str | None = None
    edited_by: str
    editor_name: str | None = None
    created_at: str
