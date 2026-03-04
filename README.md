# sam-test-app

A sample AWS SAM application that runs **FastAPI on AWS Lambda** via
[Mangum](https://mangum.fastapiexpert.com/) (ASGI adapter), using
[Lambda Powertools](https://docs.powertools.aws.dev/lambda/python/) for
structured logging, X-Ray tracing, and CloudWatch metrics.

Verifies that **SAM CLI, Docker, and AWS** all work correctly end-to-end.

## Architecture

```
HTTP client
    │
    ▼
API Gateway  ─── single route: ANY /v1/{proxy+} ───────────────────┐
                                                                    │
                                                          Lambda Function
                                                              (Python 3.12)
                                                                    │
                                                               Mangum
                                                         (ASGI ↔ API GW)
                                                                    │
                                                              FastAPI app
                                                           ┌─────────────┐
                                                           │ GET /v1/health   │
                                                           │ GET /v1/items    │
                                                           │ POST /v1/items   │
                                                           │ GET /v1/items/{id}│
                                                           │ PATCH /v1/items/{id}│
                                                           │ DELETE /v1/items/{id}│
                                                           │ GET /v1/docs     │
                                                           │ GET /v1/redoc    │
                                                           └─────────────┘
```

API Gateway has **one single route** (`ANY /v1/{proxy+}`). FastAPI + Mangum handle all
routing internally — no need to define each endpoint in the SAM template.

## API endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/v1/health` | Health check — runtime info |
| GET | `/v1/items` | List items (supports `?limit` & `?offset`) |
| POST | `/v1/items` | Create an item |
| GET | `/v1/items/{id}` | Get item by ID |
| PATCH | `/v1/items/{id}` | Partially update an item |
| DELETE | `/v1/items/{id}` | Delete an item |
| GET | `/v1/docs` | Swagger UI (auto-generated) |
| GET | `/v1/redoc` | ReDoc (auto-generated) |
| GET | `/v1/openapi.json` | OpenAPI schema |

---

## Prerequisites

| Tool | Minimum version | Install |
|------|----------------|---------|
| [pyenv](https://github.com/pyenv/pyenv) | any | `curl https://pyenv.run \| bash` |
| Python (via pyenv) | **3.12.9** | `make pyenv-setup` |
| [Poetry](https://python-poetry.org/docs/#installation) | 1.8+ | `curl -sSL https://install.python-poetry.org \| python3 -` |
| [AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/install-cliv2.html) | v2 | — |
| [AWS SAM CLI](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html) | 1.100+ | — |
| [Docker](https://docs.docker.com/get-docker/) | 20+ | — |

---

## Quick start

### 1 — Set up Python with pyenv

```bash
# Install Python 3.12.9 (version pinned in .python-version)
make pyenv-setup
# or manually:
pyenv install 3.12.9
pyenv local 3.12.9   # writes .python-version
```

### 2 — Install dependencies with Poetry

```bash
make install
# or: poetry install --with dev
```

Poetry creates an isolated virtualenv and installs both runtime and dev dependencies.
Run `poetry env info` to see where it lives.

### 3 — Verify tools

```bash
pyenv version          # should show 3.12.9
poetry env info        # shows active virtualenv + Python path
aws --version
sam --version
docker info
```

### 4 — Run unit tests (no Docker / AWS required)

```bash
make unit-test
# or: poetry run pytest tests/unit/
```

Expected: all tests pass using **FastAPI TestClient**.

### 5 — Build the SAM application

```bash
make build
# Internally runs:
#   1. poetry export → src/requirements.txt  (runtime deps only)
#   2. sam build --cached --parallel         (Docker builds Lambda packages)
```

✅ If this succeeds, **Docker + SAM + Poetry** are all working correctly.

### 6 — Validate the template

```bash
make validate
# or: sam validate --lint
```

### 7 — Run locally with Docker

```bash
make local-api        # starts API on http://127.0.0.1:3000
```

Open a second terminal and test:

```bash
# Health check
curl http://127.0.0.1:3000/v1/health | jq

# Create an item
curl -X POST http://127.0.0.1:3000/v1/items \
  -H 'Content-Type: application/json' \
  -d '{"name":"hello","description":"my first item","tags":["test"]}' | jq

# List items
curl http://127.0.0.1:3000/v1/items | jq
```

### 8 — Run integration tests against local API

```bash
# In one terminal:
make local-api

# In another terminal:
make integration-test
```

### 9 — Invoke individual functions locally

```bash
make local-invoke-get-all
make local-invoke-put
make local-invoke-get-by-id
make local-invoke-health
```

---

## Deploy to AWS

### First deployment (interactive)

```bash
make deploy-guided
```

This runs `sam deploy --guided` and saves your answers to `samconfig.toml`.

### Subsequent deployments

```bash
make deploy
# or with a specific environment:
ENV=staging make deploy
```

### Post-deploy: run integration tests against deployed API

```bash
# Get API URL from stack outputs
API_URL=$(aws cloudformation describe-stacks \
  --stack-name sam-test-app \
  --query "Stacks[0].Outputs[?OutputKey=='ApiUrl'].OutputValue" \
  --output text)

API_URL=$API_URL make integration-test
```

---

## Teardown

```bash
make destroy
```

> ⚠️ This deletes the CloudFormation stack and **all** associated resources (DynamoDB table, S3 bucket, Lambda functions).

---

## Project structure

```
sam-test-app/
├── template.yaml               # SAM template: API GW + single Lambda
├── samconfig.toml              # SAM CLI config (dev/staging/prod)
├── pyproject.toml              # Poetry: runtime + dev dependencies
├── .python-version             # pyenv: pins Python 3.12.9
├── Makefile                    # Helper commands
├── README.md
├── env-local.json              # Env overrides for local sam invocations
├── events/                     # Sample Lambda invocation payloads
├── src/                        # Lambda source code
│   ├── app.py                  # ← Lambda handler (FastAPI + Mangum entry point)
│   ├── routers/
│   │   └── v1.py               # All /v1/* routes
│   ├── schemas/
│   │   └── item.py             # Pydantic v2 models
│   └── requirements.txt        # Auto-generated by `make poetry-export`
└── tests/
    ├── unit/test_app.py         # FastAPI TestClient tests (no Docker needed)
    └── integration/test_api.py  # HTTP tests against running API
```

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `sam build` fails with Docker error | Ensure Docker daemon is running: `docker info` |
| `sam local start-api` hangs | Pull the Lambda base image first: `docker pull public.ecr.aws/lambda/python:3.12` |
| `moto` import error in unit tests | No longer needed — unit tests use FastAPI TestClient |
| `NoCredentialsError` in unit tests | Unit tests use FastAPI TestClient, no AWS credentials needed |
| `{"message":"Missing Authentication Token"}` | Add `/v1` prefix — all routes are under `/v1/...` |
| 504 timeout on local invoke | Increase Timeout in `template.yaml` Globals |
