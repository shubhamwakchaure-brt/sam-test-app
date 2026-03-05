.PHONY: help pyenv-deps pyenv-setup install poetry-export build validate lint \
        unit-test integration-test test \
        local-api local-invoke-get-all local-invoke-get-by-id \
        local-invoke-put local-invoke-delete local-invoke-health \
        local-invoke-simple-hello local-invoke-simple-echo local-invoke-simple-items \
        local-invoke-raw-hello local-invoke-raw-echo local-invoke-raw-greet local-invoke-raw-items \
        rie-simple rie-fastapi rie-stop \
        deploy deploy-guided destroy clean

# -------------------------------------------------------
# Configuration
# -------------------------------------------------------
STACK_NAME    ?= sam-test-app-sfsdvrmqplaysclopvexst34135
REGION        ?= us-east-1
ENV           ?= dev
LOCAL_PORT    ?= 3030
API_URL       ?= http://127.0.0.1:$(LOCAL_PORT)

# Python version is driven by .python-version (pyenv)
PYTHON_VERSION := $(shell cat .python-version 2>/dev/null | tr -d '[:space:]' || echo "3.12.9")

# Use poetry run so every command runs inside the Poetry virtualenv
POETRY        ?= poetry
PYTEST        := $(POETRY) run pytest
PYTHON        := $(POETRY) run python

# -------------------------------------------------------
# Default target
# -------------------------------------------------------
help:
	@echo ""
	@echo "  sam-test-app — available targets"
	@echo "  -----------------------------------------------"
	@echo "  pyenv-deps            Install system build deps (apt) needed to compile Python"
	@echo "  pyenv-setup           Install Python $(PYTHON_VERSION) via pyenv + set local"
	@echo "  install               poetry install (create/update virtualenv)"
	@echo "  poetry-export         Export runtime deps → src/requirements.txt"
	@echo "  build                 poetry-export + sam build"
	@echo "  validate              sam validate (lint template)"
	@echo "  unit-test             Run unit tests with moto mocks"
	@echo "  integration-test      Run integration tests (needs running API)"
	@echo "  test                  unit-test + build"
	@echo "  local-api             Start local API via Docker (blocking)"
	@echo "  local-invoke-simple-hello   Invoke SimpleFunction GET /v2/hello"
	@echo "  local-invoke-simple-echo    Invoke SimpleFunction GET /v2/echo/..."
	@echo "  local-invoke-simple-items   Invoke SimpleFunction GET /v2/items"
	@echo "  local-invoke-raw-hello      Invoke RawFunction GET /v3/hello"
	@echo "  local-invoke-raw-echo       Invoke RawFunction GET /v3/echo/..."
	@echo "  local-invoke-raw-greet      Invoke RawFunction POST /v3/greet"
	@echo "  local-invoke-raw-items      Invoke RawFunction GET /v3/items"
	@echo "  rie-simple            Start SimpleFunction via built-in RIE on port 9001"
	@echo "  rie-fastapi           Start FastApiFunction via built-in RIE on port 9000"
	@echo "  rie-stop              Stop all running RIE containers"
	@echo "  deploy-guided         sam deploy --guided (first time)"
	@echo "  deploy                sam deploy (subsequent)"
	@echo "  destroy               Delete the deployed CloudFormation stack"
	@echo "  clean                 Remove build artifacts and caches"
	@echo ""

# -------------------------------------------------------
# pyenv  —  install & pin the correct Python version
# -------------------------------------------------------
pyenv-deps:
	@echo ">>> Installing system build dependencies for pyenv (requires sudo)..."
	sudo apt-get update -qq
	sudo apt-get install -y \
	  build-essential \
	  curl \
	  git \
	  libbz2-dev \
	  libffi-dev \
	  liblzma-dev \
	  libncursesw5-dev \
	  libreadline-dev \
	  libsqlite3-dev \
	  libssl-dev \
	  libxml2-dev \
	  libxmlsec1-dev \
	  tk-dev \
	  xz-utils \
	  zlib1g-dev
	@echo ">>> System deps installed."

