"""FastAPI application entry point."""
from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from sqlalchemy import select, text
from app.config import settings
from app.database import async_engine, AsyncSessionLocal
from app.database import Base
from app.models.permission import Permission
import app.models  # noqa: F401 - ensure models registered

# ─── OpenTelemetry (R2) ──────────────────────────────────
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor

# Import routers
from app.api.v1 import auth, organizations, permissions, hr, tasks, wiki, notifications, audit, uploads
from app.api.v1 import reports, imports, training, benefits, onboarding


# ─── Permission seed data ───────────────────────────────────

SEED_PERMISSIONS = [
    {"code": "user:read", "name": "查看用户信息", "module": "user", "description": "查看用户基本信息"},
    {"code": "user:write", "name": "编辑用户信息", "module": "user", "description": "创建和编辑用户信息"},
    {"code": "org:admin", "name": "组织管理", "module": "org", "description": "组织管理员权限"},
    {"code": "org:read", "name": "查看组织信息", "module": "org", "description": "查看组织基本信息"},
    {"code": "hr:employee:read", "name": "查看员工信息", "module": "hr", "description": "查看员工档案信息"},
    {"code": "hr:employee:write", "name": "编辑员工信息", "module": "hr", "description": "创建和编辑员工档案"},
    {"code": "hr:leave:read", "name": "查看请假信息", "module": "hr", "description": "查看请假申请和记录"},
    {"code": "hr:leave:write", "name": "审批请假", "module": "hr", "description": "审批和操作请假申请"},
    {"code": "hr:attendance:read", "name": "查看考勤记录", "module": "hr", "description": "查看员工考勤记录"},
    {"code": "hr:attendance:write", "name": "编辑考勤记录", "module": "hr", "description": "编辑和修正考勤记录"},
    {"code": "role:read", "name": "查看角色", "module": "role", "description": "查看角色列表和详情"},
    {"code": "role:write", "name": "编辑角色", "module": "role", "description": "创建、编辑和删除角色"},
    {"code": "permission:read", "name": "查看权限", "module": "permission", "description": "查看权限列表"},
]


async def seed_permissions(session):
    """Seed basic permissions if the table is empty."""
    result = await session.execute(select(Permission).limit(1))
    if result.scalar_one_or_none() is not None:
        return  # Already seeded

    for perm_data in SEED_PERMISSIONS:
        perm = Permission(**perm_data)
        session.add(perm)


def setup_opentelemetry(app: FastAPI) -> None:
    """Configure OpenTelemetry instrumentation (CR R2)."""
    otel_endpoint = settings.OTEL_EXPORTER_ENDPOINT

    # M5: Only initialize when an exporter endpoint is configured
    if not otel_endpoint:
        return

    resource = Resource(attributes={
        SERVICE_NAME: settings.APP_NAME,
    })
    provider = TracerProvider(resource=resource)

    otlp_exporter = OTLPSpanExporter(endpoint=otel_endpoint)
    span_processor = BatchSpanProcessor(otlp_exporter)
    provider.add_span_processor(span_processor)

    trace.set_tracer_provider(provider)

    # Instrument FastAPI
    FastAPIInstrumentor.instrument_app(app)

    # Instrument SQLAlchemy
    SQLAlchemyInstrumentor().instrument(engine=async_engine.sync_engine)

    # Instrument Redis
    RedisInstrumentor().instrument()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan: startup and shutdown."""
    # Startup
    async with async_engine.begin() as conn:
        # Create tables (for development; use Alembic in production)
        await conn.run_sync(Base.metadata.create_all)

        # P2: Create tsvector trigger function for WikiPage full-text search
        await conn.execute(text("""
            CREATE OR REPLACE FUNCTION wiki_page_search_vector_update()
            RETURNS trigger AS $$
            BEGIN
                NEW.search_vector := to_tsvector('simple', coalesce(NEW.title, '') || ' ' || coalesce(NEW.content, ''));
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;
        """))

        # P2: Create trigger (IF NOT EXISTS pattern via exception handling)
        try:
            await conn.execute(text("""
                CREATE TRIGGER trg_wiki_page_search_vector
                BEFORE INSERT OR UPDATE OF title, content, content_html ON wiki_pages
                FOR EACH ROW
                EXECUTE FUNCTION wiki_page_search_vector_update();
            """))
        except Exception:
            # Trigger may already exist on subsequent runs
            pass

    # Seed permissions after tables are ready
    async with AsyncSessionLocal() as session:
        await seed_permissions(session)
        await session.commit()

    yield
    # Shutdown
    # M1: Gracefully shutdown OpenTelemetry TracerProvider
    try:
        from opentelemetry import trace as _otel_trace
        _provider = _otel_trace.get_tracer_provider()
        if hasattr(_provider, 'shutdown'):
            _provider.shutdown()
    except Exception:
        pass

    await async_engine.dispose()


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan,
    docs_url="/api/v1/docs",
    openapi_url="/api/v1/openapi.json",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"code": 50000, "message": "Internal server error", "detail": str(exc)},
    )


# Health check
@app.get("/health")
async def health_check():
    return JSONResponse({"status": "ok", "version": settings.APP_VERSION})


# Mount routers
app.include_router(auth.router, prefix="/api/v1")
app.include_router(organizations.router, prefix="/api/v1")
app.include_router(permissions.router, prefix="/api/v1")
app.include_router(hr.router, prefix="/api/v1")
app.include_router(tasks.router, prefix="/api/v1")
app.include_router(wiki.router, prefix="/api/v1")
app.include_router(notifications.router, prefix="/api/v1")
app.include_router(audit.router, prefix="/api/v1")
app.include_router(uploads.router, prefix="/api/v1")
app.include_router(reports.router, prefix="/api/v1")
app.include_router(imports.router, prefix="/api/v1")
app.include_router(training.router, prefix="/api/v1")
app.include_router(benefits.router, prefix="/api/v1")
app.include_router(onboarding.router, prefix="/api/v1")

# Setup OpenTelemetry after everything is registered
setup_opentelemetry(app)
