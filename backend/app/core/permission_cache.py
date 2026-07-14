"""Permission cache optimization (CR P1).

Implements an in-memory cache for permission checks to reduce
database round-trips on frequently-accessed permission data.

Cache strategy:
- Each org's role→permission mappings cached in memory
- TTL: 5 minutes (configurable)
- Invalidated when role permissions are updated
- Separate per-organization partitions to avoid cross-org leaks
"""
from __future__ import annotations

import threading
import time
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


class PermissionCache:
    """Thread-safe in-memory permission cache with TTL."""

    def __init__(self, ttl_seconds: int = 300):
        self._cache: dict[str, dict[str, Any]] = {}
        self._ttl: dict[str, float] = {}
        self._lock = threading.RLock()
        self._ttl_seconds = ttl_seconds

    def _cache_key(self, org_id: str, user_id: str) -> str:
        return f"{org_id}:{user_id}"

    def get(self, org_id: str, user_id: str) -> dict[str, Any] | None:
        """Get cached permissions for a user in an org."""
        key = self._cache_key(org_id, user_id)
        with self._lock:
            if key not in self._cache:
                return None
            if time.time() > self._ttl.get(key, 0):
                del self._cache[key]
                del self._ttl[key]
                return None
            return self._cache[key]

    def set(self, org_id: str, user_id: str, permissions: dict[str, Any]) -> None:
        """Cache permissions for a user in an org."""
        key = self._cache_key(org_id, user_id)
        with self._lock:
            self._cache[key] = permissions
            self._ttl[key] = time.time() + self._ttl_seconds

    def invalidate_user(self, org_id: str, user_id: str) -> None:
        """Invalidate cache for a specific user."""
        key = self._cache_key(org_id, user_id)
        with self._lock:
            self._cache.pop(key, None)
            self._ttl.pop(key, None)

    def invalidate_org(self, org_id: str) -> None:
        """Invalidate all permission caches for an organization."""
        prefix = f"{org_id}:"
        with self._lock:
            keys_to_del = [k for k in self._cache if k.startswith(prefix)]
            for key in keys_to_del:
                del self._cache[key]
                del self._ttl[key]

    def invalidate_all(self) -> None:
        """Clear entire permission cache."""
        with self._lock:
            self._cache.clear()
            self._ttl.clear()

    async def get_user_permissions(
        self,
        db: AsyncSession,
        org_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> dict[str, Any]:
        """Get user permissions (cached). Falls back to DB if not cached."""
        org_str = str(org_id)
        user_str = str(user_id)

        cached = self.get(org_str, user_str)
        if cached:
            return cached

        # Load from DB
        from app.models.organization import DepartmentMember
        from app.models.permission import Role, RolePermission, Permission as PermModel

        permissions = {
            "role_names": [],
            "permission_codes": [],
            "position_level": 0,
        }

        # Get department memberships with roles
        result = await db.execute(
            select(DepartmentMember)
            .where(DepartmentMember.user_id == user_id)
        )
        memberships = result.scalars().all()

        role_ids = set()
        for m in memberships:
            if m.role_id:
                role_ids.add(m.role_id)

        # Load roles and permissions
        if role_ids:
            roles_result = await db.execute(
                select(Role).where(Role.id.in_(role_ids))
            )
            roles = roles_result.scalars().all()
            permissions["role_names"] = [r.name for r in roles]

            # Get permissions for all roles
            perm_result = await db.execute(
                select(RolePermission).where(RolePermission.role_id.in_(role_ids))
            )
            role_perms = perm_result.scalars().all()
            perm_ids = [rp.permission_id for rp in role_perms]

            if perm_ids:
                codes_result = await db.execute(
                    select(PermModel.code).where(PermModel.id.in_(perm_ids))
                )
                permissions["permission_codes"] = [r[0] for r in codes_result]

        self.set(org_str, user_str, permissions)
        return permissions


# Singleton instance
permission_cache = PermissionCache()
