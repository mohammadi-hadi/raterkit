PY ?= .venv/bin/python

.PHONY: demo test lint typecheck goemotions build clean

demo:
	$(PY) -m raterkit.cli demo --out results
	$(PY) -m raterkit.cli inject-readme README.md --results results

test:
	$(PY) -m pytest -q

lint:
	$(PY) -m ruff check src tests
	$(PY) -m ruff format --check src tests

typecheck:
	$(PY) -m mypy src

goemotions:
	$(PY) examples/goemotions/fetch_data.py
	$(PY) examples/goemotions/audit_goemotions.py

build:
	$(PY) -m build

clean:
	rm -rf dist build .pytest_cache .mypy_cache .ruff_cache
