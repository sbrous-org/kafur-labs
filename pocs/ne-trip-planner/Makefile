.PHONY: up up-ollama dev test db-test
up:            ## offline demo: mock LLM, hash embeddings (no keys, no model download)
	docker compose up --build
up-ollama:     ## self-hosted small model via the stock ollama image
	LLM_PROVIDER=openai docker compose --profile ollama up --build
dev:           ## run app locally against a Postgres+pgvector at $$DATABASE_URL
	cd backend && uvicorn app.main:app --reload --port 8000
test:          ## needs Postgres+pgvector at $$DATABASE_URL (default 127.0.0.1:5433); DB tests skip if absent
	cd backend && python -m pytest -q tests
db-test:       ## throwaway pgvector container for tests
	docker run --rm -d --name netrip-testdb -e POSTGRES_HOST_AUTH_METHOD=trust -e POSTGRES_DB=netrip -p 5433:5432 pgvector/pgvector:pg16
