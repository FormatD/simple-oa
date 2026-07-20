"""Test fixtures and configuration for Simple OA backend tests."""

from __future__ import annotations

# Patch Uuid.bind_processor to handle strings from SQLite
import uuid as _patched_uuid
from sqlalchemy.types import Uuid as _patched_uid_type
_orig_bind = _patched_uid_type.bind_processor
def _patched_bind(self, dialect):
    proc = _orig_bind(self, dialect)
    if proc is None:
        return None
    def safe(value):
        if value is not None and isinstance(value, str):
            return value
        return proc(value)
    return safe
_patched_uid_type.bind_processor = _patched_bind


import asyncio
import json
import uuid
from datetime import datetime, timezone
from typing import AsyncGenerator

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import DateTime, event
from sqlalchemy.dialects.postgresql import ARRAY as PG_ARRAY
from sqlalchemy.dialects.postgresql import INET, JSONB as PG_JSONB, TSVECTOR
from sqlalchemy.dialects.sqlite.base import SQLiteDialect
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import Session as SASession

from app.core.security import create_access_token, hash_password
from app.database import Base, get_db
from app.main import app
from app.models.auth import User
from app.models.organization import Organization, OrganizationMember

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

# ── PostgreSQL type compatibility for SQLite ─────────────────────────

@compiles(PG_JSONB, "sqlite")
def _compile_jsonb_as_json(element, compiler, **kw):
    return compiler.visit_JSON(element, **kw)

@compiles(PG_ARRAY, "sqlite")
def _compile_array_as_text(element, compiler, **kw):
    return "TEXT"

@compiles(TSVECTOR, "sqlite")
def _compile_tsvector_as_text(element, compiler, **kw):
    return "TEXT"

@compiles(INET, "sqlite")
def _compile_inet_as_text(element, compiler, **kw):
    return "VARCHAR(45)"

from sqlalchemy.engine import Engine as SAEngine

# Register PG_ARRAY with SQLite colspecs for result processing (JSON deserialization)
from sqlalchemy.dialects.sqlite.base import SQLiteDialect as _SQLiteDialect
if PG_ARRAY not in _SQLiteDialect.colspecs:
    _SqliteARRAY = type("SqliteARRAY", (PG_ARRAY,), {
        "result_processor": lambda self, dialect, coltype: (
            None if dialect.name != "sqlite" else (
                lambda v: json.loads(v) if v is not None else None
            )
        ),
    })
    _SQLiteDialect.colspecs[PG_ARRAY] = _SqliteARRAY

# Intercept all SQL execute calls to serialize Python lists to JSON for SQLite
@event.listens_for(SAEngine, "before_cursor_execute", retval=True)
def _serialize_lists(conn, cursor, statement, parameters, context, executemany):
    if parameters is None:
        return statement, parameters
    if isinstance(parameters, dict):
        for key in list(parameters):
            if isinstance(parameters[key], list):
                parameters[key] = json.dumps(parameters[key], default=str)
            
        return statement, parameters
    new_params = []
    for v in parameters:
        if isinstance(v, (list, tuple)):
            new_params.append(json.dumps(v, default=str))
        else:
            new_params.append(v)
    return statement, tuple(new_params)

# Fix: ensure datetimes loaded from SQLite are timezone-aware
@event.listens_for(SASession, "loaded_as_persistent")
def _fix_datetime_tz(session, instance):
    for key in list(instance.__dict__):
        val = instance.__dict__[key]
        if isinstance(val, datetime) and val.tzinfo is None:
            instance.__dict__[key] = val.replace(tzinfo=timezone.utc)

# ── Fixtures ─────────────────────────────────────────────────────────

@pytest_asyncio.fixture(scope="function")
async def async_engine():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()
    await asyncio.sleep(0.05)

@pytest_asyncio.fixture(scope="function")
async def db_session(async_engine) -> AsyncGenerator[AsyncSession, None]:
    conn = await async_engine.connect()
    trans = await conn.begin()
    session = AsyncSession(bind=conn, expire_on_commit=False)
    yield session
    await session.close()
    await trans.rollback()
    await conn.close()
    await asyncio.sleep(0.02)

@pytest_asyncio.fixture(scope="function")
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    async def _get_test_db():
        yield db_session
    app.dependency_overrides[get_db] = _get_test_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()

@pytest_asyncio.fixture(scope="function")
async def test_user(db_session: AsyncSession) -> User:
    user = User(
        id=uuid.uuid4(), email="test@example.com", display_name="Test User",
        password_hash=hash_password("TestPass123!"),
        password_changed_at=datetime.now(timezone.utc),
        is_active=True, is_superuser=True,
    )
    db_session.add(user)
    await db_session.flush()
    return user

@pytest_asyncio.fixture(scope="function")
async def test_org(db_session: AsyncSession, test_user: User) -> Organization:
    org = Organization(
        id=uuid.uuid4(), name="Test Org", slug="test-org", owner_id=test_user.id,
    )
    db_session.add(org)
    await db_session.flush()
    member = OrganizationMember(organization_id=org.id, user_id=test_user.id)
    db_session.add(member)
    await db_session.flush()
    return org

@pytest_asyncio.fixture(scope="function")
async def test_user_token(test_user: User) -> str:
    return create_access_token(test_user.id)

@pytest_asyncio.fixture(scope="function")
async def auth_headers(test_user_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {test_user_token}"}

@pytest_asyncio.fixture(scope="function")
async def auth_client(client: AsyncClient, auth_headers: dict[str, str]) -> AsyncClient:
    client.headers.update(auth_headers)
    return client

@pytest_asyncio.fixture(scope="function")
async def client_with_org(auth_client: AsyncClient, test_org: Organization) -> AsyncClient:
    return auth_client
