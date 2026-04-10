.PHONY: dev migrate test lint load-fw load-competencies seed shell \
        prod-build prod-up prod-down prod-migrate prod-seed \
        prod-logs prod-shell prod-check

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

# ── Produzione ──────────────────────────────────────────────────────────────
prod-build:
	docker compose -f docker-compose.prod.yml build

prod-up:
	docker compose -f docker-compose.prod.yml up -d

prod-down:
	docker compose -f docker-compose.prod.yml down

prod-migrate:
	docker compose -f docker-compose.prod.yml exec backend \
	  python manage.py migrate

prod-seed:
	docker compose -f docker-compose.prod.yml exec backend \
	  python manage.py load_frameworks
	docker compose -f docker-compose.prod.yml exec backend \
	  python manage.py load_notification_profiles
	docker compose -f docker-compose.prod.yml exec backend \
	  python manage.py load_competency_requirements
	docker compose -f docker-compose.prod.yml exec backend \
	  python manage.py load_required_documents

prod-logs:
	docker compose -f docker-compose.prod.yml logs -f --tail=50

prod-shell:
	docker compose -f docker-compose.prod.yml exec backend \
	  python manage.py shell

prod-check:
	docker compose -f docker-compose.prod.yml exec backend \
	  python manage.py check --deploy

