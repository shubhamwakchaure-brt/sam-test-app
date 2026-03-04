"""
Integration tests — run AFTER `sam local start-api` is up,
or against a deployed stack.

Usage:
    # Local (requires Docker + sam local start-api)
    API_URL=http://127.0.0.1:3000 pytest tests/integration/

    # Deployed stack
    API_URL=https://<id>.execute-api.us-east-1.amazonaws.com/dev pytest tests/integration/
"""
import os
import uuid
import pytest
import requests

API_URL = os.environ.get("API_URL", "http://127.0.0.1:3000").rstrip("/")


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def url(path: str) -> str:
    return f"{API_URL}{path}"


# ------------------------------------------------------------------
# Tests
# ------------------------------------------------------------------

class TestHealth:
    def test_health_ok(self):
        res = requests.get(url("/v1/health"), timeout=15)
        assert res.status_code == 200
        body = res.json()
        assert body["status"] == "ok"
        assert "timestamp" in body
        assert "runtime" in body


class TestOpenAPI:
    def test_openapi_json(self):
        res = requests.get(url("/v1/openapi.json"), timeout=15)
        assert res.status_code == 200
        assert "paths" in res.json()

    def test_swagger_docs(self):
        res = requests.get(url("/v1/docs"), timeout=15)
        assert res.status_code == 200


class TestItemsCRUD:
    """Full CRUD lifecycle — proves FastAPI + Mangum + API GW all work end-to-end."""

    def test_full_lifecycle(self):
        unique_name = f"Integration Item {uuid.uuid4()}"

        # --- CREATE ---
        create_res = requests.post(
            url("/v1/items"),
            json={"name": unique_name, "description": "integration test", "tags": ["e2e"]},
            timeout=15,
        )
        assert create_res.status_code == 201, f"Create failed: {create_res.text}"
        item = create_res.json()
        assert item["name"] == unique_name
        item_id = item["id"]

        # --- READ ONE ---
        get_res = requests.get(url(f"/v1/items/{item_id}"), timeout=15)
        assert get_res.status_code == 200
        assert get_res.json()["id"] == item_id

        # --- READ ALL ---
        list_res = requests.get(url("/v1/items"), timeout=15)
        assert list_res.status_code == 200
        ids = [i["id"] for i in list_res.json()["items"]]
        assert item_id in ids

        # --- UPDATE ---
        patch_res = requests.patch(
            url(f"/v1/items/{item_id}"),
            json={"name": "Updated Name"},
            timeout=15,
        )
        assert patch_res.status_code == 200
        assert patch_res.json()["name"] == "Updated Name"

        # --- DELETE ---
        del_res = requests.delete(url(f"/v1/items/{item_id}"), timeout=15)
        assert del_res.status_code == 204

        # --- CONFIRM GONE ---
        gone_res = requests.get(url(f"/v1/items/{item_id}"), timeout=15)
        assert gone_res.status_code == 404


class TestEdgeCases:
    def test_get_nonexistent(self):
        res = requests.get(url("/v1/items/does-not-exist-xyz"), timeout=15)
        assert res.status_code == 404

    def test_delete_nonexistent(self):
        res = requests.delete(url("/v1/items/ghost-item-xyz"), timeout=15)
        assert res.status_code == 404

    def test_create_missing_name(self):
        res = requests.post(
            url("/v1/items"),
            json={"description": "no name provided"},
            timeout=15,
        )
        assert res.status_code == 422

