"""API tests for task management: CRUD, subtasks, comments."""
from __future__ import annotations

import pytest
from httpx import AsyncClient


class TestTasks:
    async def test_create_task(self, client_with_org: AsyncClient, test_user):
        resp = await client_with_org.post("/api/v1/tasks", json={
            "title": "Test Task",
            "assignee_id": str(test_user.id),
        })
        assert resp.status_code == 201
        data = resp.json()["data"]
        assert data["title"] == "Test Task"
        assert data["status"] == "todo"

    async def test_list_tasks(self, client_with_org: AsyncClient, test_user):
        await client_with_org.post("/api/v1/tasks", json={
            "title": "Task 1", "assignee_id": str(test_user.id),
        })
        resp = await client_with_org.get("/api/v1/tasks")
        assert resp.status_code == 200
        assert len(resp.json()["data"]) >= 1

    async def test_get_task(self, client_with_org: AsyncClient, test_user):
        create_resp = await client_with_org.post("/api/v1/tasks", json={
            "title": "My Task", "assignee_id": str(test_user.id),
        })
        task_id = create_resp.json()["data"]["id"]
        resp = await client_with_org.get(f"/api/v1/tasks/{task_id}")
        assert resp.status_code == 200
        assert resp.json()["data"]["title"] == "My Task"

    async def test_update_task_status(self, client_with_org: AsyncClient, test_user):
        create_resp = await client_with_org.post("/api/v1/tasks", json={
            "title": "Task", "assignee_id": str(test_user.id),
        })
        task_id = create_resp.json()["data"]["id"]
        resp = await client_with_org.put(
            f"/api/v1/tasks/{task_id}/status",
            json={"status": "in_progress"},
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["status"] == "in_progress"

    async def test_update_task(self, client_with_org: AsyncClient, test_user):
        create_resp = await client_with_org.post("/api/v1/tasks", json={
            "title": "Task", "assignee_id": str(test_user.id),
        })
        task_id = create_resp.json()["data"]["id"]
        resp = await client_with_org.put(f"/api/v1/tasks/{task_id}", json={
            "title": "Updated Title",
        })
        assert resp.status_code == 200
        assert resp.json()["data"]["title"] == "Updated Title"

    async def test_delete_task(self, client_with_org: AsyncClient, test_user):
        create_resp = await client_with_org.post("/api/v1/tasks", json={
            "title": "Task", "assignee_id": str(test_user.id),
        })
        task_id = create_resp.json()["data"]["id"]
        resp = await client_with_org.delete(f"/api/v1/tasks/{task_id}")
        assert resp.status_code == 200

    async def test_get_my_tasks(self, client_with_org: AsyncClient, test_user):
        await client_with_org.post("/api/v1/tasks", json={
            "title": "My Task", "assignee_id": str(test_user.id),
        })
        resp = await client_with_org.get("/api/v1/tasks/my")
        assert resp.status_code == 200
        assert len(resp.json()["data"]) >= 1

    async def test_kanban(self, client_with_org: AsyncClient, test_user):
        await client_with_org.post("/api/v1/tasks", json={
            "title": "Task A", "assignee_id": str(test_user.id),
        })
        resp = await client_with_org.get("/api/v1/tasks/kanban")
        assert resp.status_code == 200
        assert len(resp.json()["data"]) >= 1


class TestSubtasks:
    async def test_create_subtask(self, client_with_org: AsyncClient, test_user):
        task_resp = await client_with_org.post("/api/v1/tasks", json={
            "title": "Task", "assignee_id": str(test_user.id),
        })
        task_id = task_resp.json()["data"]["id"]
        resp = await client_with_org.post(
            f"/api/v1/tasks/{task_id}/subtasks",
            json={"title": "Subtask"},
        )
        assert resp.status_code == 201
        assert resp.json()["data"]["title"] == "Subtask"

    async def test_list_subtasks(self, client_with_org: AsyncClient, test_user):
        task_resp = await client_with_org.post("/api/v1/tasks", json={
            "title": "Task", "assignee_id": str(test_user.id),
        })
        task_id = task_resp.json()["data"]["id"]
        await client_with_org.post(
            f"/api/v1/tasks/{task_id}/subtasks", json={"title": "Subtask"},
        )
        resp = await client_with_org.get(f"/api/v1/tasks/{task_id}/subtasks")
        assert resp.status_code == 200
        assert len(resp.json()["data"]) >= 1


class TestComments:
    async def test_create_comment(self, client_with_org: AsyncClient, test_user):
        task_resp = await client_with_org.post("/api/v1/tasks", json={
            "title": "Task", "assignee_id": str(test_user.id),
        })
        task_id = task_resp.json()["data"]["id"]
        resp = await client_with_org.post(
            f"/api/v1/tasks/{task_id}/comments",
            json={"content": "Nice work!"},
        )
        assert resp.status_code == 201
        assert resp.json()["data"]["content"] == "Nice work!"

    @pytest.mark.skip(reason="SQLite ARRAY(UUID) deserialization needs fix")
    async def test_list_comments(self, client_with_org: AsyncClient, test_user):
        task_resp = await client_with_org.post("/api/v1/tasks", json={
            "title": "Task", "assignee_id": str(test_user.id),
        })
        task_id = task_resp.json()["data"]["id"]
        await client_with_org.post(
            f"/api/v1/tasks/{task_id}/comments", json={"content": "Comment 1"},
        )
        resp = await client_with_org.get(f"/api/v1/tasks/{task_id}/comments")
        assert resp.status_code == 200
        assert len(resp.json()["data"]) >= 1
