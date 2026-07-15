"""Training management API routes."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.core.deps import get_current_user
from app.database import get_db
from app.models.auth import User
from app.models.hr import Employee
from app.models.organization import OrganizationMember
from app.models.training import TrainingCourse, TrainingEnrollment
from app.schemas.auth import APIResponse
from app.schemas.training import (
    TrainingCourseCreate,
    TrainingCourseResponse,
    TrainingCourseUpdate,
    TrainingEnrollmentResponse,
    TrainingEnrollRequest,
    TrainingEnrollmentUpdate,
)

router = APIRouter(prefix="/training", tags=["training"])


async def _get_org_id(db, user_id):
    result = await db.execute(
        select(OrganizationMember).where(OrganizationMember.user_id == user_id)
    )
    membership = result.scalar_one_or_none()
    return str(membership.organization_id) if membership else None


async def _get_enrollment_count(db, course_id):
    result = await db.execute(
        select(func.count()).select_from(TrainingEnrollment)
        .where(TrainingEnrollment.course_id == course_id)
    )
    return result.scalar() or 0


def _course_to_response(c, enrollment_count=0):
    return TrainingCourseResponse(
        id=str(c.id),
        organization_id=str(c.organization_id),
        title=c.title,
        description=c.description,
        instructor=c.instructor,
        start_date=c.start_date.isoformat() if c.start_date else None,
        end_date=c.end_date.isoformat() if c.end_date else None,
        duration_hours=float(c.duration_hours) if c.duration_hours else None,
        max_participants=c.max_participants,
        location=c.location,
        status=c.status,
        category=c.category,
        enrollment_count=enrollment_count,
        created_by=str(c.created_by),
        created_at=c.created_at.isoformat() if c.created_at else "",
        updated_at=c.updated_at.isoformat() if c.updated_at else "",
    )


@router.post("/courses", response_model=APIResponse, status_code=status.HTTP_201_CREATED)
async def create_course(
    req: TrainingCourseCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new training course."""
    org_id = await _get_org_id(db, current_user.id)
    if not org_id:
        raise HTTPException(status_code=400, detail="User not in any organization")

    course = TrainingCourse(
        organization_id=uuid.UUID(org_id),
        title=req.title,
        description=req.description,
        instructor=req.instructor,
        start_date=req.start_date,
        end_date=req.end_date,
        duration_hours=req.duration_hours,
        max_participants=req.max_participants,
        location=req.location,
        category=req.category,
        status="draft",
        created_by=current_user.id,
    )
    db.add(course)
    await db.flush()

    return APIResponse(data=_course_to_response(course))


