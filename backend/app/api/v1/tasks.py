"""Task management API routes."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.deps import get_current_user
from app.database import get_db
from app.models.auth import User
from app.models.task import Task, TaskSubtask, TaskComment, TaskActivity
from app.schemas.auth import APIResponse
from app.schemas.task import (
    ActivityResponse,
    CommentCreate,
    CommentResponse,
    CommentUpdate,
    KanbanColumn,
    SubtaskCreate,
    SubtaskResponse,
    SubtaskUpdate,
    TaskCreate,
    TaskReorder,
    TaskResponse,
    TaskStatusUpdate,
    TaskUpdate,
)

router = APIRouter(prefix="/tasks", tags=["tasks"])


# ─── Helper ───────────────────────────────────────────

async def _get_task_or_404(db: AsyncSession, task_id: uuid.UUID, org_id: uuid.UUID) -> Task:
    result = await db.execute(
        select(Task).options(
            selectinload(Task.assigner), selectinload(Task.assignee)
        ).where(Task.id == task_id, Task.organization_id == org_id, Task.deleted_at.is_(None))
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


def _task_to_response(task: Task) -> TaskResponse:
    return TaskResponse(
        id=str(task.id),
        organization_id=str(task.organization_id),
        project_id=str(task.project_id) if task.project_id else None,
        assigner_id=str(task.assigner_id),
        assigner_name=task.assigner.display_name if task.assigner else None,
        assignee_id=str(task.assignee_id) if task.assignee_id else None,
        assignee_name=task.assignee.display_name if task.assignee else None,
        title=task.title,
        description=task.description,
        status=task.status,
        priority=task.priority,
        due_date=task.due_date.isoformat() if task.due_date else None,
        completed_at=task.completed_at.isoformat() if task.completed_at else None,
        tags=task.tags or [],
        sort_order=task.sort_order or 0,
        created_at=task.created_at.isoformat() if task.created_at else "",
        updated_at=task.updated_at.isoformat() if task.updated_at else "",
    )


async def _log_activity(
    db: AsyncSession,
    task_id: uuid.UUID,
    actor_id: uuid.UUID,
    action: str,
    field: str | None = None,
    old_value: str | None = None,
    new_value: str | None = None,
    metadata: dict | None = None,
) -> None:
    activity = TaskActivity(
        task_id=task_id,
        actor_id=actor_id,
        action=action,
        field=field,
        old_value=old_value,
        new_value=new_value,
        meta_data=metadata or {},
    )
    db.add(activity)


# ─── Task CRUD ────────────────────────────────────────

@router.post("", response_model=APIResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    req: TaskCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new task."""
    org_id = current_user.organization_id if hasattr(current_user, 'organization_id') else None
    # Default to first org member if not set
    if not org_id:
        from app.models.organization import OrganizationMember
        result = await db.execute(
            select(OrganizationMember).where(OrganizationMember.user_id == current_user.id)
        )
        member = result.scalar_one_or_none()
        if not member:
            raise HTTPException(400, "User is not a member of any organization")
        org_id = member.organization_id

    task = Task(
        organization_id=org_id,
        assigner_id=current_user.id,
        assignee_id=uuid.UUID(req.assignee_id) if req.assignee_id else None,
        title=req.title,
        description=req.description,
        priority=req.priority,
        due_date=req.due_date,
        tags=req.tags or [],
        project_id=uuid.UUID(req.project_id) if req.project_id else None,
    )
    db.add(task)
    await db.flush()

    await _log_activity(db, task.id, current_user.id, "task.created")
    return APIResponse(data=_task_to_response(task))


