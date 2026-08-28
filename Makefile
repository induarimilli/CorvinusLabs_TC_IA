.PHONY: up down migrate seed demo-reset logs dev-api dev-web dev-local install

up:
	docker compose up -d --build
	@echo "Waiting for services..."
	@sleep 8
	docker compose exec api alembic upgrade head
	docker compose exec api python scripts/seed.py
	@echo ""
	@echo "Portal ready:"
	@echo "  App:     http://localhost:5173"
	@echo "  API:     http://localhost:8000/docs"
	@echo "  Adminer: http://localhost:8080 (System: PostgreSQL, Server: postgres, User: corvinus, Password: corvinus, Database: corvinus)"

install:
	cd backend && pip3 install -e .
	cd frontend && npm install

dev-local:
	@echo "Starting local dev (no Docker). Run each in a separate terminal:"
	@echo "  Terminal 1: make dev-api"
	@echo "  Terminal 2: make dev-web"
	@echo ""
	@echo "Prerequisites: Postgres running, 'make install' already done."

dev-api:
	cd backend && uvicorn app.main:app --reload --port 8000

dev-web:
	cd frontend && npm run dev

setup-db:
	psql -h localhost -d postgres -c "CREATE USER corvinus WITH PASSWORD 'corvinus' CREATEDB;" 2>/dev/null || true
	psql -h localhost -d postgres -c "CREATE DATABASE corvinus OWNER corvinus;" 2>/dev/null || true
	cd backend && alembic upgrade head && python3 scripts/seed.py

down:
	docker compose down

migrate:
	docker compose exec api alembic upgrade head

seed:
	@if command -v docker >/dev/null 2>&1 && docker compose ps -q api 2>/dev/null | grep -q .; then \
		docker compose exec api python scripts/seed.py; \
	else \
		cd backend && python3 scripts/seed.py; \
	fi

demo-reset:
	@if command -v docker >/dev/null 2>&1 && docker compose ps -q postgres 2>/dev/null | grep -q .; then \
		docker compose exec postgres psql -U corvinus -d corvinus -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"; \
		docker compose exec api alembic upgrade head; \
		docker compose exec api python scripts/seed.py; \
	else \
		psql -h localhost -d corvinus -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public; GRANT ALL ON SCHEMA public TO corvinus; GRANT ALL ON SCHEMA public TO public;"; \
		cd backend && alembic upgrade head && python3 scripts/seed.py; \
	fi

logs:
	docker compose logs -f