pyenv-setup: pyenv-deps
	@echo ">>> Removing any broken previous install of Python $(PYTHON_VERSION)..."
	pyenv uninstall -f $(PYTHON_VERSION) 2>/dev/null || true
	@echo ">>> Installing Python $(PYTHON_VERSION) via pyenv..."
	pyenv install $(PYTHON_VERSION)
	pyenv local $(PYTHON_VERSION)
	@echo ">>> Active Python: $$(python --version)"
	@echo ">>> Tip: run 'make install' next to set up the Poetry virtualenv."

# -------------------------------------------------------
# Poetry  —  dependency management
# -------------------------------------------------------
install:
	@echo ">>> Pinning Poetry to pyenv Python $(PYTHON_VERSION)..."
	$(POETRY) env use "$$(pyenv which python)"
	@echo ">>> Installing dependencies via Poetry..."
	$(POETRY) install --with dev
	@echo ">>> Virtualenv: $$($(POETRY) env info --path)"
	@echo ">>> Python:     $$($(POETRY) run python --version)"

# Export ONLY runtime deps (no dev/test packages) into the file SAM consumes
poetry-export:
	@echo ">>> Exporting runtime requirements to src/requirements.txt..."
	$(POETRY) export \
	  --without dev \
	  --without-hashes \
	  --format requirements.txt \
	  --output src/requirements.txt
	@echo ">>> src/requirements.txt updated."

# -------------------------------------------------------
# Build & Validate
# -------------------------------------------------------

# Always regenerate src/requirements.txt from the lock file before building
build: poetry-export
	sam build --cached --parallel

validate:
	sam validate --lint

lint: validate

# -------------------------------------------------------
# Unit Tests  (no Docker / no AWS credentials needed)
# -------------------------------------------------------
unit-test:
	$(PYTEST) tests/unit/ -v --tb=short \
	  --cov=src --cov-report=term-missing --cov-report=html

# -------------------------------------------------------
# Local invocation (requires Docker)
# -------------------------------------------------------
local-api: build
	@echo ">>> Starting local API on http://127.0.0.1:$(LOCAL_PORT) — Ctrl+C to stop"
	sam local start-api \
	  --port $(LOCAL_PORT) \
	  --warm-containers EAGER \
	  --env-vars env-local.json

local-invoke-get-all: build
	sam local invoke FastApiFunction \
	  --event events/event-get-all-items.json

local-invoke-get-by-id: build
	sam local invoke FastApiFunction \
	  --event events/event-get-by-id.json

local-invoke-put: build
	sam local invoke FastApiFunction \
	  --event events/event-put-item.json

local-invoke-delete: build
	sam local invoke FastApiFunction \
	  --event events/event-delete-item.json

local-invoke-health: build
	sam local invoke FastApiFunction \
	  --event events/event-health.json

local-invoke-simple-hello: build
	sam local invoke SimpleFunction \
	  --env-vars env-local.json \
	  --event events/v2-hello.json

local-invoke-simple-echo: build
	sam local invoke SimpleFunction \
	  --env-vars env-local.json \
	  --event events/v2-echo.json

local-invoke-simple-items: build
	sam local invoke SimpleFunction \
	  --env-vars env-local.json \
	  --event events/v2-items.json

local-invoke-raw-hello: build
	sam local invoke RawFunction \
	  --env-vars env-local.json \
	  --event events/v3-hello.json

local-invoke-raw-echo: build
	sam local invoke RawFunction \
	  --env-vars env-local.json \
	  --event events/v3-echo.json

local-invoke-raw-greet: build
	sam local invoke RawFunction \
	  --env-vars env-local.json \
	  --event events/v3-greet.json

local-invoke-raw-items: build
	sam local invoke RawFunction \
	  --env-vars env-local.json \
	  --event events/v3-items.json

# -------------------------------------------------------
# RIE — Lambda Runtime Interface Emulator
# Bypasses SAM CLI (and Zscaler) by running the Lambda
# RIE HTTP server directly inside the Docker container.
#
# Usage:
#   make rie-simple          (start in background)
#   curl --noproxy '*' -s -X POST http://localhost:9001/2015-03-31/functions/function/invocations \
#     -H 'Content-Type: application/json' -d @events/v2-hello.json | python3 -m json.tool
#
#   make rie-fastapi         (start in background)
#   curl --noproxy '*' -s -X POST http://localhost:9000/2015-03-31/functions/function/invocations \
#     -H 'Content-Type: application/json' -d @events/health.json | python3 -m json.tool
#
#   make rie-stop            (stop both containers)
# -------------------------------------------------------
RIE_IMAGE     ?= public.ecr.aws/lambda/python:3.13-rapid-x86_64
RIE_SIMPLE_PORT  ?= 9001
RIE_FASTAPI_PORT ?= 9000

