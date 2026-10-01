.PHONY: setup setup-neural migrate seed dev api web test check build ai-eval neural-smoke mcp-smoke train-demo contracts
PY = .venv/bin/python
setup:
	uv sync --frozen --extra dev
	npm ci --prefix apps/web
setup-neural:
	uv sync --frozen --extra dev --extra neural
migrate:
	$(PY) -m alembic upgrade head
seed: migrate
	$(PY) -m services.api.seed
dev:
	$(PY) scripts/dev.py
api:
	$(PY) -m uvicorn services.api.main:app --host 127.0.0.1 --port 8000 --reload
web:
	npm run --prefix apps/web dev
check:
	.venv/bin/ruff check services ai ml tests scripts infra data/demo
	npm run --prefix apps/web typecheck
test:
	$(PY) -m pytest -q
build:
	npm run --prefix apps/web build
ai-eval:
	$(PY) -m ai.evaluate
neural-smoke:
	$(PY) -m ai.model_smoke --component all
mcp-smoke:
	$(PY) -m services.mcp.smoke
train-demo:
	$(PY) -m ml.train --synthetic --output .runtime/synthetic-training
contracts:
	$(PY) scripts/export_contracts.py
