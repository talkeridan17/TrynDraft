.PHONY: help install test run clean

help:
	@echo "TrynDraft Commands:"
	@echo "  install    Install dependencies"
	@echo "  test       Run tests"
	@echo "  run        Start development server"
	@echo "  clean      Clean cache files"

install:
	pip install -r requirements.txt

test:
	pytest tests/ -v

run:
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	rm -rf .coverage htmlcov/