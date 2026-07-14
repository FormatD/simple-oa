"""FastAPI application entry point."""
from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.database import async_engine, get_db
from app.database import Base
import app.models  # noqa: F401 - ensure models registered

# Import routers
from app.api.v1 import auth, organizations, permissions, hr, tasks, wiki, notifications, audit, uploads


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan: startup and shutdown."""
    # Startup
    async with async_engine.begin() as conn:
        # Create tables (for development; use Alembic in production)
        await conn.run_sync(Base.metadata.create_all)
    yield
    # Shutdown
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
