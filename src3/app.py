"""
app.py — Pure Python Lambda handler. No frameworks, no dependencies.

API Gateway REST proxy integration format:
  event["httpMethod"]     — GET / POST / PUT / DELETE ...
  event["path"]           — /v3/hello, /v3/items/42, ...
  event["body"]           — JSON string (or None)
  event["pathParameters"] — dict of path placeholders (or None)

Routes
------
  GET  /v3/hello          Hello World
  GET  /v3/echo/{text}    Echo text back with length + reversed
  POST /v3/greet          Body: {"name": "..."} → personalised greeting
  GET  /v3/items          List all hardcoded items
  GET  /v3/items/{id}     Fetch one item by integer id
"""

import json
import os
from datetime import datetime, timezone


# ------------------------------------------------------------------
# Helper — build an API Gateway proxy response
# ------------------------------------------------------------------
def _resp(status: int, body: dict | list | str) -> dict:
    return {
        "statusCode": status,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body),
    }


def _err(status: int, detail: str) -> dict:
    return _resp(status, {"error": detail})


# ------------------------------------------------------------------
# Static data
# ------------------------------------------------------------------
_ITEMS = [
    {"id": 1, "name": "Widget",       "price": 9.99},
    {"id": 2, "name": "Gadget",       "price": 19.49},
    {"id": 3, "name": "Doohickey",    "price": 4.99},
    {"id": 4, "name": "Thingamajig",  "price": 34.00},
]


# ------------------------------------------------------------------
# Route handlers
# ------------------------------------------------------------------
def _handle_hello() -> dict:
    return _resp(200, {
        "message": "Hello, World!",
        "route":   "GET /v3/hello",
        "time":    datetime.now(timezone.utc).isoformat(),
        "stage":   os.environ.get("STAGE", "local"),
    })


def _handle_echo(text: str) -> dict:
    if not text:
        return _err(400, "text must not be empty")
    return _resp(200, {
        "echo":     text,
        "length":   len(text),
        "reversed": text[::-1],
        "upper":    text.upper(),
    })


def _handle_greet(raw_body: str | None) -> dict:
    if not raw_body:
        return _err(400, "request body is required")
    try:
        payload = json.loads(raw_body)
    except (ValueError, TypeError):
        return _err(400, "body must be valid JSON")
    name = payload.get("name", "").strip()
    if not name:
        return _err(400, "'name' field is required and must not be empty")
    return _resp(200, {"greeting": f"Hello, {name}! Welcome to v3."})


def _handle_list_items() -> dict:
    return _resp(200, {"count": len(_ITEMS), "items": _ITEMS})


def _handle_get_item(item_id_str: str) -> dict:
    try:
        item_id = int(item_id_str)
    except (ValueError, TypeError):
        return _err(400, f"id must be an integer, got '{item_id_str}'")
    item = next((i for i in _ITEMS if i["id"] == item_id), None)
    if item is None:
        return _err(404, f"item with id {item_id} not found")
    return _resp(200, item)


# ------------------------------------------------------------------
# Router — maps (method, path pattern) to handler via if/elif/else
# ------------------------------------------------------------------
def _route(method: str, path: str, path_params: dict, body: str | None) -> dict:
    """
    Strip leading slash and split into segments for matching.
    e.g. /v3/items/2  →  ['v3', 'items', '2']
    """
    parts = [p for p in path.strip("/").split("/") if p]
    # parts[0] is always 'v3' (API GW only sends paths that match /v3/*)

    # GET /v3/hello
    if method == "GET" and parts == ["v3", "hello"]:
        return _handle_hello()

    # GET /v3/echo/{text}
    elif method == "GET" and len(parts) == 3 and parts[1] == "echo":
        return _handle_echo(parts[2])

    # POST /v3/greet
    elif method == "POST" and parts == ["v3", "greet"]:
        return _handle_greet(body)

    # GET /v3/items
    elif method == "GET" and parts == ["v3", "items"]:
        return _handle_list_items()

    # GET /v3/items/{id}
    elif method == "GET" and len(parts) == 3 and parts[1] == "items":
        return _handle_get_item(parts[2])

    # No match
    else:
        return _err(404, f"no route for {method} /{'/'.join(parts)}")


# ------------------------------------------------------------------
# Lambda entry point
# ------------------------------------------------------------------
def lambda_handler(event: dict, context) -> dict:
    method      = event.get("httpMethod", "GET")
    path        = event.get("path", "/")
    path_params = event.get("pathParameters") or {}
    body        = event.get("body")

    print(f"[v3] {method} {path}")  # shows in CloudWatch / sam local logs

    return _route(method, path, path_params, body)
