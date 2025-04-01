.PHONY: clean install dev-install lint format test coverage docs serve-docs build dist help

# Variables
PYTHON := python
PIP := pip
PYTEST := pytest
COVERAGE := coverage
BLACK := black
ISORT := isort
FLAKE8 := flake8
MYPY := mypy
MKDOCS := mkdocs

help:
	@echo "Available commands:"
	@echo "  clean        - Remove build artifacts and cache files"
	@echo "  install      - Install production dependencies"
	@echo "  dev-install  - Install development dependencies"
	@echo "  lint         - Run linting checks"
	@echo "  format       - Format code with black and isort"
	@echo "  test         - Run tests"
	@echo "  coverage     - Run tests with coverage report"
	@echo "  docs         - Build documentation"
	@echo "  serve-docs   - Serve documentation locally"
	@echo "  build        - Build package"
	@echo "  dist         - Create distribution files"

clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .pytest_cache/
	rm -rf .coverage
	rm -rf htmlcov/
	rm -rf .mypy_cache/
	rm -rf site/
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

install:
	$(PIP) install -r requirements.txt

dev-install:
	$(PIP) install -r requirements.txt
	$(PIP) install -e ".[dev]"

lint:
	$(FLAKE8) app tests
	$(MYPY) app tests

format:
	$(BLACK) app tests
	$(ISORT) app tests

test:
	$(PYTEST)

coverage:
	$(PYTEST) --cov=app --cov-report=html
	@echo "Open htmlcov/index.html in your browser to view the coverage report"

docs:
	$(MKDOCS) build

serve-docs:
	$(MKDOCS) serve

build:
	$(PYTHON) setup.py build

dist:
	$(PYTHON) setup.py sdist bdist_wheel

# Default target
.DEFAULT_GOAL := help 