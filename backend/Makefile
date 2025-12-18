# Makefile
.PHONY: install run test migrate seed

install:
	pip install -r requirements.txt

run:
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

test:
	pytest tests/ -v

migrate:
	alembic upgrade head

seed:
	python scripts/seed_champions.py

clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete

setup:
	python -m venv .venv
	.venv\Scripts\activate && pip install -r requirements.txt
	python -c "from app.database import engine; from app.models import Base; Base.metadata.create_all(bind=engine)"