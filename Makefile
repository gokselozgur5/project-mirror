SHELL := /bin/bash

UV ?= uv
VENV := .venv

.PHONY: bootstrap check test lint typecheck build firmware protocol-corpus dev run-gateway run-runtime run-perception run-web simulate phase1-soak privacy-check

bootstrap:
	$(UV) sync --locked --all-packages --all-extras
	npm ci

test:
	$(VENV)/bin/pytest -q services/embodiment
	$(VENV)/bin/pytest -q services/runtime
	$(VENV)/bin/pytest -q services/perception
	npm run test:web

lint:
	$(VENV)/bin/ruff check services/embodiment services/runtime services/perception scripts
	npm run lint

typecheck:
	$(VENV)/bin/mypy services/embodiment/src
	$(VENV)/bin/mypy services/runtime/src
	$(VENV)/bin/mypy services/perception/src
	npm run typecheck

build:
	npm run build

firmware:
	$(UV) run platformio test -d firmware/head-controller -e native
	$(UV) run platformio run -d firmware/head-controller

protocol-corpus:
	$(UV) run python scripts/generate-controller-corpus.py

dev:
	./scripts/run-dev-stack.sh

privacy-check:
	./scripts/check-repository.sh

check: privacy-check lint typecheck test build

run-gateway:
	$(VENV)/bin/uvicorn project_mirror_embodiment.app:app --reload --port 8080

run-runtime:
	MIRROR_GATEWAY_URL=http://127.0.0.1:8080 $(VENV)/bin/uvicorn project_mirror_runtime.app:app --reload --port 8081

run-perception:
	MIRROR_RUNTIME_URL=http://127.0.0.1:8081 $(VENV)/bin/uvicorn project_mirror_perception.app:app --reload --port 8082

run-web:
	npm run dev:web

simulate:
	$(VENV)/bin/python scripts/simulate-gaze.py

phase1-soak:
	./scripts/run-phase1-stack-soak.sh 300
