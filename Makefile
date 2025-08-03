.PHONY: help serve build clean create-issue start-project add-photos finish-project setup-imgur test test-coverage install-test-deps lint lint-fix check

IMAGE_NAME = nordhus-site-jekyll

# Default target
help:
	@echo "Available commands:"
	@echo "  make build              - Build Docker image and Jekyll site"
	@echo "  make clean              - Clean build artifacts and Docker resources"
	@echo "  make create-issue       - Create GitHub issue with pre-filled template"
	@echo "  make serve              - Serve site locally using docker-compose"
	@echo "  make start-project      - Start new construction project (usage: PROJECT=name make start-project)"
	@echo "  make add-photos         - Add photos to existing project (usage: PROJECT=name make add-photos)"
	@echo "  make finish-project     - Generate blog post and create PR (usage: PROJECT=name make finish-project)"
	@echo "  make setup-imgur         - Setup Imgur API integration"
	@echo "  make test               - Run unit tests for photo management system"
	@echo "  make test-coverage      - Run tests with coverage report"
	@echo "  make lint               - Run Python linter (ruff) to check code quality"
	@echo "  make lint-fix           - Run Python linter with auto-fix"
	@echo "  make check              - Run all quality checks (lint + tests)"

# Serve using docker-compose (recommended for development)
serve: lint
	@echo "Starting Jekyll server with Docker Compose..."
	@echo "Opening browser..."
	@(sleep 5 && (xdg-open http://localhost:4000 2>/dev/null || open http://localhost:4000 2>/dev/null || echo "Please open http://localhost:4000 in your browser")) &
	@echo "Press Ctrl+C to stop the server"
	docker compose up --build

# Build Docker image and Jekyll site
build:
	@echo "Building custom Jekyll image with dependencies..."
	docker build -t $(IMAGE_NAME) .
	@echo "Building Jekyll site..."
	docker run --rm -v "$(PWD)":/srv/jekyll:cached \
		-v /srv/jekyll/vendor \
		-v /srv/jekyll/.bundle \
		$(IMAGE_NAME) \
		jekyll build

# Clean build artifacts and Docker resources
clean:
	@echo "Cleaning build artifacts..."
	rm -rf _site .jekyll-cache .jekyll-metadata
	@echo "Cleaning Docker resources..."
	docker compose down --volumes --remove-orphans 2>/dev/null || true
	docker rmi $(IMAGE_NAME) 2>/dev/null || true
	docker system prune -f

# Create GitHub issue (opens browser with pre-filled content if provided)
# Usage: TITLE="Issue Title" BODY="Issue description" make create-issue
create-issue:
	@echo "Opening GitHub issue page..."
	@python3 -c "import urllib.parse, os, webbrowser; title = os.environ.get('TITLE', ''); body = os.environ.get('BODY', ''); url = 'https://github.com/jayljohnson/nordhus.site/issues/new'; url = url + '?title=' + urllib.parse.quote(title) + '&body=' + urllib.parse.quote(body) if (title or body) else url; webbrowser.open(url)"


# Construction project workflow
start-project:
	@if [ -z "$(PROJECT)" ]; then \
		echo "Error: PROJECT variable required. Usage: PROJECT=window-repair make start-project"; \
		exit 1; \
	fi
	@echo "Starting construction project: $(PROJECT)"
	@python3 scripts/project/project_manager.py start $(PROJECT)

add-photos:
	@if [ -z "$(PROJECT)" ]; then \
		echo "Error: PROJECT variable required. Usage: PROJECT=window-repair make add-photos"; \
		exit 1; \
	fi
	@echo "Adding photos to project: $(PROJECT)"
	@python3 scripts/project/project_manager.py add-photos $(PROJECT)

finish-project:
	@if [ -z "$(PROJECT)" ]; then \
		echo "Error: PROJECT variable required. Usage: PROJECT=window-repair make finish-project"; \
		exit 1; \
	fi
	@echo "Finishing project: $(PROJECT)"
	@echo "Generating blog post with Claude analysis..."
	@python3 scripts/project/project_manager.py finish $(PROJECT)

setup-imgur:
	@echo "Setting up Imgur API integration..."
	@python3 scripts/clients/imgur_client.py setup

# Testing commands
test: lint
	@echo "Running unit tests for photo management system..."
	@python3 -m pytest tests/ -v
	@echo "Cleaning up test artifacts..."
	@rm -rf ./assets/images/*test-project* ./_posts/*test-project* 2>/dev/null || true

test-coverage: lint
	@echo "Running tests with coverage report..."
	@python3 -m pytest tests/ --cov=scripts --cov-report=html --cov-report=term -v
	@echo "Cleaning up test artifacts..."
	@rm -rf ./assets/images/*test-project* ./_posts/*test-project* 2>/dev/null || true
	@echo "Coverage report generated in htmlcov/index.html"

# Install test dependencies
install-test-deps:
	@echo "Installing test dependencies..."
	@pip3 install pytest pytest-cov requests ruff

# Python code quality
lint:
	@echo "Running Python linter (ruff)..."
	@ruff check scripts/ tests/ --diff
	@ruff format scripts/ tests/ --diff --check

lint-fix:
	@echo "Running Python linter with auto-fix..."
	@ruff check scripts/ tests/ --fix
	@ruff format scripts/ tests/

check: lint test
	@echo "All quality checks passed!"


