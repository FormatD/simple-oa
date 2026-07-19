"""API tests for HR module: employees, attendance, leave."""
from __future__ import annotations

import uuid
from datetime import date, datetime, timezone

import pytest
from httpx import AsyncClient


class TestPositions:
    async def test_create_position(self, client_with_org: AsyncClient):
        resp = await client_with_org.post("/api/v1/hr/positions", json={
            "name": "Engineer",
        })
        assert resp.status_code == 201
        assert resp.json()["data"]["name"] == "Engineer"

    async def test_list_positions(self, client_with_org: AsyncClient):
        await client_with_org.post("/api/v1/hr/positions", json={"name": "Engineer"})
        resp = await client_with_org.get("/api/v1/hr/positions")
        assert resp.status_code == 200
        assert len(resp.json()["data"]) >= 1


class TestEmployees:
    async def test_create_employee(self, client_with_org: AsyncClient, test_user):
        resp = await client_with_org.post("/api/v1/hr/employees", json={
            "user_id": str(test_user.id),
            "employee_no": "EMP001",
            "hire_date": "2024-01-15",
            "employment_type": "full_time",
        })
        assert resp.status_code == 201
        data = resp.json()["data"]
        assert data["employee_no"] == "EMP001"
        assert data["display_name"] == "Test User"

    async def test_list_employees(self, client_with_org: AsyncClient, test_user):
        await client_with_org.post("/api/v1/hr/employees", json={
            "user_id": str(test_user.id),
            "employee_no": "EMP001",
            "hire_date": "2024-01-15",
        })
        resp = await client_with_org.get("/api/v1/hr/employees")
        assert resp.status_code == 200
        assert len(resp.json()["data"]["data"]) >= 1

    async def test_get_employee(self, client_with_org: AsyncClient, test_user):
        create_resp = await client_with_org.post("/api/v1/hr/employees", json={
            "user_id": str(test_user.id),
            "employee_no": "EMP001",
            "hire_date": "2024-01-15",
        })
        emp_id = create_resp.json()["data"]["id"]
        resp = await client_with_org.get(f"/api/v1/hr/employees/{emp_id}")
        assert resp.status_code == 200
        assert resp.json()["data"]["employee_no"] == "EMP001"

    async def test_update_employee(self, client_with_org: AsyncClient, test_user):
        create_resp = await client_with_org.post("/api/v1/hr/employees", json={
            "user_id": str(test_user.id),
            "employee_no": "EMP001",
            "hire_date": "2024-01-15",
        })
        emp_id = create_resp.json()["data"]["id"]
        resp = await client_with_org.put(f"/api/v1/hr/employees/{emp_id}", json={
            "work_location": "Office A",
        })
        assert resp.status_code == 200
        assert resp.json()["data"]["work_location"] == "Office A"


class TestAttendance:
    async def test_check_in(self, client_with_org: AsyncClient, test_user):
        await client_with_org.post("/api/v1/hr/employees", json={
            "user_id": str(test_user.id),
            "employee_no": "EMP001",
            "hire_date": "2024-01-15",
        })
        resp = await client_with_org.post("/api/v1/hr/attendance/check-in", json={
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        assert resp.status_code == 201

    async def test_check_in_twice_fails(self, client_with_org: AsyncClient, test_user):
        await client_with_org.post("/api/v1/hr/employees", json={
            "user_id": str(test_user.id),
            "employee_no": "EMP001",
            "hire_date": "2024-01-15",
        })
        await client_with_org.post("/api/v1/hr/attendance/check-in", json={
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        resp = await client_with_org.post("/api/v1/hr/attendance/check-in", json={
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        assert resp.status_code == 409


class TestLeaveTypesAndRequests:
    async def test_create_leave_type(self, client_with_org: AsyncClient):
        resp = await client_with_org.post("/api/v1/hr/leave-types", json={
            "name": "Annual", "paid": True, "requires_approval": True,
        })
        assert resp.status_code == 201
        assert resp.json()["data"]["name"] == "Annual"

    async def test_list_leave_types(self, client_with_org: AsyncClient):
        await client_with_org.post("/api/v1/hr/leave-types", json={
            "name": "Annual", "paid": True,
        })
        resp = await client_with_org.get("/api/v1/hr/leave-types")
        assert resp.status_code == 200
        assert len(resp.json()["data"]) >= 1

    async def test_create_leave_request(self, client_with_org: AsyncClient, test_user):
        # Create employee
        await client_with_org.post("/api/v1/hr/employees", json={
            "user_id": str(test_user.id),
            "employee_no": "EMP001",
            "hire_date": "2024-01-15",
        })
        # Create leave type
        lt_resp = await client_with_org.post("/api/v1/hr/leave-types", json={
            "name": "Annual", "paid": True,
        })
        lt_id = lt_resp.json()["data"]["id"]
        # Create leave request
        resp = await client_with_org.post("/api/v1/hr/leave-requests", json={
            "leave_type_id": lt_id,
            "start_date": "2024-06-01",
            "end_date": "2024-06-03",
            "reason": "Vacation",
        })
        assert resp.status_code == 201
        assert resp.json()["data"]["status"] == "pending"

    async def test_list_leave_requests(self, client_with_org: AsyncClient, test_user):
        await client_with_org.post("/api/v1/hr/employees", json={
            "user_id": str(test_user.id),
            "employee_no": "EMP001",
            "hire_date": "2024-01-15",
        })
        lt_resp = await client_with_org.post("/api/v1/hr/leave-types", json={
            "name": "Annual", "paid": True,
        })
        await client_with_org.post("/api/v1/hr/leave-requests", json={
            "leave_type_id": lt_resp.json()["data"]["id"],
            "start_date": "2024-06-01",
            "end_date": "2024-06-03",
        })
        resp = await client_with_org.get("/api/v1/hr/leave-requests")
        assert resp.status_code == 200
        assert len(resp.json()["data"]["data"]) >= 1


class TestEmployeeStatus:
    async def test_update_status(self, client_with_org: AsyncClient, test_user):
        create_resp = await client_with_org.post("/api/v1/hr/employees", json={
            "user_id": str(test_user.id),
            "employee_no": "EMP001",
            "hire_date": "2024-01-15",
        })
        emp_id = create_resp.json()["data"]["id"]
        resp = await client_with_org.put(
            f"/api/v1/hr/employees/{emp_id}/status",
            json={"status": "resigned"},
        )
        assert resp.status_code == 200


class TestContracts:
    async def test_create_and_list_contracts(self, client_with_org: AsyncClient, test_user):
        emp_resp = await client_with_org.post("/api/v1/hr/employees", json={
            "user_id": str(test_user.id),
            "employee_no": "EMP001",
            "hire_date": "2024-01-15",
        })
        emp_id = emp_resp.json()["data"]["id"]
        resp = await client_with_org.post(
            f"/api/v1/hr/employees/{emp_id}/contracts",
            json={
                "contract_type": "permanent",
                "start_date": "2024-01-15",
            },
        )
        assert resp.status_code == 201

        list_resp = await client_with_org.get(
            f"/api/v1/hr/employees/{emp_id}/contracts"
        )
        assert list_resp.status_code == 200
        assert len(list_resp.json()["data"]) >= 1