@router.get("/courses", response_model=APIResponse)
async def list_courses(
    status_filter: str | None = Query(None, alias="status"),
    category: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List training courses."""
    org_id = await _get_org_id(db, current_user.id)
    if not org_id:
        return APIResponse(data={"data": [], "pagination": {"page": page, "page_size": page_size, "total": 0}})

    query = select(TrainingCourse).where(
        TrainingCourse.organization_id == org_id,
    )

    if status_filter:
        statuses = [s.strip() for s in status_filter.split(",")]
        query = query.where(TrainingCourse.status.in_(statuses))
    if category:
        query = query.where(TrainingCourse.category == category)

    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    query = query.order_by(TrainingCourse.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    courses = result.scalars().all()

    data = []
    for c in courses:
        ec = await _get_enrollment_count(db, c.id)
        data.append(_course_to_response(c, ec))

    return APIResponse(data={
        "data": data,
        "pagination": {"page": page, "page_size": page_size, "total": total},
    })


@router.get("/courses/{course_id}", response_model=APIResponse)
async def get_course(
    course_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get course details."""
    result = await db.execute(select(TrainingCourse).where(TrainingCourse.id == course_id))
    course = result.scalar_one_or_none()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    ec = await _get_enrollment_count(db, course.id)
    return APIResponse(data=_course_to_response(course, ec))


@router.put("/courses/{course_id}", response_model=APIResponse)
async def update_course(
    course_id: uuid.UUID,
    req: TrainingCourseUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a training course."""
    result = await db.execute(select(TrainingCourse).where(TrainingCourse.id == course_id))
    course = result.scalar_one_or_none()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    if req.title is not None:
        course.title = req.title
    if req.description is not None:
        course.description = req.description
    if req.instructor is not None:
        course.instructor = req.instructor
    if req.start_date is not None:
        course.start_date = req.start_date
    if req.end_date is not None:
        course.end_date = req.end_date
    if req.duration_hours is not None:
        course.duration_hours = req.duration_hours
    if req.max_participants is not None:
        course.max_participants = req.max_participants
    if req.location is not None:
        course.location = req.location
    if req.status is not None:
        course.status = req.status
    if req.category is not None:
        course.category = req.category

    db.add(course)
    await db.flush()

    ec = await _get_enrollment_count(db, course.id)
    return APIResponse(data=_course_to_response(course, ec))


@router.delete("/courses/{course_id}", response_model=APIResponse)
async def delete_course(
    course_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a training course."""
    result = await db.execute(select(TrainingCourse).where(TrainingCourse.id == course_id))
    course = result.scalar_one_or_none()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    await db.delete(course)
    await db.flush()
    return APIResponse(data={"message": "Course deleted"})


# ─── Training Enrollments ─────────────────────────────────

@router.post("/courses/{course_id}/enroll", response_model=APIResponse)
async def enroll_employees(
    course_id: uuid.UUID,
    req: TrainingEnrollRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Enroll employees in a training course."""
    result = await db.execute(select(TrainingCourse).where(TrainingCourse.id == course_id))
    course = result.scalar_one_or_none()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    enrolled = []
    for emp_id_str in req.employee_ids:
        emp_id = uuid.UUID(emp_id_str)
        # Check not already enrolled
        existing = await db.execute(
            select(TrainingEnrollment).where(
                TrainingEnrollment.course_id == course_id,
                TrainingEnrollment.employee_id == emp_id,
            )
        )
        if existing.scalar_one_or_none():
            continue

        enrollment = TrainingEnrollment(
            course_id=course_id,
            employee_id=emp_id,
            status="enrolled",
        )
        db.add(enrollment)
        enrolled.append(emp_id_str)

    await db.flush()
    return APIResponse(data={"message": f"{len(enrolled)} employees enrolled", "count": len(enrolled)})


@router.get("/courses/{course_id}/enrollments", response_model=APIResponse)
async def list_enrollments(
    course_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List enrollments for a course."""
    result = await db.execute(
        select(TrainingEnrollment)
        .options(joinedload(TrainingEnrollment.employee).joinedload(Employee.user))
        .where(TrainingEnrollment.course_id == course_id)
        .order_by(TrainingEnrollment.created_at.desc())
    )
    enrollments = result.scalars().all()

    return APIResponse(data=[TrainingEnrollmentResponse(
        id=str(e.id),
        course_id=str(e.course_id),
        employee_id=str(e.employee_id),
        employee_name=e.employee.user.display_name if e.employee and e.employee.user else None,
        employee_no=e.employee.employee_no if e.employee else None,
        status=e.status,
        attended=e.attended,
        score=float(e.score) if e.score else None,
        feedback=e.feedback,
        completed_at=e.completed_at.isoformat() if e.completed_at else None,
        created_at=e.created_at.isoformat() if e.created_at else "",
    ) for e in enrollments])


@router.put("/enrollments/{enrollment_id}", response_model=APIResponse)
async def update_enrollment(
    enrollment_id: uuid.UUID,
    req: TrainingEnrollmentUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update enrollment (attendance, score, feedback)."""
    result = await db.execute(
        select(TrainingEnrollment).where(TrainingEnrollment.id == enrollment_id)
    )
    enrollment = result.scalar_one_or_none()
    if not enrollment:
        raise HTTPException(status_code=404, detail="Enrollment not found")

    if req.attended is not None:
        enrollment.attended = req.attended
    if req.score is not None:
        enrollment.score = req.score
    if req.feedback is not None:
        enrollment.feedback = req.feedback
    if req.status is not None:
        enrollment.status = req.status
    if req.status == "completed":
        enrollment.completed_at = datetime.now(timezone.utc)

    db.add(enrollment)
    await db.flush()
    return APIResponse(data={"message": "Enrollment updated"})
