.DEFAULT_GOAL := help

export UV_CACHE_DIR := $(CURDIR)/.uv-cache

.PHONY: help setup test lint typecheck check format build-data validate-data clean

help:
	@echo "setup          Install Python 3.11 dependencies from the lockfile"
	@echo "test           Run the offline automated test suite"
	@echo "lint           Check lint and formatting"
	@echo "typecheck      Run static type checks"
	@echo "check          Run every CI check"
	@echo "format         Apply automatic formatting"
	@echo "build-data      Rebuild and validate the reference SQLite database"
	@echo "validate-data   Validate the existing reference SQLite database"

setup:
	uv sync --all-groups

test:
	uv run pytest -m "not live"

lint:
	uv run ruff check .
	uv run ruff format --check .

typecheck:
	uv run mypy

check: lint typecheck test

format:
	uv run ruff format .
	uv run ruff check --fix .

build-data:
	uv run python -m eval_those_models dataset build

validate-data:
	uv run python -m eval_those_models dataset validate

clean:
	uv run python -c "from pathlib import Path; import shutil; [shutil.rmtree(path, ignore_errors=True) for path in ('.mypy_cache', '.pytest_cache', '.ruff_cache')]; Path('.coverage').unlink(missing_ok=True)"