@router.get("", response_model=APIResponse)
async def list_tasks(
    status_filter: str | None = Query(None, alias="status"),
    assignee_id: str | None = Query(None),
    priority: str | None = Query(None),
    search: str | None = Query(None),
    project_id: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List tasks with filtering and pagination."""
    # Get user's org
    from app.models.organization import OrganizationMember
    result = await db.execute(
        select(OrganizationMember).where(OrganizationMember.user_id == current_user.id)
    )
    member = result.scalar_one_or_none()
    if not member:
        return APIResponse(data=[], pagination={"page": page, "page_size": page_size, "total": 0})
    org_id = member.organization_id

    query = select(Task).options(
        selectinload(Task.assigner), selectinload(Task.assignee)
    ).where(
        Task.organization_id == org_id,
        Task.deleted_at.is_(None),
    )

    if status_filter:
        statuses = [s.strip() for s in status_filter.split(",")]
        query = query.where(Task.status.in_(statuses))
    if assignee_id:
        query = query.where(Task.assignee_id == uuid.UUID(assignee_id))
    if priority:
        query = query.where(Task.priority == priority)
    if search:
        query = query.where(Task.title.ilike(f"%{search}%"))
    if project_id:
        query = query.where(Task.project_id == uuid.UUID(project_id))

    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    query = query.order_by(Task.sort_order, Task.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    tasks = result.scalars().all()

    return APIResponse(
        data=[_task_to_response(t) for t in tasks],
        pagination={"page": page, "page_size": page_size, "total": total},
    )


@router.get("/kanban", response_model=APIResponse)
async def get_kanban(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get tasks grouped by status for Kanban view."""
    from app.models.organization import OrganizationMember
    result = await db.execute(
        select(OrganizationMember).where(OrganizationMember.user_id == current_user.id)
    )
    member = result.scalar_one_or_none()
    if not member:
        return APIResponse(data=[])
    org_id = member.organization_id

    query = select(Task).options(
        selectinload(Task.assigner), selectinload(Task.assignee)
    ).where(
        Task.organization_id == org_id,
        Task.deleted_at.is_(None),
    ).order_by(Task.sort_order, Task.created_at.desc())

    result = await db.execute(query)
    tasks = result.scalars().all()

    columns = {}
    for task in tasks:
        col = task.status or "todo"
        if col not in columns:
            columns[col] = []
        columns[col].append(_task_to_response(task))

    kanban_data = [
        {"status": status, "tasks": task_list}
        for status, task_list in columns.items()
    ]

    return APIResponse(data=kanban_data)


@router.get("/my", response_model=APIResponse)
async def get_my_tasks(
    status_filter: str | None = Query(None, alias="status"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List tasks assigned to the current user."""
    from app.models.organization import OrganizationMember
    result = await db.execute(
        select(OrganizationMember).where(OrganizationMember.user_id == current_user.id)
    )
    member = result.scalar_one_or_none()
    if not member:
        return APIResponse(data=[])
    org_id = member.organization_id

    query = select(Task).options(
        selectinload(Task.assigner), selectinload(Task.assignee)
    ).where(
        Task.organization_id == org_id,
        Task.assignee_id == current_user.id,
        Task.deleted_at.is_(None),
    )

    if status_filter:
        statuses = [s.strip() for s in status_filter.split(",")]
        query = query.where(Task.status.in_(statuses))

    query = query.order_by(Task.created_at.desc())
    result = await db.execute(query)
    tasks = result.scalars().all()

    return APIResponse(data=[_task_to_response(t) for t in tasks])


@router.get("/{task_id}", response_model=APIResponse)
async def get_task(
    task_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get task details."""
    from app.models.organization import OrganizationMember
    result = await db.execute(
        select(OrganizationMember).where(OrganizationMember.user_id == current_user.id)
    )
    member = result.scalar_one_or_none()
    if not member:
        raise HTTPException(400, "Not a member of any organization")
    org_id = member.organization_id

    task = await _get_task_or_404(db, task_id, org_id)
    return APIResponse(data=_task_to_response(task))


@router.put("/{task_id}", response_model=APIResponse)
async def update_task(
    task_id: uuid.UUID,
    req: TaskUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update task fields."""
    from app.models.organization import OrganizationMember
    result = await db.execute(
        select(OrganizationMember).where(OrganizationMember.user_id == current_user.id)
    )
    member = result.scalar_one_or_none()
    if not member:
        raise HTTPException(400, "Not a member of any organization")
    org_id = member.organization_id

    task = await _get_task_or_404(db, task_id, org_id)

    update_data = req.model_dump(exclude_unset=True)
    changed_fields = []
    for key, val in update_data.items():
        if key == "assignee_id" and val:
            val = uuid.UUID(val)
        if key == "due_date" and val:
            val = datetime.fromisoformat(val) if isinstance(val, str) else val
        if key == "project_id" and val:
            val = uuid.UUID(val)
        old_val = getattr(task, key, None)
        if str(old_val) != str(val):
            changed_fields.append(key)
            setattr(task, key, val)

    if changed_fields:
        await _log_activity(
            db, task.id, current_user.id,
            "task.updated",
            field=",".join(changed_fields),
        )

    return APIResponse(data=_task_to_response(task))


@router.put("/{task_id}/status", response_model=APIResponse)
async def update_task_status(
    task_id: uuid.UUID,
    req: TaskStatusUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update task status."""
    from app.models.organization import OrganizationMember
    result = await db.execute(
        select(OrganizationMember).where(OrganizationMember.user_id == current_user.id)
    )
    member = result.scalar_one_or_none()
    if not member:
        raise HTTPException(400, "Not a member of any organization")
    org_id = member.organization_id

    task = await _get_task_or_404(db, task_id, org_id)

    old_status = task.status
    task.status = req.status

    if req.status == "done" and not task.completed_at:
        task.completed_at = datetime.now(timezone.utc)

    await _log_activity(
        db, task.id, current_user.id,
        "task.status_changed",
        field="status",
        old_value=old_status,
        new_value=req.status,
    )

    return APIResponse(data=_task_to_response(task))


@router.put("/{task_id}/reorder", response_model=APIResponse)
async def reorder_task(
    task_id: uuid.UUID,
    req: TaskReorder,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Reorder task within a column (Kanban drag & drop)."""
    from app.models.organization import OrganizationMember
    result = await db.execute(
        select(OrganizationMember).where(OrganizationMember.user_id == current_user.id)
    )
    member = result.scalar_one_or_none()
    if not member:
        raise HTTPException(400, "Not a member of any organization")
    org_id = member.organization_id

    task = await _get_task_or_404(db, task_id, org_id)
    old_status = task.status
    task.status = req.status
    task.sort_order = req.sort_order

    await _log_activity(
        db, task.id, current_user.id,
        "task.reordered",
        field="status",
        old_value=old_status,
        new_value=req.status,
    )

    return APIResponse(data=_task_to_response(task))


@router.delete("/{task_id}", response_model=APIResponse)
async def delete_task(
    task_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Soft-delete a task."""
    from app.models.organization import OrganizationMember
    result = await db.execute(
        select(OrganizationMember).where(OrganizationMember.user_id == current_user.id)
    )
    member = result.scalar_one_or_none()
    if not member:
        raise HTTPException(400, "Not a member of any organization")
    org_id = member.organization_id

    task = await _get_task_or_404(db, task_id, org_id)
    task.deleted_at = datetime.now(timezone.utc)

    await _log_activity(db, task.id, current_user.id, "task.deleted")
    return APIResponse(message="Task deleted")


# ─── Subtasks ────────────────────────────────────────

@router.post("/{task_id}/subtasks", response_model=APIResponse, status_code=201)
async def create_subtask(
    task_id: uuid.UUID,
    req: SubtaskCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.models.organization import OrganizationMember
    result = await db.execute(
        select(OrganizationMember).where(OrganizationMember.user_id == current_user.id)
    )
    member = result.scalar_one_or_none()
    if not member:
        raise HTTPException(400, "Not a member of any organization")
    await _get_task_or_404(db, task_id, member.organization_id)

    subtask = TaskSubtask(
        task_id=task_id,
        title=req.title,
        assignee_id=uuid.UUID(req.assignee_id) if req.assignee_id else None,
    )
    db.add(subtask)
    await db.flush()

    await _log_activity(db, task_id, current_user.id, "subtask.created")
    return APIResponse(data=_subtask_to_response(subtask))


def _subtask_to_response(s: TaskSubtask) -> SubtaskResponse:
    return SubtaskResponse(
        id=str(s.id),
        task_id=str(s.task_id),
        title=s.title,
        is_done=s.is_done,
        sort_order=s.sort_order or 0,
        assignee_id=str(s.assignee_id) if s.assignee_id else None,
        assignee_name=s.assignee.display_name if hasattr(s, 'assignee') and s.assignee else None,
        created_at=s.created_at.isoformat() if s.created_at else "",
        updated_at=s.updated_at.isoformat() if s.updated_at else "",
    )


@router.get("/{task_id}/subtasks", response_model=APIResponse)
async def list_subtasks(
    task_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.models.organization import OrganizationMember
    result = await db.execute(
        select(OrganizationMember).where(OrganizationMember.user_id == current_user.id)
    )
    member = result.scalar_one_or_none()
    if not member:
        return APIResponse(data=[])
    await _get_task_or_404(db, task_id, member.organization_id)

    result = await db.execute(
        select(TaskSubtask).options(
            selectinload(TaskSubtask.assignee)
        ).where(TaskSubtask.task_id == task_id).order_by(TaskSubtask.sort_order)
    )
    subtasks = result.scalars().all()
    return APIResponse(data=[_subtask_to_response(s) for s in subtasks])


@router.put("/{task_id}/subtasks/{subtask_id}", response_model=APIResponse)
async def update_subtask(
    task_id: uuid.UUID,
    subtask_id: uuid.UUID,
    req: SubtaskUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.models.organization import OrganizationMember
    result = await db.execute(
        select(OrganizationMember).where(OrganizationMember.user_id == current_user.id)
    )
    member = result.scalar_one_or_none()
    if not member:
        raise HTTPException(400, "Not a member of any organization")
    await _get_task_or_404(db, task_id, member.organization_id)

    result = await db.execute(
        select(TaskSubtask).where(TaskSubtask.id == subtask_id, TaskSubtask.task_id == task_id)
    )
    subtask = result.scalar_one_or_none()
    if not subtask:
        raise HTTPException(404, "Subtask not found")

    update_data = req.model_dump(exclude_unset=True)
    for key, val in update_data.items():
        if key == "assignee_id" and val:
            val = uuid.UUID(val)
        setattr(subtask, key, val)

    await _log_activity(db, task_id, current_user.id, "subtask.updated")
    return APIResponse(data=_subtask_to_response(subtask))


@router.delete("/{task_id}/subtasks/{subtask_id}", response_model=APIResponse)
async def delete_subtask(
    task_id: uuid.UUID,
    subtask_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.models.organization import OrganizationMember
    result = await db.execute(
        select(OrganizationMember).where(OrganizationMember.user_id == current_user.id)
    )
    member = result.scalar_one_or_none()
    if not member:
        raise HTTPException(400, "Not a member of any organization")
    await _get_task_or_404(db, task_id, member.organization_id)

    result = await db.execute(
        select(TaskSubtask).where(TaskSubtask.id == subtask_id, TaskSubtask.task_id == task_id)
    )
    subtask = result.scalar_one_or_none()
    if not subtask:
        raise HTTPException(404, "Subtask not found")

    await db.delete(subtask)
    await _log_activity(db, task_id, current_user.id, "subtask.deleted")
    return APIResponse(message="Subtask deleted")


# ─── Comments ─────────────────────────────────────────

@router.post("/{task_id}/comments", response_model=APIResponse, status_code=201)
async def create_comment(
    task_id: uuid.UUID,
    req: CommentCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Add a comment to a task."""
    from app.models.organization import OrganizationMember
    result = await db.execute(
        select(OrganizationMember).where(OrganizationMember.user_id == current_user.id)
    )
    member = result.scalar_one_or_none()
    if not member:
        raise HTTPException(400, "Not a member of any organization")
    await _get_task_or_404(db, task_id, member.organization_id)

    comment = TaskComment(
        task_id=task_id,
        author_id=current_user.id,
        parent_id=uuid.UUID(req.parent_id) if req.parent_id else None,
        content=req.content,
        mentions=[uuid.UUID(m) for m in req.mentions] if req.mentions else [],
    )
    db.add(comment)
    await db.flush()

    await _log_activity(db, task_id, current_user.id, "comment.created",
                        metadata={"comment_id": str(comment.id)})
    return APIResponse(data=_comment_to_response(comment))


def _comment_to_response(c: TaskComment) -> CommentResponse:
    return CommentResponse(
        id=str(c.id),
        task_id=str(c.task_id),
        author_id=str(c.author_id),
        author_name=c.author.display_name if hasattr(c, 'author') and c.author else None,
        author_avatar=c.author.avatar_url if hasattr(c, 'author') and c.author else None,
        parent_id=str(c.parent_id) if c.parent_id else None,
        content=c.content,
        mentions=[str(m) for m in c.mentions] if c.mentions else [],
        created_at=c.created_at.isoformat() if c.created_at else "",
        updated_at=c.updated_at.isoformat() if c.updated_at else "",
    )


@router.get("/{task_id}/comments", response_model=APIResponse)
async def list_comments(
    task_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List comments for a task."""
    from app.models.organization import OrganizationMember
    result = await db.execute(
        select(OrganizationMember).where(OrganizationMember.user_id == current_user.id)
    )
    member = result.scalar_one_or_none()
    if not member:
        return APIResponse(data=[])
    await _get_task_or_404(db, task_id, member.organization_id)

    result = await db.execute(
        select(TaskComment).options(selectinload(TaskComment.author))
        .where(TaskComment.task_id == task_id, TaskComment.deleted_at.is_(None))
        .order_by(TaskComment.created_at)
    )
    comments = result.scalars().all()
    return APIResponse(data=[_comment_to_response(c) for c in comments])


@router.put("/{task_id}/comments/{comment_id}", response_model=APIResponse)
async def update_comment(
    task_id: uuid.UUID,
    comment_id: uuid.UUID,
    req: CommentUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Edit a comment."""
    result = await db.execute(
        select(TaskComment).options(
            selectinload(TaskComment.author)
        ).where(
            TaskComment.id == comment_id,
            TaskComment.task_id == task_id,
            TaskComment.author_id == current_user.id,
            TaskComment.deleted_at.is_(None),
        )
    )
    comment = result.scalar_one_or_none()
    if not comment:
        raise HTTPException(404, "Comment not found or not editable")

    comment.content = req.content
    return APIResponse(data=_comment_to_response(comment))


@router.delete("/{task_id}/comments/{comment_id}", response_model=APIResponse)
async def delete_comment(
    task_id: uuid.UUID,
    comment_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Soft-delete a comment."""
    result = await db.execute(
        select(TaskComment).options(
            selectinload(TaskComment.author)
        ).where(
            TaskComment.id == comment_id,
            TaskComment.task_id == task_id,
            TaskComment.author_id == current_user.id,
            TaskComment.deleted_at.is_(None),
        )
    )
    comment = result.scalar_one_or_none()
    if not comment:
        raise HTTPException(404, "Comment not found or not deletable")

    comment.deleted_at = datetime.now(timezone.utc)
    return APIResponse(message="Comment deleted")


# ─── Activities ───────────────────────────────────────

@router.get("/{task_id}/activities", response_model=APIResponse)
async def list_activities(
    task_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List activity log for a task."""
    from app.models.organization import OrganizationMember
    result = await db.execute(
        select(OrganizationMember).where(OrganizationMember.user_id == current_user.id)
    )
    member = result.scalar_one_or_none()
    if not member:
        return APIResponse(data=[])
    await _get_task_or_404(db, task_id, member.organization_id)

    result = await db.execute(
        select(TaskActivity).options(selectinload(TaskActivity.actor))
        .where(TaskActivity.task_id == task_id)
        .order_by(TaskActivity.created_at.desc())
        .limit(100)
    )
    activities = result.scalars().all()

    return APIResponse(data=[
        ActivityResponse(
            id=str(a.id),
            task_id=str(a.task_id),
            actor_id=str(a.actor_id),
            actor_name=a.actor.display_name if a.actor else None,
            action=a.action,
            field=a.field,
            old_value=a.old_value,
            new_value=a.new_value,
            meta_data=a.meta_data,
            created_at=a.created_at.isoformat() if a.created_at else "",
        )
        for a in activities
    ])
