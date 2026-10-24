SHELL := /bin/bash

PYTHON ?= python3
VENV := .venv

.PHONY: bootstrap check test lint typecheck build run-gateway run-web simulate privacy-check

bootstrap:
	$(PYTHON) -m venv $(VENV)
	$(VENV)/bin/python -m pip install --upgrade pip
	$(VENV)/bin/python -m pip install -e 'services/embodiment[dev]'
	npm ci

test:
	$(VENV)/bin/pytest -q services/embodiment

lint:
	$(VENV)/bin/ruff check services/embodiment
	npm run lint

typecheck:
	$(VENV)/bin/mypy services/embodiment/src
	npm run typecheck

build:
	npm run build

privacy-check:
	./scripts/check-repository.sh

check: privacy-check lint typecheck test build

run-gateway:
	$(VENV)/bin/uvicorn project_mirror_embodiment.app:app --reload --port 8080

run-web:
	npm run dev:web

simulate:
	$(VENV)/bin/python scripts/simulate-gaze.py
