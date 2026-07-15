"""Training management API routes: courses, plans, instructors, materials, registrations, evaluations, certificates."""
from __future__ import annotations

import asyncio

import asyncio

import uuid
from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.core.deps import get_current_user
from app.database import get_db
from app.models.auth import User
from app.models.hr import Employee
from app.models.organization import OrganizationMember
from app.models.training import (
    TrainingCertificate,
    TrainingCourse,
    TrainingEvaluation,
    TrainingInstructor,
    TrainingMaterial,
    TrainingPlan,
    TrainingRegistration,
)
from app.schemas.auth import APIResponse
from app.schemas.training import (
    CertificateIssue,
    CertificateResponse,
    CertificateUpdate,
    CourseCreate,
    CourseDetailResponse,
    CourseResponse,
    CourseUpdate,
    EvaluationCreate,
    EvaluationResponse,
    InstructorCreate,
    InstructorResponse,
    InstructorUpdate,
    MaterialCreate,
    MaterialResponse,
    MaterialUpdate,
    PlanBriefResponse,
    PlanCreate,
    PlanResponse,
    PlanUpdate,
    RegistrationCheckIn,
    RegistrationCheckOut,
    RegistrationCreate,
    RegistrationResponse,
    RegistrationUpdate,
    PaginatedCertificateResponse,
    PaginatedCourseResponse,
    PaginatedInstructorResponse,
    PaginatedPlanResponse,
    PaginatedRegistrationResponse,
)

router = APIRouter(prefix="/hr/training", tags=["training"])


# ─── Helper functions ───────────────────────────────────────

async def _get_org_id(db: AsyncSession, current_user: User) -> uuid.UUID:
    """Get the user's organization ID."""
    result = await db.execute(
        select(OrganizationMember).where(OrganizationMember.user_id == current_user.id)
    )
    membership = result.scalar_one_or_none()
    if not membership:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User not in any organization")
    return membership.organization_id


async def _get_employee(db: AsyncSession, org_id: uuid.UUID, current_user: User) -> Employee | None:
    """Get the employee record for the current user."""
    result = await db.execute(
        select(Employee).options(
            joinedload(Employee.user), joinedload(Employee.department)
        ).where(
            Employee.user_id == current_user.id,
            Employee.organization_id == org_id,
            Employee.deleted_at.is_(None),
        )
    )
    return result.scalar_one_or_none()


async def _verify_course_exists(db: AsyncSession, course_id: uuid.UUID) -> TrainingCourse:
    result = await db.execute(
        select(TrainingCourse).where(
            TrainingCourse.id == course_id,
            TrainingCourse.deleted_at.is_(None),
        )
    )
    course = result.scalar_one_or_none()
    if not course:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")
    return course


async def _verify_plan_exists(db: AsyncSession, plan_id: uuid.UUID) -> TrainingPlan:
    result = await db.execute(
        select(TrainingPlan).where(
            TrainingPlan.id == plan_id,
            TrainingPlan.deleted_at.is_(None),
        )
    )
    plan = result.scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Training plan not found")
    return plan


# ─── Training Instructors ──────────────────────────────────

