.PHONY: help install test run docker-build docker-run docker-stop clean

help:
	@echo "Available commands:"
	@echo "  make install       - Install dependencies"
	@echo "  make test          - Run tests"
	@echo "  make test-cov      - Run tests with coverage"
	@echo "  make run           - Run development server"
	@echo "  make docker-build  - Build Docker image"
	@echo "  make docker-run    - Run with Docker Compose"
	@echo "  make docker-stop   - Stop Docker containers"
	@echo "  make clean         - Clean up temporary files"
	@echo "  make lint          - Run code linting"

install:
	pip install -r requirements.txt

test:
	pytest -v

test-cov:
	pytest --cov=app --cov-report=html --cov-report=term

run:
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

docker-build:
	docker build -t hospital-bulk-api .

docker-run:
	docker-compose up -d

docker-stop:
	docker-compose down

docker-logs:
	docker-compose logs -f

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.log" -delete
	rm -rf .pytest_cache
	rm -rf htmlcov
	rm -rf .coverage
	rm -rf build
	rm -rf dist
	rm -rf *.egg-info

lint:
	@echo "Running flake8..."
	@flake8 app/ tests/ --max-line-length=120 --ignore=E501 || true
	@echo "Running black check..."
	@black --check app/ tests/ || true

format:
	black app/ tests/

dev-setup: install
	@echo "Development environment ready!"
	@echo "Run 'make run' to start the server"