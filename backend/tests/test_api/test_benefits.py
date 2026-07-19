"""API tests for benefits (P2 module)."""
from __future__ import annotations

from httpx import AsyncClient


class TestBenefits:
    async def test_list_benefit_items(self, client_with_org: AsyncClient):
        resp = await client_with_org.get("/api/v1/benefits/items")
        assert resp.status_code == 200
        assert isinstance(resp.json()["data"], list)

    async def test_create_and_list_benefit_items(self, client_with_org: AsyncClient):
        create_resp = await client_with_org.post("/api/v1/benefits/items", json={
            "name": "Health Insurance",
            "category": "health",
        })
        assert create_resp.status_code == 201
        assert create_resp.json()["data"]["name"] == "Health Insurance"

        resp = await client_with_org.get("/api/v1/benefits/items")
        assert resp.status_code == 200
        assert len(resp.json()["data"]) >= 1

    async def test_benefits_unauthorized(self, client: AsyncClient):
        resp = await client.get("/api/v1/benefits/items")
        assert resp.status_code == 401
