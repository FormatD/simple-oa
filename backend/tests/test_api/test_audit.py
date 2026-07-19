"""API tests for audit logs."""
from __future__ import annotations

from httpx import AsyncClient


class TestAuditLogs:
    async def test_list_audit_logs(self, client_with_org: AsyncClient):
        resp = await client_with_org.get("/api/v1/audit-logs")
        assert resp.status_code == 200
        assert "data" in resp.json()
        assert "pagination" in resp.json()

    async def test_list_audit_logs_with_pagination(self, client_with_org: AsyncClient):
        resp = await client_with_org.get("/api/v1/audit-logs?page=1&page_size=10")
        assert resp.status_code == 200
        data = resp.json()
        assert data["pagination"]["page"] == 1
        assert data["pagination"]["page_size"] == 10
