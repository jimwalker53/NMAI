.PHONY: up down logs api ui worker db collector migrate migration test shell psql clean restart

up:
	docker compose up -d --build

down:
	docker compose down

logs:
	docker compose logs -f

api:
	docker compose up -d --build api

ui:
	docker compose up -d --build ui

worker:
	docker compose up -d --build worker

db:
	docker compose up -d db

collector:
	docker compose up -d --build collector

migrate:
	docker compose exec api alembic upgrade head

migration:
	docker compose exec api alembic revision --autogenerate -m "$(msg)"

test:
	docker compose exec api pytest tests/ -v

shell:
	docker compose exec api bash

psql:
	docker compose exec db psql -U nmia

clean:
	docker compose down -v --remove-orphans

restart:
	make down && make up
