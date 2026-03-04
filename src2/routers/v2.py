"""
routers/v2.py
Simple routes — no Powertools, no external dependencies beyond FastAPI.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(tags=["v2"])


# ------------------------------------------------------------------
# Schemas
# ------------------------------------------------------------------
class GreetRequest(BaseModel):
    name: str


class Item(BaseModel):
    id: int
    name: str
    price: float


# ------------------------------------------------------------------
# Routes
# ------------------------------------------------------------------

@router.get("/hello", summary="Hello World")
def hello_world():
    """Returns a simple Hello World message."""
    return {"message": "Hello, World!", "route": "GET /v2/hello"}


@router.get("/echo/{text}", summary="Echo text")
def echo(text: str):
    """Echoes back the provided text with its length."""
    return {
        "echo": text,
        "length": len(text),
        "reversed": text[::-1],
    }


@router.post("/greet", summary="Greet by name")
def greet(body: GreetRequest):
    """Returns a personalised greeting for the given name."""
    if not body.name.strip():
        raise HTTPException(status_code=400, detail="name must not be empty")
    return {"greeting": f"Hello, {body.name}! Welcome to v2."}


@router.get("/items", summary="List sample items")
def list_items():
    """Returns a static list of sample items."""
    items = [
        Item(id=1, name="Widget",  price=9.99),
        Item(id=2, name="Gadget",  price=19.49),
        Item(id=3, name="Doohickey", price=4.99),
        Item(id=4, name="Thingamajig", price=34.00),
    ]
    return {"count": len(items), "items": [i.model_dump() for i in items]}
