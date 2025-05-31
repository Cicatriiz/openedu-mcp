.PHONY: help install install-dev test lint format clean run docker-build docker-run validate validate-quick validate-arxiv validate-wikipedia validate-dictionary validate-openlibrary

help:
	@echo "Available commands:"
	@echo "  install           Install production dependencies"
	@echo "  install-dev       Install development dependencies"
	@echo "  test              Run unit tests"
	@echo "  validate          Run comprehensive real-world API validation tests"
	@echo "  validate-quick    Run quick API health checks"
	@echo "  validate-arxiv    Run ArXiv API validation tests"
	@echo "  validate-wikipedia Run Wikipedia API validation tests"
	@echo "  validate-dictionary Run Dictionary API validation tests"
	@echo "  validate-openlibrary Run OpenLibrary API validation tests"
	@echo "  lint              Run linting"
	@echo "  format            Format code"
	@echo "  clean             Clean up generated files"
	@echo "  run               Run the server"
	@echo "  docker-build      Build Docker image"
	@echo "  docker-run        Run with Docker Compose"

install:
	pip install -r requirements.txt

install-dev:
	pip install -r requirements.txt -r requirements-dev.txt
	pre-commit install

test:
	pytest

lint:
	flake8 src tests
	mypy src
	bandit -r src

format:
	black src tests
	isort src tests

clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	rm -rf .pytest_cache
	rm -rf htmlcov
	rm -rf dist
	rm -rf build

run:
	python -m src.main

docker-build:
	docker build -t openedu-mcp-server .

docker-run:
	docker-compose up -d
# Real-world API validation tests
validate:
	@echo "🚀 Running comprehensive real-world API validation tests..."
	python run_validation_tests.py --verbose

validate-quick:
	@echo "⚡ Running quick API health checks..."
	python run_validation_tests.py --quick --verbose

validate-arxiv:
	@echo "📚 Running ArXiv API validation tests..."
	python run_validation_tests.py --api arxiv --verbose

validate-wikipedia:
	@echo "📖 Running Wikipedia API validation tests..."
	python run_validation_tests.py --api wikipedia --verbose

validate-dictionary:
	@echo "📝 Running Dictionary API validation tests..."
	python run_validation_tests.py --api dictionary --verbose

validate-openlibrary:
	@echo "📚 Running OpenLibrary API validation tests..."
	python run_validation_tests.py --api openlibrary --verbose

validate-report:
	@echo "📊 Running validation tests with detailed reporting..."
	python run_validation_tests.py --verbose --output validation_report_$(shell date +%Y%m%d_%H%M%S).json
	@echo "📄 Report saved with timestamp"

validate-ci:
	@echo "🔄 Running validation tests for CI/CD..."
	python run_validation_tests.py --quick