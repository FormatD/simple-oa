"""API tests for Wiki module: folders, pages, search."""
from __future__ import annotations

from httpx import AsyncClient


class TestWikiFolders:
    async def test_create_folder(self, client_with_org: AsyncClient):
        resp = await client_with_org.post("/api/v1/wiki/folders", json={
            "name": "Docs",
        })
        assert resp.status_code == 201
        assert resp.json()["data"]["name"] == "Docs"

    async def test_list_folders(self, client_with_org: AsyncClient):
        await client_with_org.post("/api/v1/wiki/folders", json={"name": "Docs"})
        resp = await client_with_org.get("/api/v1/wiki/folders")
        assert resp.status_code == 200
        assert len(resp.json()["data"]) >= 1

    async def test_update_folder(self, client_with_org: AsyncClient):
        create_resp = await client_with_org.post("/api/v1/wiki/folders", json={
            "name": "Docs",
        })
        folder_id = create_resp.json()["data"]["id"]
        resp = await client_with_org.put(
            f"/api/v1/wiki/folders/{folder_id}",
            json={"name": "Documents"},
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["name"] == "Documents"

    async def test_delete_folder(self, client_with_org: AsyncClient):
        create_resp = await client_with_org.post("/api/v1/wiki/folders", json={
            "name": "Temp",
        })
        folder_id = create_resp.json()["data"]["id"]
        resp = await client_with_org.delete(f"/api/v1/wiki/folders/{folder_id}")
        assert resp.status_code == 200


class TestWikiPages:
    async def test_create_page(self, client_with_org: AsyncClient):
        resp = await client_with_org.post("/api/v1/wiki/pages", json={
            "title": "Welcome",
            "content": "Hello world",
        })
        assert resp.status_code == 201
        assert resp.json()["data"]["title"] == "Welcome"

    async def test_list_pages(self, client_with_org: AsyncClient):
        await client_with_org.post("/api/v1/wiki/pages", json={
            "title": "Page 1", "content": "Content 1",
        })
        resp = await client_with_org.get("/api/v1/wiki/pages")
        assert resp.status_code == 200
        assert len(resp.json()["data"]) >= 1

    async def test_get_page(self, client_with_org: AsyncClient):
        create_resp = await client_with_org.post("/api/v1/wiki/pages", json={
            "title": "My Page", "content": "Content",
        })
        page_id = create_resp.json()["data"]["id"]
        resp = await client_with_org.get(f"/api/v1/wiki/pages/{page_id}")
        assert resp.status_code == 200
        assert resp.json()["data"]["title"] == "My Page"

    async def test_update_page(self, client_with_org: AsyncClient):
        create_resp = await client_with_org.post("/api/v1/wiki/pages", json={
            "title": "Page", "content": "Old",
        })
        page_id = create_resp.json()["data"]["id"]
        resp = await client_with_org.put(f"/api/v1/wiki/pages/{page_id}", json={
            "title": "Updated", "content": "New",
        })
        assert resp.status_code == 200
        assert resp.json()["data"]["title"] == "Updated"

    async def test_delete_page(self, client_with_org: AsyncClient):
        create_resp = await client_with_org.post("/api/v1/wiki/pages", json={
            "title": "Temp", "content": "temp",
        })
        page_id = create_resp.json()["data"]["id"]
        resp = await client_with_org.delete(f"/api/v1/wiki/pages/{page_id}")
        assert resp.status_code == 200

    async def test_search_pages(self, client_with_org: AsyncClient):
        await client_with_org.post("/api/v1/wiki/pages", json={
            "title": "API Guide", "content": "How to use the API",
        })
        resp = await client_with_org.get("/api/v1/wiki/search?q=API")
        assert resp.status_code == 200
        assert isinstance(resp.json()["data"], list)
