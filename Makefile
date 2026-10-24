SHELL := /bin/bash

PYTHON ?= python3
VENV := .venv

.PHONY: bootstrap check test lint typecheck build firmware run-gateway run-web simulate phase1-soak privacy-check

bootstrap:
	$(PYTHON) -m venv $(VENV)
	$(VENV)/bin/python -m pip install --upgrade pip
	$(VENV)/bin/python -m pip install -e 'services/embodiment[dev]'
	$(VENV)/bin/python -m pip install -e 'services/runtime[dev]'
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
	pio run -d firmware/head-controller

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
