.PHONY: dev migrate test lint load-fw load-competencies seed shell

dev:
	docker compose up -d db redis minio mailhog
	cd backend && python manage.py runserver &
	cd frontend && npm run dev

migrate:
	cd backend && python manage.py migrate

test:
	cd backend && pytest
	cd frontend && npm test -- --watchAll=false

lint:
	cd backend && ruff check . && ruff format --check .

load-fw:
	cd backend && python manage.py load_frameworks

load-competencies:
	cd backend && python manage.py load_competency_requirements

seed:
	cd backend && python manage.py seed_demo

shell:
	cd backend && python manage.py shell_plus

