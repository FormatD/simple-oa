"""API tests for reports: dashboard stats, headcount."""
from __future__ import annotations

from httpx import AsyncClient


class TestReports:
    async def test_dashboard_stats(self, client_with_org: AsyncClient):
        resp = await client_with_org.get("/api/v1/reports/dashboard")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert "total_employees" in data
        assert "active_employees" in data
        assert "department_count" in data

    async def test_headcount_report(self, client_with_org: AsyncClient, test_org):
        resp = await client_with_org.get("/api/v1/reports/hr/headcount")
        assert resp.status_code == 200
        assert isinstance(resp.json()["data"], list)

    async def test_attendance_summary(self, client_with_org: AsyncClient):
        resp = await client_with_org.get("/api/v1/reports/hr/attendance-summary")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert "period" in data
        assert "total_employees" in data

    async def test_leave_summary(self, client_with_org: AsyncClient):
        resp = await client_with_org.get("/api/v1/reports/hr/leave-summary")
        assert resp.status_code == 200
        assert isinstance(resp.json()["data"], list)
