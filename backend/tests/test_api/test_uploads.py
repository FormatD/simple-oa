"""API tests for file uploads."""
from __future__ import annotations

import io

from httpx import AsyncClient


class TestUploads:
    async def test_list_uploads(self, client_with_org: AsyncClient):
        resp = await client_with_org.get("/api/v1/uploads")
        assert resp.status_code == 200
        assert "data" in resp.json()

    async def test_upload_file(self, client_with_org: AsyncClient):
        file_content = b"test file content"
        resp = await client_with_org.post(
            "/api/v1/uploads",
            files={"file": ("test.txt", io.BytesIO(file_content), "text/plain")},
        )
        assert resp.status_code == 201
        data = resp.json()["data"]
        assert data["original_filename"] == "test.txt"
        assert data["mime_type"] == "text/plain"

    async def test_get_upload(self, client_with_org: AsyncClient):
        file_content = b"test content"
        create_resp = await client_with_org.post(
            "/api/v1/uploads",
            files={"file": ("test.txt", io.BytesIO(file_content), "text/plain")},
        )
        upload_id = create_resp.json()["data"]["id"]
        resp = await client_with_org.get(f"/api/v1/uploads/{upload_id}")
        assert resp.status_code == 200
        assert resp.json()["data"]["original_filename"] == "test.txt"

    async def test_delete_upload(self, client_with_org: AsyncClient):
        file_content = b"test content"
        create_resp = await client_with_org.post(
            "/api/v1/uploads",
            files={"file": ("test.txt", io.BytesIO(file_content), "text/plain")},
        )
        upload_id = create_resp.json()["data"]["id"]
        resp = await client_with_org.delete(f"/api/v1/uploads/{upload_id}")
        assert resp.status_code == 200
