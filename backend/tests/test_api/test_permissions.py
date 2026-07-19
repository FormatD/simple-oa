"""API tests for permissions and roles."""
from __future__ import annotations

from sqlalchemy import select
from httpx import AsyncClient


class TestPermissions:
    async def test_list_permissions(self, client_with_org: AsyncClient, db_session):
        from app.models.permission import Permission
        from app.main import SEED_PERMISSIONS
        # Seed permissions for test
        result = await db_session.execute(select(Permission).limit(1))
        if result.scalar_one_or_none() is None:
            for perm_data in SEED_PERMISSIONS:
                db_session.add(Permission(**perm_data))
            await db_session.flush()
        
        resp = await client_with_org.get("/api/v1/permissions")
        assert resp.status_code == 200
        assert len(resp.json()["data"]) >= 1


class TestRoles:
    async def test_create_role(self, client_with_org: AsyncClient, test_org):
        resp = await client_with_org.post(
            f"/api/v1/organizations/{test_org.id}/roles",
            json={"name": "admin", "display_name": "Admin"},
        )
        assert resp.status_code == 201
        assert resp.json()["data"]["name"] == "admin"

    async def test_list_roles(self, client_with_org: AsyncClient, test_org):
        await client_with_org.post(
            f"/api/v1/organizations/{test_org.id}/roles",
            json={"name": "admin", "display_name": "Admin"},
        )
        resp = await client_with_org.get(
            f"/api/v1/organizations/{test_org.id}/roles"
        )
        assert resp.status_code == 200
        assert len(resp.json()["data"]) >= 1

    async def test_get_role(self, client_with_org: AsyncClient, test_org):
        create_resp = await client_with_org.post(
            f"/api/v1/organizations/{test_org.id}/roles",
            json={"name": "admin", "display_name": "Admin"},
        )
        role_id = create_resp.json()["data"]["id"]
        resp = await client_with_org.get(
            f"/api/v1/organizations/{test_org.id}/roles/{role_id}"
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["name"] == "admin"

    async def test_update_role(self, client_with_org: AsyncClient, test_org):
        create_resp = await client_with_org.post(
            f"/api/v1/organizations/{test_org.id}/roles",
            json={"name": "editor", "display_name": "Editor"},
        )
        role_id = create_resp.json()["data"]["id"]
        resp = await client_with_org.put(
            f"/api/v1/organizations/{test_org.id}/roles/{role_id}",
            json={"display_name": "Senior Editor"},
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["display_name"] == "Senior Editor"

    async def test_delete_role(self, client_with_org: AsyncClient, test_org):
        create_resp = await client_with_org.post(
            f"/api/v1/organizations/{test_org.id}/roles",
            json={"name": "temp", "display_name": "Temp"},
        )
        role_id = create_resp.json()["data"]["id"]
        resp = await client_with_org.delete(
            f"/api/v1/organizations/{test_org.id}/roles/{role_id}"
        )
        assert resp.status_code == 200

    async def test_set_role_permissions(self, client_with_org: AsyncClient, test_org):
        create_resp = await client_with_org.post(
            f"/api/v1/organizations/{test_org.id}/roles",
            json={"name": "admin", "display_name": "Admin"},
        )
        role_id = create_resp.json()["data"]["id"]
        perms_resp = await client_with_org.get("/api/v1/permissions")
        perm_ids = [p["id"] for p in perms_resp.json()["data"]]

        resp = await client_with_org.put(
            f"/api/v1/organizations/{test_org.id}/roles/{role_id}/permissions",
            json={"permission_ids": perm_ids},
        )
        assert resp.status_code == 200
