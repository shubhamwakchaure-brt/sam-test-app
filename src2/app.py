"""
app.py — Simple Lambda entry point (no Powertools)
FastAPI wrapped with Mangum. All routes under /v2.
"""
import asyncio

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum

from routers import v2_router

# ------------------------------------------------------------------
# FastAPI app
# ------------------------------------------------------------------
app = FastAPI(
    title="Simple Lambda — v2",
    description="Minimal FastAPI on AWS Lambda via Mangum. No Powertools.",
    version="1.0.0",
    docs_url="/v2/docs",
    redoc_url="/v2/redoc",
    openapi_url="/v2/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(v2_router, prefix="/v2")

# ------------------------------------------------------------------
# Mangum — ASGI adapter
# ------------------------------------------------------------------
_mangum_handler = Mangum(app, lifespan="off")


# ------------------------------------------------------------------
# Lambda entry point
# ------------------------------------------------------------------
def lambda_handler(event: dict, context) -> dict:
    """AWS Lambda entry point — delegates to FastAPI via Mangum."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return _mangum_handler(event, context)
    finally:
        try:
            loop.close()
        except Exception:
            pass
