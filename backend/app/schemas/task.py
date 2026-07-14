"""Task module schemas."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class TaskCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    description: str | None = None
    assignee_id: str | None = None
    priority: str = "medium"
    due_date: datetime | None = None
    tags: list[str] | None = None
    project_id: str | None = None


class TaskUpdate(BaseModel):
    title: str | None = Field(None, max_length=500)
    description: str | None = None
    assignee_id: str | None = None
    priority: str | None = None
    due_date: datetime | None = None
    tags: list[str] | None = None
    project_id: str | None = None


class TaskStatusUpdate(BaseModel):
    status: str = Field(..., pattern=r"^(todo|in_progress|review|done)$")


class TaskReorder(BaseModel):
    status: str
    sort_order: int


class TaskResponse(BaseModel):
    id: str
    organization_id: str
    project_id: str | None = None
    assigner_id: str
    assigner_name: str | None = None
    assignee_id: str | None = None
    assignee_name: str | None = None
    title: str
    description: str | None = None
    status: str
    priority: str
    due_date: str | None = None
    completed_at: str | None = None
    tags: list[str] | None = None
    sort_order: int
    created_at: str
    updated_at: str


class KanbanColumn(BaseModel):
    status: str
    tasks: list[TaskResponse]


# ─── Subtasks ────────────────────────────────────────

class SubtaskCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    assignee_id: str | None = None


class SubtaskUpdate(BaseModel):
    title: str | None = Field(None, max_length=500)
    is_done: bool | None = None
    assignee_id: str | None = None


class SubtaskResponse(BaseModel):
    id: str
    task_id: str
    title: str
    is_done: bool
    sort_order: int
    assignee_id: str | None = None
    assignee_name: str | None = None
    created_at: str
    updated_at: str


# ─── Comments ────────────────────────────────────────

class CommentCreate(BaseModel):
    content: str = Field(..., min_length=1)
    parent_id: str | None = None
    mentions: list[str] | None = None


class CommentUpdate(BaseModel):
    content: str = Field(..., min_length=1)


class CommentResponse(BaseModel):
    id: str
    task_id: str
    author_id: str
    author_name: str | None = None
    author_avatar: str | None = None
    parent_id: str | None = None
    content: str
    mentions: list[str] | None = None
    created_at: str
    updated_at: str


# ─── Activities ──────────────────────────────────────

class ActivityResponse(BaseModel):
    id: str
    task_id: str
    actor_id: str
    actor_name: str | None = None
    action: str
    field: str | None = None
    old_value: str | None = None
    new_value: str | None = None
    meta_data: dict[str, Any] | None = None
    created_at: str
