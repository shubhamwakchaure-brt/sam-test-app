"""
Unit tests for the FastAPI v1 router using FastAPI's TestClient.
No Docker, no AWS credentials, no mocks needed — pure in-process HTTP testing.
"""
import sys
import os
import pytest

# Make src/ importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

# Set required Powertools env vars before importing the app
os.environ.setdefault("POWERTOOLS_SERVICE_NAME",      "test-service")
os.environ.setdefault("POWERTOOLS_METRICS_NAMESPACE", "TestApp")
os.environ.setdefault("AWS_DEFAULT_REGION",            "us-east-1")
os.environ.setdefault("AWS_ACCESS_KEY_ID",             "testing")
os.environ.setdefault("AWS_SECRET_ACCESS_KEY",         "testing")
os.environ.setdefault("POWERTOOLS_TRACE_DISABLED",     "true")  # disable X-Ray in tests
os.environ.setdefault("POWERTOOLS_METRICS_DISABLED",   "true")  # disable EMF in tests

from fastapi.testclient import TestClient
from app import app                       # imports FastAPI application
from routers.v1 import _store             # in-memory store reference

client = TestClient(app, raise_server_exceptions=True)


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _clear_store():
    """Reset the in-memory store between tests."""
    _store.clear()


def _create_item(name="Test Widget", description="desc", tags=None):
    payload = {"name": name, "description": description, "tags": tags or ["test"]}
    res = client.post("/v1/items", json=payload)
    assert res.status_code == 201
    return res.json()


# ------------------------------------------------------------------
# /v1/health
# ------------------------------------------------------------------

class TestHealth:
    def test_health_returns_200(self):
        res = client.get("/v1/health")
        assert res.status_code == 200

    def test_health_body(self):
        body = client.get("/v1/health").json()
        assert body["status"] == "ok"
        assert "timestamp" in body
        assert "runtime" in body
        assert body["runtime"]["python"].startswith("3.12")


# ------------------------------------------------------------------
# /v1/items — GET (list)
# ------------------------------------------------------------------

class TestListItems:
    def setup_method(self):
        _clear_store()

    def test_empty_list(self):
        res = client.get("/v1/items")
        assert res.status_code == 200
        body = res.json()
        assert body["total"] == 0
        assert body["items"] == []

    def test_returns_created_items(self):
        _create_item("Alpha")
        _create_item("Beta")
        body = client.get("/v1/items").json()
        assert body["total"] == 2
        assert body["count"] == 2

    def test_pagination_limit(self):
        for i in range(5):
            _create_item(f"Item {i}")
        body = client.get("/v1/items?limit=2").json()
        assert body["count"] == 2
        assert body["total"] == 5

    def test_pagination_offset(self):
        for i in range(5):
            _create_item(f"Item {i}")
        body = client.get("/v1/items?limit=3&offset=3").json()
        assert body["count"] == 2


# ------------------------------------------------------------------
# /v1/items — POST (create)
# ------------------------------------------------------------------

class TestCreateItem:
    def setup_method(self):
        _clear_store()

    def test_create_returns_201(self):
        res = client.post("/v1/items", json={"name": "Widget"})
        assert res.status_code == 201

    def test_create_response_shape(self):
        item = _create_item("My Widget", "A description", ["a", "b"])
        assert "id" in item
        assert item["name"] == "My Widget"
        assert item["description"] == "A description"
        assert item["tags"] == ["a", "b"]
        assert "created_at" in item
        assert "updated_at" in item

    def test_missing_name_returns_422(self):
        res = client.post("/v1/items", json={"description": "no name"})
        assert res.status_code == 422

    def test_empty_name_returns_422(self):
        res = client.post("/v1/items", json={"name": ""})
        assert res.status_code == 422


# ------------------------------------------------------------------
# /v1/items/{id} — GET (single)
# ------------------------------------------------------------------

class TestGetItem:
    def setup_method(self):
        _clear_store()

    def test_get_existing(self):
        item = _create_item("Findable")
        res = client.get(f"/v1/items/{item['id']}")
        assert res.status_code == 200
        assert res.json()["name"] == "Findable"

    def test_get_nonexistent_returns_404(self):
        res = client.get("/v1/items/does-not-exist")
        assert res.status_code == 404


# ------------------------------------------------------------------
# /v1/items/{id} — PATCH (update)
# ------------------------------------------------------------------

class TestUpdateItem:
    def setup_method(self):
        _clear_store()

    def test_partial_update(self):
        item = _create_item("Original")
        res = client.patch(f"/v1/items/{item['id']}", json={"name": "Updated"})
        assert res.status_code == 200
        body = res.json()
        assert body["name"] == "Updated"
        assert body["description"] == item["description"]  # unchanged

    def test_update_tags(self):
        item = _create_item(tags=["old"])
        res = client.patch(f"/v1/items/{item['id']}", json={"tags": ["new1", "new2"]})
        assert res.json()["tags"] == ["new1", "new2"]

    def test_update_nonexistent_returns_404(self):
        res = client.patch("/v1/items/ghost", json={"name": "X"})
        assert res.status_code == 404


# ------------------------------------------------------------------
# /v1/items/{id} — DELETE
# ------------------------------------------------------------------

class TestDeleteItem:
    def setup_method(self):
        _clear_store()

    def test_delete_returns_204(self):
        item = _create_item("Goodbye")
        res = client.delete(f"/v1/items/{item['id']}")
        assert res.status_code == 204

    def test_deleted_item_is_gone(self):
        item = _create_item("Ephemeral")
        client.delete(f"/v1/items/{item['id']}")
        res = client.get(f"/v1/items/{item['id']}")
        assert res.status_code == 404

    def test_delete_nonexistent_returns_404(self):
        res = client.delete("/v1/items/ghost")
        assert res.status_code == 404


# ------------------------------------------------------------------
# OpenAPI schema endpoints
# ------------------------------------------------------------------

class TestOpenAPI:
    def test_openapi_json_reachable(self):
        res = client.get("/v1/openapi.json")
        assert res.status_code == 200
        assert res.json()["info"]["title"] == "SAM Test — FastAPI on Lambda"

    def test_docs_reachable(self):
        res = client.get("/v1/docs")
        assert res.status_code == 200

    def test_redoc_reachable(self):
        res = client.get("/v1/redoc")
        assert res.status_code == 200
