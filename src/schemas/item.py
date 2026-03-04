"""
schemas/item.py
Pydantic v2 models for the Item resource.
"""
from typing import Optional
from pydantic import BaseModel, Field


class ItemCreate(BaseModel):
    """Request body for POST /v1/items."""
    name: str = Field(..., min_length=1, max_length=200, description="Item name")
    description: str = Field(default="", max_length=2000, description="Optional description")
    tags: list[str] = Field(default_factory=list, description="Free-form tags")

    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "My Widget",
                "description": "A test item created via FastAPI on Lambda",
                "tags": ["test", "sam", "fastapi"],
            }
        }
    }


class ItemUpdate(BaseModel):
    """Request body for PATCH /v1/items/{id} — all fields optional."""
    name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    description: Optional[str] = Field(default=None, max_length=2000)
    tags: Optional[list[str]] = None


class Item(BaseModel):
    """Full item representation returned by the API."""
    id: str
    name: str
    description: str
    tags: list[str]
    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}


class ItemListResponse(BaseModel):
    """Response envelope for GET /v1/items."""
    total: int = Field(description="Total items in the store")
    count: int = Field(description="Items returned in this page")
    items: list[Item]
