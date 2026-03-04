"""
routers/v1.py
All application routes under the /v1 prefix.
FastAPI handles routing internally via Mangum — API Gateway only sees /v1/{proxy+}.
"""
import os
import platform
import sys
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, status
from aws_lambda_powertools import Logger, Tracer

from schemas.item import Item, ItemCreate, ItemUpdate, ItemListResponse

logger = Logger(child=True)
tracer = Tracer()

router = APIRouter(tags=["v1"])

# ------------------------------------------------------------------
# In-memory store (swap for DynamoDB / RDS in production)
# ------------------------------------------------------------------
_store: dict[str, Item] = {}


# ------------------------------------------------------------------
# /v1/health
# ------------------------------------------------------------------
@router.get(
    "/health",
    summary="Health check",
    response_description="Service health status",
)
@tracer.capture_method
def health_check():
    """Verify the Lambda function, runtime, and FastAPI are all running."""
    return {
        "status": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "service": os.environ.get("POWERTOOLS_SERVICE_NAME", "sam-test-fastapi"),
        "environment": os.environ.get("STAGE", "local"),
        "runtime": {
            "python": sys.version,
            "platform": platform.platform(),
        },
    }


# ------------------------------------------------------------------
# /v1/items  — CRUD
# ------------------------------------------------------------------
@router.get(
    "/items",
    response_model=ItemListResponse,
    summary="List all items",
)
@tracer.capture_method
def list_items(
    limit: int = Query(default=50, ge=1, le=500, description="Max items to return"),
    offset: int = Query(default=0, ge=0, description="Pagination offset"),
):
    """Return a paginated list of all items."""
    all_items = list(_store.values())
    page = all_items[offset : offset + limit]
    logger.info("list_items", extra={"total": len(all_items), "returned": len(page)})
    return ItemListResponse(total=len(all_items), count=len(page), items=page)


@router.post(
    "/items",
    response_model=Item,
    status_code=status.HTTP_201_CREATED,
    summary="Create an item",
)
@tracer.capture_method
def create_item(payload: ItemCreate):
    """Create a new item and persist it to the store."""
    import uuid
    item = Item(
        id=str(uuid.uuid4()),
        name=payload.name,
        description=payload.description,
        tags=payload.tags,
        created_at=datetime.now(timezone.utc).isoformat(),
        updated_at=datetime.now(timezone.utc).isoformat(),
    )
    _store[item.id] = item
    logger.info("create_item", extra={"item_id": item.id})
    return item


@router.get(
    "/items/{item_id}",
    response_model=Item,
    summary="Get item by ID",
)
@tracer.capture_method
def get_item(item_id: str):
    """Fetch a single item by its ID."""
    item = _store.get(item_id)
    if not item:
        raise HTTPException(status_code=404, detail=f"Item '{item_id}' not found")
    return item


@router.patch(
    "/items/{item_id}",
    response_model=Item,
    summary="Update an item",
)
@tracer.capture_method
def update_item(item_id: str, payload: ItemUpdate):
    """Partially update an existing item."""
    item = _store.get(item_id)
    if not item:
        raise HTTPException(status_code=404, detail=f"Item '{item_id}' not found")

    update_data = payload.model_dump(exclude_unset=True)
    updated = item.model_copy(
        update={**update_data, "updated_at": datetime.now(timezone.utc).isoformat()}
    )
    _store[item_id] = updated
    logger.info("update_item", extra={"item_id": item_id, "fields": list(update_data)})
    return updated


@router.delete(
    "/items/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an item",
)
@tracer.capture_method
def delete_item(item_id: str):
    """Delete an item by ID."""
    if item_id not in _store:
        raise HTTPException(status_code=404, detail=f"Item '{item_id}' not found")
    del _store[item_id]
    logger.info("delete_item", extra={"item_id": item_id})
