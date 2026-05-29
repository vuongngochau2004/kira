# K.I.R.A Simplified - Makefile
.PHONY: help dev backend frontend infra infra-stop infra-restart test install clean lint

# Default target
.DEFAULT_GOAL := help

# Colors for output
BLUE  := \033[0;34m
GREEN := \033[0;32m
RED   := \033[0;31m
NC    := \033[0m

# Project paths
BACKEND_DIR := .
FRONTEND_DIR := frontend

# Ports
BACKEND_PORT := 8006
FRONTEND_PORT := 3001

##@ General

help: ## Show this help message
	@echo "$(BLUE)K.I.R.A Simplified - Available commands:$(NC)"
	@echo ""
	@grep -E '^##@|^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-15s$(NC) %s\n", $$1, $$2}' | sed 's/^##@//'
	@echo ""

##@ Development

dev: ## Start both backend and frontend (requires tmux)
	@echo "$(BLUE)Starting K.I.R.A Simplified...$(NC)"
	@tmux new-session -d -s kira -n backend "cd $(BACKEND_DIR) && source .venv/bin/activate && python -m src.main"
	@tmux new-window -t kira:1 -n frontend "cd $(FRONTEND_DIR) && npm run dev"
	@tmux attach-session -t kira
	@echo "$(GREEN)Both services started in tmux session 'kira'$(NC)"

dev-backend: ## Start backend only
	@echo "$(BLUE)Starting backend on port $(BACKEND_PORT)...$(NC)"
	@cd $(BACKEND_DIR) && source .venv/bin/activate && python -m src.main

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

##@ Installation

install: install-backend install-frontend ## Install both backend and frontend dependencies

install-backend: ## Install backend dependencies
	@echo "$(BLUE)Installing backend dependencies...$(NC)"
	@cd $(BACKEND_DIR) && pip install -e .
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

db-migrate: ## Run database migrations
	@echo "$(BLUE)Running migrations...$(NC)"
	@cd $(BACKEND_DIR) && source .venv/bin/activate && python -m scripts.migrate

##@ Testing & Quality

test: ## Run all tests
	@echo "$(BLUE)Running tests...$(NC)"
	@cd $(BACKEND_DIR) && source .venv/bin/activate && pytest tests/ -v

test-backend: ## Run backend tests
	@echo "$(BLUE)Running backend tests...$(NC)"
	@cd $(BACKEND_DIR) && source .venv/bin/activate && pytest tests/ -v

test-frontend: ## Run frontend tests
	@echo "$(BLUE)Running frontend tests...$(NC)"
	@cd $(FRONTEND_DIR) && npm test

lint: lint-backend lint-frontend ## Run all linters

lint-backend: ## Lint backend code
	@echo "$(BLUE)Linting backend...$(NC)"
	@cd $(BACKEND_DIR) && source .venv/bin/activate && ruff check src/ tests/

lint-frontend: ## Lint frontend code
	@echo "$(BLUE)Linting frontend...$(NC)"
	@cd $(FRONTEND_DIR) && npm run lint

format: format-backend format-frontend ## Format all code

format-backend: ## Format backend code
	@echo "$(BLUE)Formatting backend...$(NC)"
	@cd $(BACKEND_DIR) && source .venv/bin/activate && ruff format src/ tests/

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
	@rm -rf .pytest_cache .ruff_cache
	@echo "$(GREEN)Backend cleaned$(NC)"

clean-frontend: ## Clean frontend artifacts
	@echo "$(BLUE)Cleaning frontend...$(NC)"
	@cd $(FRONTEND_DIR) && rm -rf .next out
	@echo "$(GREEN)Frontend cleaned$(NC)"

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