rie-simple: build
	@echo ">>> Stopping any existing rie-simple container..."
	docker rm -f rie-simple 2>/dev/null || true
	@echo ">>> Starting SimpleFunction RIE on http://localhost:$(RIE_SIMPLE_PORT)"
	docker run -d --name rie-simple \
	  -v $(PWD)/.aws-sam/build/SimpleFunction:/var/task:ro \
	  -e STAGE=$(ENV) \
	  -p $(RIE_SIMPLE_PORT):8080 \
	  $(RIE_IMAGE) app.lambda_handler
	@echo ">>> Invoke with:"
	@echo "    curl --noproxy '*' -s -X POST http://localhost:$(RIE_SIMPLE_PORT)/2015-03-31/functions/function/invocations \\"
	@echo "      -H 'Content-Type: application/json' -d @events/v2-hello.json | python3 -m json.tool"

rie-fastapi: build
	@echo ">>> Stopping any existing rie-fastapi container..."
	docker rm -f rie-fastapi 2>/dev/null || true
	@echo ">>> Starting FastApiFunction RIE on http://localhost:$(RIE_FASTAPI_PORT)"
	docker run -d --name rie-fastapi \
	  -v $(PWD)/.aws-sam/build/FastApiFunction:/var/task:ro \
	  -e POWERTOOLS_SERVICE_NAME=sam-test-fastapi \
	  -e POWERTOOLS_METRICS_NAMESPACE=SamTestApp \
	  -e POWERTOOLS_TRACE_DISABLED=true \
	  -e LOG_LEVEL=DEBUG \
	  -e STAGE=$(ENV) \
	  -p $(RIE_FASTAPI_PORT):8080 \
	  $(RIE_IMAGE) app.lambda_handler
	@echo ">>> Invoke with:"
	@echo "    curl --noproxy '*' -s -X POST http://localhost:$(RIE_FASTAPI_PORT)/2015-03-31/functions/function/invocations \\"
	@echo "      -H 'Content-Type: application/json' -d @events/health.json | python3 -m json.tool"

rie-stop:
	@echo ">>> Stopping RIE containers..."
	docker rm -f rie-simple rie-fastapi 2>/dev/null || true
	@echo ">>> Done."

# -------------------------------------------------------
# Integration Tests  (requires local-api or deployed stack)
# -------------------------------------------------------
integration-test:
	API_URL=$(API_URL) $(PYTEST) tests/integration/ -v --tb=short

# -------------------------------------------------------
# Full test suite
# -------------------------------------------------------
test: unit-test build

# -------------------------------------------------------
# Deploy
# -------------------------------------------------------
deploy-guided: build
	sam deploy --guided \
	  --stack-name $(STACK_NAME) \
	  --region $(REGION) \
	  --parameter-overrides Environment=$(ENV)

deploy: build
	sam deploy \
	  --stack-name $(STACK_NAME) \
	  --region $(REGION) \
	  --parameter-overrides Environment=$(ENV) \
	  --no-confirm-changeset \
	  --no-fail-on-empty-changeset

# -------------------------------------------------------
# Destroy
# -------------------------------------------------------
destroy:
	@echo "WARNING: This will delete the stack $(STACK_NAME) and ALL its resources."
	@read -p "Type 'yes' to confirm: " confirm && [ "$$confirm" = "yes" ]
	aws cloudformation delete-stack \
	  --stack-name $(STACK_NAME) \
	  --region $(REGION)
	@echo "Waiting for stack deletion to complete..."
	aws cloudformation wait stack-delete-complete \
	  --stack-name $(STACK_NAME) \
	  --region $(REGION)
	@echo "Stack deleted."

# -------------------------------------------------------
# Clean
# -------------------------------------------------------
clean:
	rm -rf .aws-sam htmlcov .pytest_cache .coverage
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete
	$(POETRY) env remove --all 2>/dev/null || true
