# TYPEFASTER-CLI — developer commands
# Phase 1 (offline) targets are active. `up`/`down` arrive with Phase 2 (Docker/Redis).

.DEFAULT_GOAL := help
PYTHON ?= python3

# Make the package importable from the monorepo layout (client/typefaster)
# regardless of how the editable install resolves paths on a given OS.
export PYTHONPATH := client

.PHONY: help install dev play test test-cov lint format typecheck check seed clean up down

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

install: ## Install package + dev deps in editable mode
	$(PYTHON) -m pip install -e ".[dev]"

dev: install ## Alias for a full dev environment setup
	@echo "Dev environment ready. Run 'make play' to start the game."

play: ## Launch the game (offline)
	typefaster

test: ## Run the test suite
	pytest

test-cov: ## Run tests with coverage report
	pytest --cov=typefaster --cov-report=term-missing

lint: ## Ruff lint
	ruff check client tests

format: ## Auto-format (black) + autofix (ruff)
	black client tests
	ruff check --fix client tests

typecheck: ## MyPy static type check
	mypy

check: lint typecheck test ## Run lint + typecheck + tests (CI parity)

seed: ## Validate / (re)build the quotes dataset
	$(PYTHON) scripts/seed_quotes.py

clean: ## Remove caches and build artifacts
	rm -rf .pytest_cache .mypy_cache .ruff_cache htmlcov .coverage build dist *.egg-info
	find . -type d -name __pycache__ -prune -exec rm -rf {} +

# ── Online stack (Phase 2) ─────────────────────────────────────────────
up: ## Start the online stack (redis + server) via Docker Compose
	docker compose up -d --build

up-proxy: ## Start the full stack including the nginx TLS proxy
	docker compose --profile proxy up -d --build

down: ## Stop the online stack
	docker compose down

logs: ## Tail server logs
	docker compose logs -f server

server-dev: ## Run the server locally (needs a local Redis on :6379)
	cd server && uvicorn app.main:app --reload --port 8000

server-test: ## Run the server test suite
	cd server && pytest
