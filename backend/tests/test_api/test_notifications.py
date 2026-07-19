"""API tests for notifications: list, mark read, unread count."""
from __future__ import annotations

from httpx import AsyncClient


class TestNotifications:
    async def test_list_notifications(self, client_with_org: AsyncClient):
        resp = await client_with_org.get("/api/v1/notifications")
        assert resp.status_code == 200
        # No notifications yet — empty list is fine
        assert "data" in resp.json()

    async def test_unread_count(self, client_with_org: AsyncClient):
        resp = await client_with_org.get("/api/v1/notifications/unread-count")
        assert resp.status_code == 200
        assert "count" in resp.json()["data"]

    async def test_get_preferences(self, client_with_org: AsyncClient):
        resp = await client_with_org.get("/api/v1/notifications/preferences")
        assert resp.status_code == 200
        assert isinstance(resp.json()["data"], list)

    async def test_upsert_preferences(self, client_with_org: AsyncClient):
        resp = await client_with_org.put("/api/v1/notifications/preferences", json=[
            {
                "notification_type": "leave_request",
                "channel_in_app": True,
                "channel_email": True,
                "digest": "daily",
            },
        ])
        assert resp.status_code == 200
        assert len(resp.json()["data"]) >= 1
