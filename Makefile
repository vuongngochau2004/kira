SHELL := /bin/bash
# KIRA - Makefile
.PHONY: help dev backend frontend dev-worker infra infra-stop infra-restart test test-backend test-integration install clean lint eval-rag \
        deploy deploy-tunnel tunnel-url deploy-logs deploy-stop

# Default target
.DEFAULT_GOAL := help

# Colors for output
BLUE  := \033[0;34m
GREEN := \033[0;32m
RED   := \033[0;31m
NC    := \033[0m

# Project paths
BACKEND_DIR := backend
FRONTEND_DIR := frontend

# Ports
BACKEND_PORT := 8006
FRONTEND_PORT := 3001

##@ General

help: ## Show this help message
	@echo "$(BLUE)KIRA - Available commands:$(NC)"
	@echo ""
	@grep -E '^##@|^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-15s$(NC) %s\n", $$1, $$2}' | sed 's/^##@//'
	@echo ""

##@ Development

dev: ## Start both backend and frontend (requires tmux)
	@echo "$(BLUE)Starting KIRA...$(NC)"
	@tmux new-session -d -s kira -n backend "cd $(BACKEND_DIR) && source .venv/bin/activate && python -m kira.main"
	@tmux new-window -t kira:1 -n worker "cd $(BACKEND_DIR) && source .venv/bin/activate && celery -A kira.worker.celery_app worker --loglevel=info --concurrency=$${CELERY_WORKER_CONCURRENCY:-1}"
	@tmux new-window -t kira:2 -n frontend "cd $(FRONTEND_DIR) && npm run dev"
	@tmux attach-session -t kira
	@echo "$(GREEN)Both services started in tmux session 'kira'$(NC)"

dev-backend: ## Start backend only
	@echo "$(BLUE)Starting backend on port $(BACKEND_PORT)...$(NC)"
	@cd $(BACKEND_DIR) && source .venv/bin/activate && python -m kira.main

dev-worker: ## Start Celery document worker
	@echo "$(BLUE)Starting Celery worker...$(NC)"
	@cd $(BACKEND_DIR) && source .venv/bin/activate && celery -A kira.worker.celery_app worker --loglevel=info --concurrency=$${CELERY_WORKER_CONCURRENCY:-1}

dev-frontend: ## Start frontend only
	@echo "$(BLUE)Starting frontend on port $(FRONTEND_PORT)...$(NC)"
	@cd $(FRONTEND_DIR) && npm run dev

##@ Infrastructure

infra: ## Start infrastructure (Postgres, Qdrant, MinIO)
	@echo "$(BLUE)Starting infrastructure...$(NC)"
	@docker compose up -d
	@echo "$(GREEN)Infrastructure started$(NC)"
	@make infra-status

infra-stop: ## Stop infrastructure
	@echo "$(BLUE)Stopping infrastructure...$(NC)"
	@docker compose down
	@echo "$(GREEN)Infrastructure stopped$(NC)"

infra-restart: ## Restart infrastructure
	@echo "$(BLUE)Restarting infrastructure...$(NC)"
	@docker compose restart
	@echo "$(GREEN)Infrastructure restarted$(NC)"
	@make infra-status

infra-status: ## Show infrastructure status
	@echo "$(BLUE)Infrastructure status:$(NC)"
	@docker compose ps

infra-logs: ## Show infrastructure logs
	@docker compose logs -f

##@ Deployment (Docker + Cloudflare Tunnel)

deploy: ## Build and run full stack in Docker (frontend on :3002, no tunnel)
	@printf "$(BLUE)Starting KIRA full stack in Docker...$(NC)\n"
	@docker compose --profile app up -d --build
	@docker compose --profile app ps

deploy-tunnel: ## Run full stack + Cloudflare Tunnel (Quick Tunnel unless CLOUDFLARE_TUNNEL_TOKEN is set)
	@printf "$(BLUE)Starting KIRA with Cloudflare Tunnel...$(NC)\n"
	@docker compose --profile tunnel up -d --build
	@sleep 5
	@$(MAKE) --no-print-directory tunnel-url

tunnel-url: ## Print the active Cloudflare Quick Tunnel URL
	@printf "$(BLUE)Public URL:$(NC)\n"
	@docker logs kira-simple-tunnel 2>&1 | grep -o 'https://[a-z0-9-]*\.trycloudflare\.com' | tail -n 1 \
		|| echo "Not found yet (or Named Tunnel in use). Retry 'make tunnel-url' in a few seconds."

deploy-logs: ## Follow logs of the deployed app containers
	@docker compose --profile tunnel logs -f api worker frontend cloudflared

deploy-stop: ## Stop app + tunnel containers (infrastructure keeps running)
	@printf "$(BLUE)Stopping KIRA app containers...$(NC)\n"
	@docker compose --profile tunnel stop cloudflared frontend worker api
	@docker compose --profile tunnel rm -f cloudflared frontend worker api
	@printf "$(GREEN)App containers stopped$(NC)\n"

##@ Installation

install: install-backend install-frontend ## Install both backend and frontend dependencies

install-backend: ## Install backend dependencies
	@echo "$(BLUE)Installing backend dependencies...$(NC)"
	@cd $(BACKEND_DIR) && uv sync --extra dev
	@echo "$(GREEN)Backend dependencies installed$(NC)"

install-frontend: ## Install frontend dependencies
	@echo "$(BLUE)Installing frontend dependencies...$(NC)"
	@cd $(FRONTEND_DIR) && npm install --legacy-peer-deps
	@echo "$(GREEN)Frontend dependencies installed$(NC)"

##@ Database

db-reset: ## Reset database (WARNING: deletes all data)
	@echo "$(RED)WARNING: This will delete all data!$(NC)"
	@read -p "Are you sure? [y/N] " -n 1 -r; \
	echo ""; \
	if [[ $$REPLY =~ ^[Yy] ]]; then \
		docker compose down -v; \
		docker compose up -d; \
		echo "$(GREEN)Database reset complete$(NC)"; \
	fi

db-migrate: ## Apply database migrations (Alembic)
	@echo "$(BLUE)Running migrations...$(NC)"
	@cd $(BACKEND_DIR) && source .venv/bin/activate && alembic upgrade head

##@ Testing & Quality

test: test-backend test-frontend ## Run backend and frontend unit tests

test-backend: ## Run backend unit tests (no Docker services needed)
	@echo "$(BLUE)Running backend tests...$(NC)"
	@cd $(BACKEND_DIR) && source .venv/bin/activate && pytest -m "not integration"

test-integration: ## Run backend integration tests (needs `make infra`)
	@cd $(BACKEND_DIR) && source .venv/bin/activate && pytest -m integration

eval-rag: ## Run DeepEval RAG benchmark. Usage: make eval-rag USER_ID=<uuid> DATASET=docs/examples/evaluation/golden_sample.json
	@echo "$(BLUE)Running DeepEval RAG benchmark...$(NC)"
	@cd $(BACKEND_DIR) && source .venv/bin/activate && python -m kira.evaluation.cli run --dataset $${DATASET:-../docs/examples/evaluation/golden_sample.json} --user-id $$USER_ID --output-dir ../reports/evaluation

eval-legal: ## Run the legal QA benchmark. Usage: make eval-legal DATASET=dataset/legal/golden.json
	@echo "$(BLUE)Running legal QA benchmark...$(NC)"
	@cd $(BACKEND_DIR) && source .venv/bin/activate && python scripts/validate_legal_eval_dataset.py $${DATASET:-../docs/examples/evaluation/legal_golden_example.json} && python -m kira.evaluation.cli run-legal --dataset $${DATASET:-../docs/examples/evaluation/legal_golden_example.json} --output-dir ../reports/evaluation

test-frontend: ## Run frontend tests
	@echo "$(BLUE)Running frontend tests...$(NC)"
	@cd $(FRONTEND_DIR) && npm test

lint: lint-backend lint-frontend ## Run all linters

lint-backend: ## Lint backend code
	@echo "$(BLUE)Linting backend...$(NC)"
	@cd $(BACKEND_DIR) && source .venv/bin/activate && ruff check kira tests

lint-frontend: ## Lint frontend code
	@echo "$(BLUE)Linting frontend...$(NC)"
	@cd $(FRONTEND_DIR) && npm run lint

format: format-backend format-frontend ## Format all code

format-backend: ## Format backend code
	@echo "$(BLUE)Formatting backend...$(NC)"
	@cd $(BACKEND_DIR) && source .venv/bin/activate && ruff format kira tests

format-frontend: ## Format frontend code
	@echo "$(BLUE)Formatting frontend...$(NC)"
	@cd $(FRONTEND_DIR) && npm run lint -- --fix

##@ Utils

clean: clean-backend clean-frontend ## Clean build artifacts

clean-backend: ## Clean backend artifacts
	@echo "$(BLUE)Cleaning backend...$(NC)"
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@find . -type f -name "*.pyo" -delete 2>/dev/null || true
	@find . -name ".DS_Store" -delete 2>/dev/null || true
	@rm -rf .pytest_cache .ruff_cache output/
	@echo "$(GREEN)Backend cleaned$(NC)"

clean-frontend: ## Clean frontend artifacts
	@echo "$(BLUE)Cleaning frontend...$(NC)"
	@cd $(FRONTEND_DIR) && rm -rf .next out
	@echo "$(GREEN)Frontend cleaned$(NC)"

charts: ## Generate RAG evaluation charts
	@echo "$(BLUE)Generating RAG evaluation charts...$(NC)"
	@cd $(BACKEND_DIR) && .venv/bin/python scripts/generate_rag_evaluation_charts.py
	@echo "$(GREEN)Charts generated in reports/evaluation/charts$(NC)"

logs: ## Show backend and infrastructure logs
	@echo "$(BLUE)Backend logs (Ctrl+C to exit):$(NC)"
	@docker compose logs -f

build: build-frontend ## Build production artifacts

build-frontend: ## Build frontend for production
	@echo "$(BLUE)Building frontend...$(NC)"
	@cd $(FRONTEND_DIR) && npm run build
	@echo "$(GREEN)Frontend built$(NC)"

##@ Quick Actions

up: infra dev ## Start everything (infra + backend + frontend)

down: infra-stop ## Stop everything

rebuild: infra-restart ## Restart infrastructure

setup: install infra ## Full setup (install + start infra)
	@echo "$(GREEN)Setup complete! Run 'make dev' to start development$(NC)"

# Check if tmux is installed for dev target
.PHONY: check-tmux
check-tmux:
	@command -v tmux >/dev/null 2>&1 || { echo "$(RED)tmux is required for 'make dev'. Install with: brew install tmux$(NC)"; exit 1; }
