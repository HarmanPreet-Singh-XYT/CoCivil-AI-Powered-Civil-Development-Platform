.PHONY: infra-up infra-down infra-logs doctor migrate run-api run-frontend seed-toronto seed-policies audit-toronto test-backend test-frontend

DATA_DIR ?= data
FIXTURE ?= tests/fixtures/benchmarks/toronto_core.json

ifdef ADDRESS_FILE
ADDRESS_FILE_ARG := --address-file $(ADDRESS_FILE)
else
ADDRESS_FILE_ARG :=
endif

infra-up:
	docker compose up -d db redis minio

infra-down:
	docker compose down

infra-logs:
	docker compose logs -f db redis minio

doctor:
	python3 scripts/dev_doctor.py

migrate:
	python3 scripts/dev_doctor.py --services db
	alembic upgrade head

run-api:
	uvicorn app.main:app --reload

run-frontend:
	npm --prefix frontend-react run dev

seed-toronto:
	python3 scripts/seed_toronto.py --data-dir $(DATA_DIR) $(ADDRESS_FILE_ARG)

seed-policies:
	python3 scripts/seed_policies.py

audit-toronto:
	python3 scripts/audit_toronto_seed.py --fixture $(FIXTURE)

test-backend:
	pytest tests -q -p no:rerunfailures

test-frontend:
	npm --prefix frontend-react test
