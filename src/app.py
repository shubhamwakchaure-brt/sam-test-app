"""
app.py — Lambda entry point
FastAPI application wrapped with Mangum (ASGI → Lambda proxy).
Lambda Powertools provides structured logging, X-Ray tracing, and metrics.
"""
import asyncio
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum

from aws_lambda_powertools import Logger, Metrics
from aws_lambda_powertools.logging import correlation_paths
from aws_lambda_powertools.metrics import MetricUnit
from aws_lambda_powertools.utilities.typing import LambdaContext

from routers import v1_router
from routers import v1

# ------------------------------------------------------------------
# Lambda Powertools — initialise once at module level (cold start)
# ------------------------------------------------------------------
logger  = Logger(service=os.environ.get("POWERTOOLS_SERVICE_NAME", "sam-test-fastapi"))
metrics = Metrics()


# ------------------------------------------------------------------
# Application lifecycle
# ------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("FastAPI startup — cold start complete")
    yield
    logger.info("FastAPI shutdown")


# ------------------------------------------------------------------
# FastAPI app
# ------------------------------------------------------------------
app = FastAPI(
    title="SAM Test — FastAPI on Lambda",
    description=(
        "Sample FastAPI application running on AWS Lambda via Mangum. "
        "All routes live under **/v1**. "
        "API Gateway has a single `/v1/{proxy+}` catch-all route; "
        "FastAPI/Mangum handle the rest internally."
    ),
    version="1.0.0",
    # Serve OpenAPI docs under /v1/ so they're accessible via API Gateway
    docs_url="/v1/docs",
    redoc_url="/v1/redoc",
    openapi_url="/v1/openapi.json",
    # When deployed behind API GW, the stage name is the root path.
    # Set root_path so OpenAPI schema resolves /v1/... links correctly.
    root_path=f"/{os.environ.get('STAGE', 'dev')}",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount v1 router — all routes prefixed with /v1
app.include_router(v1_router, prefix="/v1")


# ------------------------------------------------------------------
# Mangum — ASGI adapter for API Gateway (REST / proxy)
# ------------------------------------------------------------------
_mangum_handler = Mangum(app, lifespan="off")


# ------------------------------------------------------------------
# Lambda handler with Powertools decorators
# ------------------------------------------------------------------
@logger.inject_lambda_context(
    correlation_id_path=correlation_paths.API_GATEWAY_REST,
    log_event=True,
)
@metrics.log_metrics(capture_cold_start_metric=True)
def lambda_handler(event: dict, context: LambdaContext) -> dict:
    print('Inside the lambda function')
    metrics.add_metric(name="Invocations", unit=MetricUnit.Count, value=1)

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        print('Inside the lambda function - before calling mangum handler')
        return _mangum_handler(event, context)
    finally:
        try:
            loop.close()
            print('Inside the lambda function - before calling mangum handler - closing loop')
        except Exception:  # pragma: no cover
            pass
