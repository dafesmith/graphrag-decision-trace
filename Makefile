.PHONY: setup install neo4j seed trace api ui clean down

PY ?= python3
VENV := .venv
ACT := . $(VENV)/bin/activate

setup: install neo4j ## Install deps and start Neo4j
	@echo ""
	@echo "Setup complete. Next:"
	@echo "  make seed           # load sample data"
	@echo "  make trace LOAN=LOAN-1042"
	@echo "  make api            # http://localhost:8000"

install: $(VENV)/.installed ## Install Python deps into a local venv

$(VENV)/.installed: requirements.txt
	$(PY) -m venv $(VENV)
	$(ACT) && pip install --upgrade pip
	$(ACT) && pip install -r requirements.txt
	@touch $(VENV)/.installed

neo4j: ## Start Neo4j via docker-compose (waits until ready)
	docker compose up -d neo4j
	@echo "Waiting for Neo4j to be ready..."
	@until docker inspect --format='{{.State.Health.Status}}' graphrag-neo4j 2>/dev/null | grep -q healthy; do \
		printf "."; sleep 2; \
	done
	@echo " ready."

seed: install ## Load sample loans and policies into the graph
	$(ACT) && $(PY) -m graphrag_trace.seed

trace: install ## Trace a single decision: make trace LOAN=LOAN-1042
	@if [ -z "$(LOAN)" ]; then echo "Usage: make trace LOAN=LOAN-1042"; exit 1; fi
	$(ACT) && $(PY) -m graphrag_trace.cli trace $(LOAN)

api: install ## Run the FastAPI server on http://localhost:8000
	$(ACT) && $(PY) -m uvicorn graphrag_trace.api:app --reload --host 0.0.0.0 --port 8000

test: install ## Run smoke tests (requires Neo4j running and seeded)
	$(ACT) && pytest -q

down: ## Stop Neo4j
	docker compose down

clean: down ## Remove venv and Neo4j data
	rm -rf $(VENV) neo4j-data __pycache__ .pytest_cache
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
