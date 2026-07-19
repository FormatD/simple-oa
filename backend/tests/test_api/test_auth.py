"""API tests for authentication: register, login, refresh, TOTP."""
from __future__ import annotations

import pytest
from httpx import AsyncClient

from app.core.security import hash_password
from app.models.auth import User


class TestRegister:
    async def test_register_success(self, client: AsyncClient):
        resp = await client.post("/api/v1/auth/register", json={
            "email": "new@example.com",
            "password": "NewUserP@ss1",
            "display_name": "New User",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["code"] == 0
        assert "access_token" in data["data"]
        assert "refresh_token" in data["data"]

    async def test_register_duplicate_email(self, client: AsyncClient, test_user: User):
        resp = await client.post("/api/v1/auth/register", json={
            "email": "test@example.com",
            "password": "NewUserP@ss1",
            "display_name": "Duplicate",
        })
        assert resp.status_code == 409
        assert "already registered" in resp.json()["detail"]

    async def test_register_weak_password(self, client: AsyncClient):
        resp = await client.post("/api/v1/auth/register", json={
            "email": "weak@example.com",
            "password": "short",
            "display_name": "Weak",
        })
        assert resp.status_code == 422

    async def test_register_no_display_name(self, client: AsyncClient):
        resp = await client.post("/api/v1/auth/register", json={
            "email": "noname@example.com",
            "password": "ValidP@ss1",
        })
        assert resp.status_code == 422


class TestLogin:
    async def test_login_success(self, client: AsyncClient, test_user: User):
        resp = await client.post("/api/v1/auth/login", json={
            "email": "test@example.com",
            "password": "TestPass123!",
        })
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert "access_token" in data
        assert "refresh_token" in data

    async def test_login_wrong_password(self, client: AsyncClient, test_user: User):
        resp = await client.post("/api/v1/auth/login", json={
            "email": "test@example.com",
            "password": "WrongP@ss1",
        })
        assert resp.status_code == 401

    async def test_login_nonexistent_email(self, client: AsyncClient):
        resp = await client.post("/api/v1/auth/login", json={
            "email": "nobody@example.com",
            "password": "TestPass123!",
        })
        assert resp.status_code == 401


class TestTokenRefresh:
    async def test_refresh_success(self, client: AsyncClient, test_user: User):
        login_resp = await client.post("/api/v1/auth/login", json={
            "email": "test@example.com",
            "password": "TestPass123!",
        })
        refresh_token = login_resp.json()["data"]["refresh_token"]

        resp = await client.post("/api/v1/auth/refresh", json={
            "refresh_token": refresh_token,
        })
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert "access_token" in data
        assert data["refresh_token"] != refresh_token  # token rotation (R5)

    async def test_refresh_invalid_token(self, client: AsyncClient):
        resp = await client.post("/api/v1/auth/refresh", json={
            "refresh_token": "invalid-token-here",
        })
        assert resp.status_code == 401

    async def test_refresh_revoked_token(self, client: AsyncClient, test_user: User):
        login_resp = await client.post("/api/v1/auth/login", json={
            "email": "test@example.com",
            "password": "TestPass123!",
        })
        refresh_token = login_resp.json()["data"]["refresh_token"]

        # Use it once (rotation revokes it)
        resp1 = await client.post("/api/v1/auth/refresh", json={
            "refresh_token": refresh_token,
        })
        assert resp1.status_code == 200

        # Use it again (should fail — revoked)
        resp2 = await client.post("/api/v1/auth/refresh", json={
            "refresh_token": refresh_token,
        })
        assert resp2.status_code == 401


class TestLogout:
    async def test_logout_revokes_token(self, client: AsyncClient, test_user: User):
        login_resp = await client.post("/api/v1/auth/login", json={
            "email": "test@example.com",
            "password": "TestPass123!",
        })
        refresh_token = login_resp.json()["data"]["refresh_token"]

        resp = await client.post("/api/v1/auth/logout", json={
            "refresh_token": refresh_token,
        })
        assert resp.status_code == 200

        # Now refresh should fail
        resp2 = await client.post("/api/v1/auth/refresh", json={
            "refresh_token": refresh_token,
        })
        assert resp2.status_code == 401


class TestGetMe:
    async def test_get_me_success(self, auth_client: AsyncClient):
        resp = await auth_client.get("/api/v1/auth/me")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["email"] == "test@example.com"
        assert data["display_name"] == "Test User"
        assert data["is_active"] is True

    async def test_get_me_unauthorized(self, client: AsyncClient):
        resp = await client.get("/api/v1/auth/me")
        assert resp.status_code == 401


class TestChangePassword:
    async def test_change_password_success(self, auth_client: AsyncClient, db_session, test_user):
        resp = await auth_client.put("/api/v1/auth/password", json={
            "old_password": "TestPass123!",
            "new_password": "NewP@ssword1",
        })
        assert resp.status_code == 200

    async def test_change_password_wrong_old(self, auth_client: AsyncClient):
        resp = await auth_client.put("/api/v1/auth/password", json={
            "old_password": "WrongP@ss1",
            "new_password": "NewP@ssword1",
        })
        assert resp.status_code == 400

    async def test_change_password_weak_new(self, auth_client: AsyncClient):
        resp = await auth_client.put("/api/v1/auth/password", json={
            "old_password": "TestPass123!",
            "new_password": "weak",
        })
        assert resp.status_code == 422


class TestTOTP:
    async def test_totp_setup(self, auth_client: AsyncClient):
        resp = await auth_client.post("/api/v1/auth/totp/setup")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert "secret" in data
        assert "uri" in data
        assert "qr_code" in data

    async def test_totp_verify_fails_without_setup(self, auth_client: AsyncClient, test_user: User):
        # test_user hasn't set up TOTP secret yet
        resp = await auth_client.post("/api/v1/auth/totp/verify", json={"code": "123456"})
        assert resp.status_code == 400
        assert "not set up" in resp.json()["detail"]
