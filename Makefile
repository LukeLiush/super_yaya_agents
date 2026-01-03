.PHONY: lint format check clean install

install:
	uv sync

lint:
	uv run ruff check .

format:
	uv run ruff format .
	uv run ruff check --fix .

check:
	uv run mypy .

all: format lint check
