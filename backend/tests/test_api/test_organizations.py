"""API tests for organization management: CRUD, departments, members."""
from __future__ import annotations

from httpx import AsyncClient


class TestCreateOrganization:
    async def test_create_org_success(self, auth_client: AsyncClient, test_user):
        resp = await auth_client.post("/api/v1/organizations", json={
            "name": "My Org", "slug": "my-org",
        })
        assert resp.status_code == 201
        data = resp.json()["data"]
        assert data["name"] == "My Org"
        assert data["slug"] == "my-org"

    async def test_create_org_duplicate_slug(self, auth_client: AsyncClient, test_org):
        resp = await auth_client.post("/api/v1/organizations", json={
            "name": "Dup", "slug": "test-org",
        })
        assert resp.status_code == 409

    async def test_create_org_unauthorized(self, client: AsyncClient):
        resp = await client.post("/api/v1/organizations", json={
            "name": "Org", "slug": "org",
        })
        assert resp.status_code == 401


class TestListOrganizations:
    async def test_list_orgs(self, auth_client: AsyncClient, test_org):
        resp = await auth_client.get("/api/v1/organizations")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert len(data) >= 1
        assert data[0]["slug"] == "test-org"


class TestGetOrganization:
    async def test_get_org(self, auth_client: AsyncClient, test_org):
        resp = await auth_client.get(f"/api/v1/organizations/{test_org.id}")
        assert resp.status_code == 200
        assert resp.json()["data"]["slug"] == "test-org"

    async def test_get_org_not_found(self, auth_client: AsyncClient):
        import uuid
        resp = await auth_client.get(f"/api/v1/organizations/{uuid.uuid4()}")
        assert resp.status_code == 404


class TestUpdateOrganization:
    async def test_update_org_name(self, auth_client: AsyncClient, test_org):
        resp = await auth_client.put(f"/api/v1/organizations/{test_org.id}", json={
            "name": "Updated Org",
        })
        assert resp.status_code == 200
        assert resp.json()["data"]["name"] == "Updated Org"


class TestDepartments:
    async def test_create_dept(self, auth_client: AsyncClient, test_org):
        resp = await auth_client.post(
            f"/api/v1/organizations/{test_org.id}/departments",
            json={"name": "Engineering"},
        )
        assert resp.status_code == 201
        assert resp.json()["data"]["name"] == "Engineering"

    async def test_list_depts(self, auth_client: AsyncClient, test_org):
        await auth_client.post(
            f"/api/v1/organizations/{test_org.id}/departments",
            json={"name": "Engineering"},
        )
        resp = await auth_client.get(
            f"/api/v1/organizations/{test_org.id}/departments"
        )
        assert resp.status_code == 200
        assert len(resp.json()["data"]) >= 1

    async def test_create_dept_with_parent(self, auth_client: AsyncClient, test_org):
        p_resp = await auth_client.post(
            f"/api/v1/organizations/{test_org.id}/departments",
            json={"name": "Parent"},
        )
        parent_id = p_resp.json()["data"]["id"]
        resp = await auth_client.post(
            f"/api/v1/organizations/{test_org.id}/departments",
            json={"name": "Child", "parent_id": parent_id},
        )
        assert resp.status_code == 201
        assert resp.json()["data"]["name"] == "Child"


class TestOrgMembers:
    async def test_add_member(self, auth_client: AsyncClient, test_org, test_user):
        resp = await auth_client.post(
            f"/api/v1/organizations/{test_org.id}/members",
            json={"user_id": str(test_user.id)},
        )
        assert resp.status_code == 201

    async def test_list_members(self, auth_client: AsyncClient, test_org):
        resp = await auth_client.get(
            f"/api/v1/organizations/{test_org.id}/members"
        )
        assert resp.status_code == 200
        assert len(resp.json()["data"]) >= 1

    async def test_remove_member(self, auth_client: AsyncClient, test_org, test_user):
        await auth_client.post(
            f"/api/v1/organizations/{test_org.id}/members",
            json={"user_id": str(test_user.id)},
        )
        resp = await auth_client.delete(
            f"/api/v1/organizations/{test_org.id}/members/{test_user.id}"
        )
        assert resp.status_code == 200
