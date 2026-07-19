"""API tests for training (P2 module)."""
from __future__ import annotations

from httpx import AsyncClient


class TestTraining:
    async def test_list_courses(self, client_with_org: AsyncClient):
        resp = await client_with_org.get("/api/v1/training/courses")
        assert resp.status_code == 200
        assert isinstance(resp.json()["data"]["data"], list)

    async def test_create_and_list_courses(self, client_with_org: AsyncClient):
        create_resp = await client_with_org.post("/api/v1/training/courses", json={
            "title": "Security Training",
            "instructor": "John",
        })
        assert create_resp.status_code == 201
        assert create_resp.json()["data"]["title"] == "Security Training"

        resp = await client_with_org.get("/api/v1/training/courses")
        assert resp.status_code == 200
        assert len(resp.json()["data"]["data"]) >= 1

    async def test_training_unauthorized(self, client: AsyncClient):
        resp = await client.get("/api/v1/training/courses")
        assert resp.status_code == 401
