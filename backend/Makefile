# TrynDraft Backend Makefile
# Cross-platform compatible for macOS, Linux, and Windows
.PHONY: install run test migrate seed clean setup db-create help

# Default target
.DEFAULT_GOAL := help

help: ## Show this help message
	@echo "TrynDraft Backend - Available Commands:"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

install: ## Install Python dependencies
	pip install -r requirements.txt

run: ## Start development server with hot reload
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

test: ## Run test suite
	pytest tests/ -v --cov=app --cov-report=term-missing

migrate: ## Run database migrations
	alembic upgrade head

migrate-create: ## Create a new migration (use: make migrate-create MSG="description")
	alembic revision --autogenerate -m "$(MSG)"

seed: ## Seed database with champion data from Data Dragon API
	python scripts/seed_champions.py

db-create: ## Create database tables (for fresh setup)
	python scripts/create_tables.py

clean: ## Clean Python cache files
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name ".coverage" -delete
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true

clean-db: ## Remove SQLite database (WARNING: deletes local data)
	rm -f tryndraft.db
	@echo "Database removed. Run 'make migrate' to recreate."

reset-db: ## Reset database and migration state (fresh start)
	@echo "Resetting database..."
	rm -f tryndraft.db
	rm -f alembic/versions/*.py
	git checkout alembic/versions/__init__.py 2>/dev/null || touch alembic/versions/__init__.py
	@echo "Database and migrations reset. Run 'make migrate' to recreate."

setup: ## Initial setup - create venv and install dependencies
	@echo "Setting up development environment..."
	python3 -m venv .venv || python -m venv .venv
	@echo ""
	@echo "Virtual environment created!"
	@echo "Activate it with:"
	@echo "  - macOS/Linux: source .venv/bin/activate"
	@echo "  - Windows:     .venv\\Scripts\\activate"
	@echo ""
	@echo "Then run: make install"

dev: ## Full development setup (venv + install + migrate + seed)
	@echo "Running full development setup..."
	$(MAKE) setup
	@echo "\nInstalling dependencies..."
	. .venv/bin/activate && pip install -r requirements.txt || .venv\\Scripts\\activate && pip install -r requirements.txt
	@echo "\nRunning migrations..."
	. .venv/bin/activate && alembic upgrade head || .venv\\Scripts\\activate && alembic upgrade head
	@echo "\nSeeding champion data..."
	. .venv/bin/activate && python scripts/seed_champions.py || .venv\\Scripts\\activate && python scripts/seed_champions.py
	@echo "\n✅ Development environment ready!"
	@echo "Run 'make run' to start the server"

format: ## Format code with black
	black app/ tests/ scripts/

lint: ## Lint code with ruff
	ruff check app/ tests/ scripts/

scrape-stats: ## Run Riot API scraper to collect champion statistics
	python scripts/scrape_champion_stats.py

scrape-training: ## Scrape training data from MOBAFire/LoLalytics for LLM fine-tuning
	python scripts/scrape_training_data.py

scrape-training-test: ## Test scraping with only 5 champions
	python scripts/scrape_training_data.py --test