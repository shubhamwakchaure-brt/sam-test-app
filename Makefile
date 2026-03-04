.PHONY: help pyenv-deps pyenv-setup install poetry-export build validate lint \
        unit-test integration-test test \
        local-api local-invoke-get-all local-invoke-get-by-id \
        local-invoke-put local-invoke-delete local-invoke-health \
        deploy deploy-guided destroy clean

# -------------------------------------------------------
# Configuration
# -------------------------------------------------------
STACK_NAME    ?= sam-test-app
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
