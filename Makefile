.PHONY: setup dev-backend dev-frontend dev test

setup:
	cd backend && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt

dev-backend:
	cd backend && .venv/bin/uvicorn app.main:app --reload --port 8000

dev-frontend:
	cd frontend && npm run dev

dev:
	$(MAKE) dev-backend & $(MAKE) dev-frontend

test:
	cd backend && .venv/bin/pytest -v
