.PHONY: up local down test ingest

up:
	docker compose up --build

local:
	docker compose --profile local up --build

down:
	docker compose down

test:
	docker compose run --rm -e RUN_DATABASE_TESTS=1 api pytest

ingest:
	docker compose run --rm api python -m app.services.ingest --repo-url https://github.com/ChatPRD/lennys-podcast-transcripts.git
