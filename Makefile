.PHONY: help setup test lint fmt smoke calibrate data-check clean

help:
	@echo "make setup      install the package in editable mode with dev extras"
	@echo "make test       run the test suite"
	@echo "make lint       run ruff"
	@echo "make smoke      offline integrity check (no Docker, no API key)"
	@echo "make calibrate  check a local environment against the reference anchor"
	@echo "make data-check verify data/calibration_set.json still matches its rule"

setup:
	python -m pip install -e ".[dev]"

setup-run:
	python -m pip install -e ".[run,dev]"
	python -m playwright install chromium

test:
	python -m pytest -q

lint:
	python -m ruff check src tests scripts

fmt:
	python -m ruff check --fix src tests scripts

smoke:
	python scripts/smoke_test.py

calibrate:
	skillshift calibrate

data-check:
	python scripts/build_calibration_set.py --check

clean:
	rm -rf .pytest_cache .ruff_cache **/__pycache__ build dist *.egg-info
