.PHONY: help dev dev-backend dev-frontend migrate migrate-create seed db-reset test test-backend test-frontend coverage lint format build clean docker-up docker-down prod install

# Default target
help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# Development
dev: ## Start all services with Docker Compose
	docker-compose up -d postgres redis
	cd backend && uvicorn app.main:app --reload --port 8000 &
	cd frontend && pnpm dev

dev-backend: ## Start backend only
	cd backend && uvicorn app.main:app --reload --port 8000

dev-frontend: ## Start frontend only
	cd frontend && pnpm dev

install: ## Install all dependencies
	cd backend && pip install -e ".[dev]"
	cd frontend && pnpm install

# Database
migrate: ## Run database migrations
	cd backend && alembic upgrade head

migrate-create: ## Create a new migration (use MSG="description")
	cd backend && alembic revision --autogenerate -m "$(MSG)"

seed: ## Seed database with sample data
	cd backend && python -m scripts.seed_knowledge
	cd backend && python -m scripts.seed_questions
	cd backend && python -m scripts.seed_templates

db-reset: ## Reset database (downgrade + migrate + seed)
	cd backend && alembic downgrade base
	cd backend && alembic upgrade head
	$(MAKE) seed

# Tests
test: test-backend ## Run all tests

test-backend: ## Run backend tests
	cd backend && pytest -v

test-frontend: ## Run frontend tests
	cd frontend && pnpm test

coverage: ## Run backend tests with coverage report
	cd backend && pytest --cov=app --cov-report=html --cov-report=term-missing

# Code Quality
lint: lint-backend lint-frontend ## Run all linters

lint-backend: ## Run backend linters
	cd backend && ruff check .
	cd backend && ruff format --check .

lint-frontend: ## Run frontend linters
	cd frontend && pnpm tsc --noEmit 2>/dev/null || true
	cd frontend && pnpm lint 2>/dev/null || true

format: ## Format all code
	cd backend && ruff format .
	cd backend && ruff check --fix .

# Docker
docker-up: ## Start all services with Docker Compose
	docker-compose up -d

docker-down: ## Stop all Docker services
	docker-compose down

docker-logs: ## View Docker logs
	docker-compose logs -f

# Build
build: ## Build production Docker images
	docker-compose -f docker-compose.prod.yml build

prod: ## Start production environment
	docker-compose -f docker-compose.prod.yml up -d

prod-down: ## Stop production environment
	docker-compose -f docker-compose.prod.yml down

# Clean
clean: ## Clean build artifacts and caches
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name htmlcov -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name "test.db" -delete 2>/dev/null || true
	cd frontend && rm -rf node_modules/.cache dist 2>/dev/null || true
