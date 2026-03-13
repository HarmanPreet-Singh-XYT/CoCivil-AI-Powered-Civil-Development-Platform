.PHONY: infra-up infra-down infra-logs doctor migrate migrate-users migrate-all run-api run-frontend seed-toronto seed-policies audit-toronto test-backend test-frontend

DATA_DIR ?= data
FIXTURE ?= tests/fixtures/benchmarks/toronto_core.json

ifdef ADDRESS_FILE
ADDRESS_FILE_ARG := --address-file $(ADDRESS_FILE)
else
ADDRESS_FILE_ARG :=
endif

# ── Infrastructure ────────────────────────────────────────────────────────────

infra-up:
	docker compose up -d db redis minio

infra-down:
	docker compose down

infra-logs:
	docker compose logs -f db redis minio

doctor:
	python3 scripts/dev_doctor.py

# ── Migrations ────────────────────────────────────────────────────────────────
# Main app DB  → alembic.ini        (existing)
# Users/billing DB → alembic_users.ini  (new — separate physical DB)

migrate:
	python3 scripts/dev_doctor.py --services db
	alembic upgrade head

migrate-users:
	python3 scripts/dev_doctor.py --services db
	alembic -c alembic_users.ini upgrade head

migrate-all:
	python3 scripts/dev_doctor.py --services db
	alembic upgrade head
	alembic -c alembic_users.ini upgrade head

migrate-gen:
	@read -p "Migration message: " msg; \
	alembic revision --autogenerate -m "$$msg"

migrate-users-gen:
	@read -p "Migration message: " msg; \
	alembic -c alembic_users.ini revision --autogenerate -m "$$msg"

# ── App ───────────────────────────────────────────────────────────────────────

run-api:
	uvicorn app.main:app --reload

run-frontend:
	npm --prefix frontend-react run dev

# ── Seed / audit ─────────────────────────────────────────────────────────────

seed-toronto:
	python3 scripts/seed_toronto.py --data-dir $(DATA_DIR) $(ADDRESS_FILE_ARG)

seed-policies:
	python3 scripts/seed_policies.py

audit-toronto:
	python3 scripts/audit_toronto_seed.py --fixture $(FIXTURE)

# ── Tests ─────────────────────────────────────────────────────────────────────

test-backend:
	pytest tests -q -p no:rerunfailures

test-frontend:
	npm --prefix frontend-react test