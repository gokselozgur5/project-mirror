SHELL := /bin/bash

UV ?= uv
VENV := .venv

.PHONY: bootstrap check test lint typecheck build firmware protocol-corpus run-gateway run-web simulate phase1-soak privacy-check

bootstrap:
	$(UV) sync --locked --all-packages --all-extras
	npm ci

test:
	$(VENV)/bin/pytest -q services/embodiment
	$(VENV)/bin/pytest -q services/runtime

lint:
	$(VENV)/bin/ruff check services/embodiment services/runtime scripts
	npm run lint

typecheck:
	$(VENV)/bin/mypy services/embodiment/src
	$(VENV)/bin/mypy services/runtime/src
	npm run typecheck

build:
	npm run build

firmware:
	$(UV) run platformio test -d firmware/head-controller -e native
	$(UV) run platformio run -d firmware/head-controller

protocol-corpus:
	$(UV) run python scripts/generate-controller-corpus.py

privacy-check:
	./scripts/check-repository.sh

check: privacy-check lint typecheck test build

run-gateway:
	$(VENV)/bin/uvicorn project_mirror_embodiment.app:app --reload --port 8080

run-web:
	npm run dev:web

simulate:
	$(VENV)/bin/python scripts/simulate-gaze.py

phase1-soak:
	./scripts/run-phase1-stack-soak.sh 300