@router.post("/instructors", response_model=APIResponse, status_code=status.HTTP_201_CREATED)
async def create_instructor(
    req: InstructorCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a training instructor profile."""
    org_id = await _get_org_id(db, current_user)

    instructor = TrainingInstructor(
        organization_id=org_id,
        name=req.name,
        employee_id=uuid.UUID(req.employee_id) if req.employee_id else None,
        title=req.title,
        expertise=req.expertise,
        bio=req.bio,
        phone=req.phone,
        email=req.email,
        is_external=req.is_external,
    )
    db.add(instructor)
    await db.flush()

    return APIResponse(data=_instructor_to_response(instructor))


@router.get("/instructors", response_model=APIResponse)
async def list_instructors(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status_filter: str | None = Query(None, alias="status"),
    search: str | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List training instructors."""
    org_id = await _get_org_id(db, current_user)

    query = select(TrainingInstructor).where(
        TrainingInstructor.organization_id == org_id,
        TrainingInstructor.deleted_at.is_(None),
    )

    if status_filter:
        statuses = [s.strip() for s in status_filter.split(",")]
        query = query.where(TrainingInstructor.status.in_(statuses))
    if search:
        query = query.where(
            or_(
                TrainingInstructor.name.ilike(f"%{search}%"),
                TrainingInstructor.title.ilike(f"%{search}%"),
                TrainingInstructor.expertise.ilike(f"%{search}%"),
            )
        )

    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    query = query.order_by(TrainingInstructor.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    instructors = result.scalars().all()

    return APIResponse(data={
        "data": [_instructor_to_response(i) for i in instructors],
        "pagination": {"page": page, "page_size": page_size, "total": total},
    })


@router.get("/instructors/{instructor_id}", response_model=APIResponse)
async def get_instructor(
    instructor_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get instructor details."""
    result = await db.execute(
        select(TrainingInstructor).where(
            TrainingInstructor.id == instructor_id,
            TrainingInstructor.deleted_at.is_(None),
        )
    )
    instructor = result.scalar_one_or_none()
    if not instructor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Instructor not found")
    return APIResponse(data=_instructor_to_response(instructor))


@router.put("/instructors/{instructor_id}", response_model=APIResponse)
async def update_instructor(
    instructor_id: uuid.UUID,
    req: InstructorUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update instructor profile."""
    result = await db.execute(
        select(TrainingInstructor).where(
            TrainingInstructor.id == instructor_id,
            TrainingInstructor.deleted_at.is_(None),
        )
    )
    instructor = result.scalar_one_or_none()
    if not instructor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Instructor not found")

    if req.name is not None:
        instructor.name = req.name
    if req.employee_id is not None:
        instructor.employee_id = uuid.UUID(req.employee_id) if req.employee_id else None
    if req.title is not None:
        instructor.title = req.title
    if req.expertise is not None:
        instructor.expertise = req.expertise
    if req.bio is not None:
        instructor.bio = req.bio
    if req.phone is not None:
        instructor.phone = req.phone
    if req.email is not None:
        instructor.email = req.email
    if req.is_external is not None:
        instructor.is_external = req.is_external
    if req.status is not None:
        instructor.status = req.status

    db.add(instructor)
    await db.flush()
    return APIResponse(data=_instructor_to_response(instructor))


def _instructor_to_response(i: TrainingInstructor) -> InstructorResponse:
    return InstructorResponse(
        id=str(i.id),
        organization_id=str(i.organization_id),
        name=i.name,
        employee_id=str(i.employee_id) if i.employee_id else None,
        title=i.title,
        expertise=i.expertise,
        bio=i.bio,
        phone=i.phone,
        email=i.email,
        is_external=i.is_external,
        status=i.status,
        created_at=i.created_at.isoformat() if i.created_at else "",
        updated_at=i.updated_at.isoformat() if i.updated_at else "",
    )


# ─── Training Courses ─────────────────────────────────────

@router.post("/courses", response_model=APIResponse, status_code=status.HTTP_201_CREATED)
async def create_course(
    req: CourseCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new training course."""
    org_id = await _get_org_id(db, current_user)

    course = TrainingCourse(
        organization_id=org_id,
        title=req.title,
        description=req.description,
        category=req.category,
        duration_hours=req.duration_hours,
        max_participants=req.max_participants,
        credits=req.credits,
        cover_url=req.cover_url,
        created_by=current_user.id,
    )
    db.add(course)
    await db.flush()

    return APIResponse(data=await _course_to_response(db, course))


@router.get("/courses", response_model=APIResponse)
async def list_courses(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    category: str | None = None,
    status_filter: str | None = Query(None, alias="status"),
    search: str | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List training courses with filtering."""
    org_id = await _get_org_id(db, current_user)

    query = select(TrainingCourse).where(
        TrainingCourse.organization_id == org_id,
        TrainingCourse.deleted_at.is_(None),
    )

    if category:
        query = query.where(TrainingCourse.category == category)
    if status_filter:
        statuses = [s.strip() for s in status_filter.split(",")]
        query = query.where(TrainingCourse.status.in_(statuses))
    if search:
        query = query.where(
            or_(
                TrainingCourse.title.ilike(f"%{search}%"),
                TrainingCourse.description.ilike(f"%{search}%"),
            )
        )

    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    query = query.order_by(TrainingCourse.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    courses = result.scalars().all()

    results = []
    for c in courses:
        results.append(await _course_to_response(db, c))

    return APIResponse(data={
        "data": results,
        "pagination": {"page": page, "page_size": page_size, "total": total},
    })


@router.get("/courses/{course_id}", response_model=APIResponse)
async def get_course(
    course_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get course details with plans and materials."""
    course = await _verify_course_exists(db, course_id)

    # Load plans
    plans_result = await db.execute(
        select(TrainingPlan).options(
            joinedload(TrainingPlan.instructor)
        ).where(
            TrainingPlan.course_id == course_id,
            TrainingPlan.deleted_at.is_(None),
        ).order_by(TrainingPlan.start_date.desc())
    )
    plans = plans_result.scalars().all()

    # Load materials
    materials_result = await db.execute(
        select(TrainingMaterial).where(
            TrainingMaterial.course_id == course_id,
        ).order_by(TrainingMaterial.sort_order)
    )
    materials = materials_result.scalars().all()

    course_data = await _course_to_response(db, course)
    return APIResponse(data={
        **course_data.model_dump(),
        "plans": [_plan_to_brief(p) for p in plans],
        "materials": [_material_to_response(m) for m in materials],
    })


@router.put("/courses/{course_id}", response_model=APIResponse)
async def update_course(
    course_id: uuid.UUID,
    req: CourseUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update training course."""
    course = await _verify_course_exists(db, course_id)

    if req.title is not None:
        course.title = req.title
    if req.description is not None:
        course.description = req.description
    if req.category is not None:
        course.category = req.category
    if req.duration_hours is not None:
        course.duration_hours = req.duration_hours
    if req.max_participants is not None:
        course.max_participants = req.max_participants
    if req.credits is not None:
        course.credits = req.credits
    if req.cover_url is not None:
        course.cover_url = req.cover_url
    if req.status is not None:
        course.status = req.status

    db.add(course)
    await db.flush()
    return APIResponse(data=await _course_to_response(db, course))


async def _course_to_response(db: AsyncSession, c: TrainingCourse) -> CourseResponse:
    return CourseResponse(
        id=str(c.id),
        organization_id=str(c.organization_id),
        title=c.title,
        description=c.description,
        category=c.category,
        duration_hours=float(c.duration_hours) if c.duration_hours else None,
        max_participants=c.max_participants,
        credits=float(c.credits) if c.credits else None,
        status=c.status,
        cover_url=c.cover_url,
        created_by=str(c.created_by),
        created_at=c.created_at.isoformat() if c.created_at else "",
        updated_at=c.updated_at.isoformat() if c.updated_at else "",
    )


# ─── Training Plans ───────────────────────────────────────

@router.post("/plans", response_model=APIResponse, status_code=status.HTTP_201_CREATED)
async def create_plan(
    req: PlanCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new training plan (scheduled session)."""
    await _get_org_id(db, current_user)
    await _verify_course_exists(db, uuid.UUID(req.course_id))

    if req.end_date < req.start_date:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="End date must be after start date")

    plan = TrainingPlan(
        course_id=uuid.UUID(req.course_id),
        title=req.title,
        start_date=req.start_date,
        end_date=req.end_date,
        start_time=req.start_time,
        end_time=req.end_time,
        location=req.location,
        instructor_id=uuid.UUID(req.instructor_id) if req.instructor_id else None,
        max_participants=req.max_participants,
        notes=req.notes,
    )
    db.add(plan)
    await db.flush()

    return APIResponse(data=await _plan_to_response(db, plan))


@router.get("/plans", response_model=APIResponse)
async def list_plans(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    course_id: str | None = None,
    status_filter: str | None = Query(None, alias="status"),
    date_from: date | None = None,
    date_to: date | None = None,
    search: str | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List training plans with filtering."""
    org_id = await _get_org_id(db, current_user)

    query = select(TrainingPlan).options(
        joinedload(TrainingPlan.course),
        joinedload(TrainingPlan.instructor),
    ).join(
        TrainingCourse,
        TrainingPlan.course_id == TrainingCourse.id,
    ).where(
        TrainingCourse.organization_id == org_id,
        TrainingCourse.deleted_at.is_(None),
        TrainingPlan.deleted_at.is_(None),
    )

    if course_id:
        query = query.where(TrainingPlan.course_id == uuid.UUID(course_id))
    if status_filter:
        statuses = [s.strip() for s in status_filter.split(",")]
        query = query.where(TrainingPlan.status.in_(statuses))
    if date_from:
        query = query.where(TrainingPlan.start_date >= date_from)
    if date_to:
        query = query.where(TrainingPlan.end_date <= date_to)
    if search:
        query = query.where(
            or_(
                TrainingPlan.title.ilike(f"%{search}%"),
                TrainingPlan.location.ilike(f"%{search}%"),
            )
        )

    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    query = query.order_by(TrainingPlan.start_date.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    plans = result.scalars().all()

    results = []
    for p in plans:
        results.append(await _plan_to_response(db, p))

    return APIResponse(data={
        "data": results,
        "pagination": {"page": page, "page_size": page_size, "total": total},
    })


@router.get("/plans/{plan_id}", response_model=APIResponse)
async def get_plan(
    plan_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get training plan details."""
    result = await db.execute(
        select(TrainingPlan).options(
            joinedload(TrainingPlan.course),
            joinedload(TrainingPlan.instructor),
        ).where(
            TrainingPlan.id == plan_id,
            TrainingPlan.deleted_at.is_(None),
        )
    )
    plan = result.scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Training plan not found")

    return APIResponse(data=await _plan_to_response(db, plan))


@router.put("/plans/{plan_id}", response_model=APIResponse)
async def update_plan(
    plan_id: uuid.UUID,
    req: PlanUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update training plan."""
    plan = await _verify_plan_exists(db, plan_id)

    if req.title is not None:
        plan.title = req.title
    if req.start_date is not None:
        plan.start_date = req.start_date
    if req.end_date is not None:
        plan.end_date = req.end_date
    if req.start_time is not None:
        plan.start_time = req.start_time
    if req.end_time is not None:
        plan.end_time = req.end_time
    if req.location is not None:
        plan.location = req.location
    if req.instructor_id is not None:
        plan.instructor_id = uuid.UUID(req.instructor_id) if req.instructor_id else None
    if req.max_participants is not None:
        plan.max_participants = req.max_participants
    if req.status is not None:
        plan.status = req.status
    if req.notes is not None:
        plan.notes = req.notes

    db.add(plan)
    await db.flush()
    return APIResponse(data=await _plan_to_response(db, plan))


async def _plan_to_response(db: AsyncSession, p: TrainingPlan) -> PlanResponse:
    # Count registrations
    count_result = await db.execute(
        select(func.count()).select_from(TrainingRegistration).where(
            TrainingRegistration.plan_id == p.id,
            TrainingRegistration.status.in_(["registered", "attended", "completed"]),
        )
    )
    registered_count = count_result.scalar() or 0

    return PlanResponse(
        id=str(p.id),
        course_id=str(p.course_id),
        course_title=p.course.title if p.course else None,
        title=p.title,
        start_date=p.start_date.isoformat(),
        end_date=p.end_date.isoformat(),
        start_time=p.start_time,
        end_time=p.end_time,
        location=p.location,
        instructor_id=str(p.instructor_id) if p.instructor_id else None,
        instructor_name=p.instructor.name if p.instructor else None,
        max_participants=p.max_participants,
        registered_count=registered_count,
        status=p.status,
        notes=p.notes,
        created_at=p.created_at.isoformat() if p.created_at else "",
        updated_at=p.updated_at.isoformat() if p.updated_at else "",
    )


def _plan_to_brief(p: TrainingPlan) -> PlanBriefResponse:
    return PlanBriefResponse(
        id=str(p.id),
        title=p.title,
        start_date=p.start_date.isoformat(),
        end_date=p.end_date.isoformat(),
        status=p.status,
    )


# ─── Training Materials ──────────────────────────────────

@router.post("/courses/{course_id}/materials", response_model=APIResponse, status_code=status.HTTP_201_CREATED)
async def create_material(
    course_id: uuid.UUID,
    req: MaterialCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Add material to a training course."""
    await _verify_course_exists(db, course_id)

    material = TrainingMaterial(
        course_id=course_id,
        name=req.name,
        type=req.type,
        file_url=req.file_url,
        description=req.description,
        sort_order=req.sort_order,
    )
    db.add(material)
    await db.flush()
    return APIResponse(data=_material_to_response(material))


@router.get("/courses/{course_id}/materials", response_model=APIResponse)
async def list_materials(
    course_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List materials for a course."""
    await _verify_course_exists(db, course_id)

    result = await db.execute(
        select(TrainingMaterial).where(
            TrainingMaterial.course_id == course_id,
        ).order_by(TrainingMaterial.sort_order)
    )
    materials = result.scalars().all()
    return APIResponse(data=[_material_to_response(m) for m in materials])


@router.put("/materials/{material_id}", response_model=APIResponse)
async def update_material(
    material_id: uuid.UUID,
    req: MaterialUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update course material."""
    result = await db.execute(select(TrainingMaterial).where(TrainingMaterial.id == material_id))
    material = result.scalar_one_or_none()
    if not material:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Material not found")

    if req.name is not None:
        material.name = req.name
    if req.type is not None:
        material.type = req.type
    if req.file_url is not None:
        material.file_url = req.file_url
    if req.description is not None:
        material.description = req.description
    if req.sort_order is not None:
        material.sort_order = req.sort_order

    db.add(material)
    await db.flush()
    return APIResponse(data=_material_to_response(material))


@router.delete("/materials/{material_id}", response_model=APIResponse)
async def delete_material(
    material_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete course material."""
    result = await db.execute(select(TrainingMaterial).where(TrainingMaterial.id == material_id))
    material = result.scalar_one_or_none()
    if not material:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Material not found")

    await db.delete(material)
    await db.flush()
    return APIResponse(data={"message": "Material deleted"})


def _material_to_response(m: TrainingMaterial) -> MaterialResponse:
    return MaterialResponse(
        id=str(m.id),
        course_id=str(m.course_id),
        name=m.name,
        type=m.type,
        file_url=m.file_url,
        description=m.description,
        sort_order=m.sort_order,
        created_at=m.created_at.isoformat() if m.created_at else "",
        updated_at=m.updated_at.isoformat() if m.updated_at else "",
    )


# ─── Training Registrations ──────────────────────────────

@router.post("/registrations", response_model=APIResponse, status_code=status.HTTP_201_CREATED)
async def register_for_training(
    req: RegistrationCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Register current user for a training plan."""
    org_id = await _get_org_id(db, current_user)
    emp = await _get_employee(db, org_id, current_user)
    if not emp:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Employee profile not found")

    plan = await _verify_plan_exists(db, uuid.UUID(req.plan_id))
    if plan.status not in ("open", "in_progress"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Training plan is not open for registration")

    # Check capacity
    count_result = await db.execute(
        select(func.count()).select_from(TrainingRegistration).where(
            TrainingRegistration.plan_id == plan.id,
            TrainingRegistration.status.in_(["registered", "attended", "completed"]),
        )
    )
    current_count = count_result.scalar() or 0
    max_participants = plan.max_participants or (plan.course.max_participants if plan.course else None)
    if max_participants and current_count >= max_participants:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Training plan is fully booked")

    # Check duplicate registration
    dup_result = await db.execute(
        select(TrainingRegistration).where(
            TrainingRegistration.plan_id == plan.id,
            TrainingRegistration.employee_id == emp.id,
            TrainingRegistration.status.in_(["registered", "attended", "completed"]),
        )
    )
    if dup_result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Already registered for this training")

    registration = TrainingRegistration(
        plan_id=plan.id,
        employee_id=emp.id,
        status="registered",
    )
    db.add(registration)
    await db.flush()

    # Auto-update plan status to open if it was draft
    if plan.status == "draft":
        plan.status = "open"
        db.add(plan)
        await db.flush()

    return APIResponse(data=await _registration_to_response(db, registration))


@router.post("/registrations/{reg_id}/check-in", response_model=APIResponse)
async def registration_check_in(
    reg_id: uuid.UUID,
    req: RegistrationCheckIn,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Check in for a training session."""
    result = await db.execute(
        select(TrainingRegistration).where(TrainingRegistration.id == reg_id)
    )
    registration = result.scalar_one_or_none()
    if not registration:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Registration not found")

    if registration.check_in_time:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Already checked in")

    registration.check_in_time = datetime.now(timezone.utc)
    registration.attendance_status = "present"
    if req.notes:
        registration.notes = req.notes
    db.add(registration)
    await db.flush()

    return APIResponse(data=await _registration_to_response(db, registration))


@router.post("/registrations/{reg_id}/check-out", response_model=APIResponse)
async def registration_check_out(
    reg_id: uuid.UUID,
    req: RegistrationCheckOut,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Check out from a training session."""
    result = await db.execute(
        select(TrainingRegistration).where(TrainingRegistration.id == reg_id)
    )
    registration = result.scalar_one_or_none()
    if not registration:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Registration not found")

    if not registration.check_in_time:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Must check in first")
    if registration.check_out_time:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Already checked out")

    registration.check_out_time = datetime.now(timezone.utc)
    registration.status = "completed"
    if req.notes:
        registration.notes = req.notes
    db.add(registration)
    await db.flush()

    return APIResponse(data=await _registration_to_response(db, registration))


@router.get("/registrations", response_model=APIResponse)
async def list_registrations(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    plan_id: str | None = None,
    status_filter: str | None = Query(None, alias="status"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List training registrations."""
    org_id = await _get_org_id(db, current_user)

    emp = await _get_employee(db, org_id, current_user)

    query = select(TrainingRegistration).options(
        joinedload(TrainingRegistration.plan).joinedload(TrainingPlan.course),
        joinedload(TrainingRegistration.employee).joinedload(Employee.user),
    ).join(
        TrainingPlan,
        TrainingRegistration.plan_id == TrainingPlan.id,
    ).join(
        TrainingCourse,
        TrainingPlan.course_id == TrainingCourse.id,
    ).where(
        TrainingCourse.organization_id == org_id,
        TrainingRegistration.employee_id == emp.id if emp else True,
    )

    if plan_id:
        query = query.where(TrainingRegistration.plan_id == uuid.UUID(plan_id))
    if status_filter:
        statuses = [s.strip() for s in status_filter.split(",")]
        query = query.where(TrainingRegistration.status.in_(statuses))

    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    query = query.order_by(TrainingRegistration.registered_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    registrations = result.scalars().all()

    results = []
    for r in registrations:
        results.append(await _registration_to_response(db, r))

    return APIResponse(data={
        "data": results,
        "pagination": {"page": page, "page_size": page_size, "total": total},
    })


@router.put("/registrations/{reg_id}", response_model=APIResponse)
async def update_registration(
    reg_id: uuid.UUID,
    req: RegistrationUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update registration (admin: mark attendance, adjust credits, etc.)."""
    result = await db.execute(
        select(TrainingRegistration).where(TrainingRegistration.id == reg_id)
    )
    registration = result.scalar_one_or_none()
    if not registration:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Registration not found")

    if req.status is not None:
        registration.status = req.status
    if req.attendance_status is not None:
        registration.attendance_status = req.attendance_status
    if req.credits_earned is not None:
        registration.credits_earned = req.credits_earned
    if req.notes is not None:
        registration.notes = req.notes

    db.add(registration)
    await db.flush()
    return APIResponse(data=await _registration_to_response(db, registration))


async def _registration_to_response(db: AsyncSession, r: TrainingRegistration) -> RegistrationResponse:
    emp_name = None
    emp_no = None
    if r.employee and r.employee.user:
        emp_name = r.employee.user.display_name
        emp_no = r.employee.employee_no

    plan_title = None
    if r.plan:
        plan_title = r.plan.title

    return RegistrationResponse(
        id=str(r.id),
        plan_id=str(r.plan_id),
        plan_title=plan_title,
        employee_id=str(r.employee_id),
        employee_name=emp_name,
        employee_no=emp_no,
        status=r.status,
        registered_at=r.registered_at.isoformat() if r.registered_at else "",
        check_in_time=r.check_in_time.isoformat() if r.check_in_time else None,
        check_out_time=r.check_out_time.isoformat() if r.check_out_time else None,
        attendance_status=r.attendance_status,
        credits_earned=float(r.credits_earned) if r.credits_earned else None,
        notes=r.notes,
        created_at=r.created_at.isoformat() if r.created_at else "",
        updated_at=r.updated_at.isoformat() if r.updated_at else "",
    )


# ─── Training Evaluations ───────────────────────────────

@router.post("/evaluations", response_model=APIResponse, status_code=status.HTTP_201_CREATED)
async def submit_evaluation(
    req: EvaluationCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Submit a training evaluation."""
    org_id = await _get_org_id(db, current_user)
    emp = await _get_employee(db, org_id, current_user)
    if not emp:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Employee profile not found")

    plan = await _verify_plan_exists(db, uuid.UUID(req.plan_id))

    # Check duplicate evaluation
    dup_result = await db.execute(
        select(TrainingEvaluation).where(
            TrainingEvaluation.plan_id == plan.id,
            TrainingEvaluation.employee_id == emp.id,
        )
    )
    if dup_result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Already submitted evaluation for this training")

    evaluation = TrainingEvaluation(
        plan_id=plan.id,
        employee_id=emp.id,
        overall_rating=req.overall_rating,
        content_rating=req.content_rating,
        instructor_rating=req.instructor_rating,
        practical_rating=req.practical_rating,
        comment=req.comment,
    )
    db.add(evaluation)
    await db.flush()

    return APIResponse(data=await _evaluation_to_response(db, evaluation))


@router.get("/evaluations", response_model=APIResponse)
async def list_evaluations(
    plan_id: str | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List evaluations (for a plan)."""
    query = select(TrainingEvaluation).options(
        joinedload(TrainingEvaluation.plan),
        joinedload(TrainingEvaluation.employee).joinedload(Employee.user),
    )

    if plan_id:
        query = query.where(TrainingEvaluation.plan_id == uuid.UUID(plan_id))

    query = query.order_by(TrainingEvaluation.submitted_at.desc())
    result = await db.execute(query)
    evaluations = result.scalars().all()

    results = []
    for e in evaluations:
        results.append(await _evaluation_to_response(db, e))
    return APIResponse(data=results)


async def _evaluation_to_response(db: AsyncSession, e: TrainingEvaluation) -> EvaluationResponse:
    emp_name = None
    if e.employee and e.employee.user:
        emp_name = e.employee.user.display_name

    plan_title = None
    if e.plan:
        plan_title = e.plan.title

    return EvaluationResponse(
        id=str(e.id),
        plan_id=str(e.plan_id),
        plan_title=plan_title,
        employee_id=str(e.employee_id),
        employee_name=emp_name,
        overall_rating=e.overall_rating,
        content_rating=e.content_rating,
        instructor_rating=e.instructor_rating,
        practical_rating=e.practical_rating,
        comment=e.comment,
        submitted_at=e.submitted_at.isoformat() if e.submitted_at else "",
    )


# ─── Training Certificates ──────────────────────────────

@router.post("/certificates", response_model=APIResponse, status_code=status.HTTP_201_CREATED)
async def issue_certificate(
    req: CertificateIssue,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Issue a training certificate to an employee."""
    await _get_org_id(db, current_user)
    await _verify_course_exists(db, uuid.UUID(req.course_id))

    # Generate unique certificate number
    cert_no = f"CERT-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"

    if req.plan_id:
        await _verify_plan_exists(db, uuid.UUID(req.plan_id))

    certificate = TrainingCertificate(
        employee_id=uuid.UUID(req.employee_id),
        course_id=uuid.UUID(req.course_id),
        plan_id=uuid.UUID(req.plan_id) if req.plan_id else None,
        certificate_no=cert_no,
        issued_date=req.issued_date,
        expiry_date=req.expiry_date,
        file_url=req.file_url,
    )
    db.add(certificate)
    await db.flush()

    return APIResponse(data=await _certificate_to_response(db, certificate))


@router.get("/certificates", response_model=APIResponse)
async def list_certificates(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    employee_id: str | None = None,
    status_filter: str | None = Query(None, alias="status"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List training certificates."""
    org_id = await _get_org_id(db, current_user)

    query = select(TrainingCertificate).options(
        joinedload(TrainingCertificate.employee).joinedload(Employee.user),
        joinedload(TrainingCertificate.course),
        joinedload(TrainingCertificate.plan),
    ).join(
        TrainingCourse,
        TrainingCertificate.course_id == TrainingCourse.id,
    ).where(
        TrainingCourse.organization_id == org_id,
    )

    if employee_id:
        query = query.where(TrainingCertificate.employee_id == uuid.UUID(employee_id))
    if status_filter:
        statuses = [s.strip() for s in status_filter.split(",")]
        query = query.where(TrainingCertificate.status.in_(statuses))

    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    query = query.order_by(TrainingCertificate.issued_date.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    certificates = result.scalars().all()

    results = []
    for c in certificates:
        results.append(await _certificate_to_response(db, c))

    return APIResponse(data={
        "data": results,
        "pagination": {"page": page, "page_size": page_size, "total": total},
    })


@router.put("/certificates/{cert_id}", response_model=APIResponse)
async def update_certificate(
    cert_id: uuid.UUID,
    req: CertificateUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update certificate status or details."""
    result = await db.execute(
        select(TrainingCertificate).where(TrainingCertificate.id == cert_id)
    )
    cert = result.scalar_one_or_none()
    if not cert:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Certificate not found")

    if req.expiry_date is not None:
        cert.expiry_date = req.expiry_date
    if req.status is not None:
        cert.status = req.status
    if req.file_url is not None:
        cert.file_url = req.file_url

    db.add(cert)
    await db.flush()
    return APIResponse(data=await _certificate_to_response(db, cert))


async def _certificate_to_response(db: AsyncSession, c: TrainingCertificate) -> CertificateResponse:
    emp_name = None
    emp_no = None
    if c.employee and c.employee.user:
        emp_name = c.employee.user.display_name
        emp_no = c.employee.employee_no

    return CertificateResponse(
        id=str(c.id),
        employee_id=str(c.employee_id),
        employee_name=emp_name,
        employee_no=emp_no,
        course_id=str(c.course_id),
        course_title=c.course.title if c.course else None,
        plan_id=str(c.plan_id) if c.plan_id else None,
        plan_title=c.plan.title if c.plan else None,
        certificate_no=c.certificate_no,
        issued_date=c.issued_date.isoformat(),
        expiry_date=c.expiry_date.isoformat() if c.expiry_date else None,
        status=c.status,
        file_url=c.file_url,
        created_at=c.created_at.isoformat() if c.created_at else "",
        updated_at=c.updated_at.isoformat() if c.updated_at else "",
    )
