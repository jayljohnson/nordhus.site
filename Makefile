.PHONY: help serve build clean create-issue start-project add-photos finish-project setup-cloudinary test test-coverage install-test-deps lint lint-fix check container-start container-stop container-exec

IMAGE_NAME = nordhus-site-jekyll
CONTAINER_NAME = nordhus-dev-container

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
	@echo "  make setup-cloudinary    - Setup Cloudinary API integration"
	@echo "  make test               - Run unit tests for photo management system"
	@echo "  make test-coverage      - Run tests with coverage report"
	@echo "  make lint               - Run ruff linter to check code quality"
	@echo "  make lint-fix           - Format and fix code with ruff"
	@echo "  make check              - Run all quality checks (lint + test coverage)"
	@echo "  make container-start    - Start persistent development container"
	@echo "  make container-stop     - Stop persistent development container"
	@echo "  make container-exec     - Execute command in running container (CMD=command)"

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
		bundle exec jekyll build

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
	@docker run --rm -v "$(PWD)":/srv/jekyll:cached \
		-e TITLE -e BODY \
		-w /srv/jekyll \
		$(IMAGE_NAME) \
		python3 -c "import urllib.parse, os, webbrowser; title = os.environ.get('TITLE', ''); body = os.environ.get('BODY', ''); url = 'https://github.com/jayljohnson/nordhus.site/issues/new'; url = url + '?title=' + urllib.parse.quote(title) + '&body=' + urllib.parse.quote(body) if (title or body) else url; webbrowser.open(url)"


# Project variable validation helper
check-project-var:
	@if [ -z "$(PROJECT)" ]; then \
		echo "Error: PROJECT variable required. Usage: PROJECT=project-name make [command]"; \
		exit 1; \
	fi

# Unified Docker execution helper
docker-exec:
	@if [ -z "$(CMD)" ]; then \
		echo "Error: CMD variable required. Usage: CMD='command' make docker-exec"; \
		exit 1; \
	fi
	$(call run_in_container,$(CMD))

# Construction project workflow (consolidated)
start-project: check-project-var
	@echo "Starting construction project: $(PROJECT)"
	@make docker-exec CMD="python3 scripts/cli.py project start $(PROJECT)"

add-photos: check-project-var
	@echo "Adding photos to project: $(PROJECT)"
	@make docker-exec CMD="python3 scripts/cli.py project add-photos $(PROJECT)"

finish-project: check-project-var
	@echo "Finishing project: $(PROJECT)"
	@echo "Generating blog post with Claude analysis..."
	@make docker-exec CMD="python3 scripts/cli.py project finish $(PROJECT)"

setup-cloudinary:
	@echo "Setting up Cloudinary API integration..."
	@make docker-exec CMD="python3 scripts/cli.py cloudinary test"

# Testing commands
test: lint-fix
	@echo "Running unit tests via CLI..."
	$(call run_in_container,python3 scripts/cli.py dev test)
	@echo "Cleaning up test artifacts..."
	@rm -rf ./assets/images/*test-project* ./_posts/*test-project* 2>/dev/null || true

test-coverage:
	@echo "Running tests with coverage..."
	$(call run_in_container,python3 scripts/cli.py dev test --coverage)
	@rm -rf ./assets/images/*test-project* ./_posts/*test-project* 2>/dev/null || true

# Install test dependencies (now handled in Docker container)
install-test-deps:
	@echo "Test dependencies are now installed in the Docker container"
	@echo "Run 'make build' to rebuild the container with latest dependencies"

# Python code quality
lint:
	@echo "Checking code format and style..."
	$(call run_in_container,ruff format --check scripts/ tests/)
	$(call run_in_container,ruff check scripts/ tests/)

lint-fix:
	@echo "Formatting and fixing code..."
	$(call run_in_container,ruff format --quiet scripts/ tests/)
	$(call run_in_container,ruff check --fix scripts/ tests/)

check: lint-fix test-coverage
	@echo "All quality checks passed!"


# Container management for faster command execution
container-start:
	@echo "Starting persistent development container..."
	@docker run -d --name $(CONTAINER_NAME) \
		-v "$(PWD)":/srv/jekyll:cached \
		-v /srv/jekyll/vendor \
		-v /srv/jekyll/.bundle \
		-w /srv/jekyll \
		$(IMAGE_NAME) \
		tail -f /dev/null
	@echo "Container $(CONTAINER_NAME) is running. Use 'make container-exec CMD=command' to run commands."

container-stop:
	@echo "Stopping persistent development container..."
	@docker stop $(CONTAINER_NAME) 2>/dev/null || true
	@docker rm $(CONTAINER_NAME) 2>/dev/null || true
	@echo "Container $(CONTAINER_NAME) stopped and removed."

container-exec:
	@if [ -z "$(CMD)" ]; then \
		echo "Error: CMD variable required. Usage: CMD='python3 --version' make container-exec"; \
		exit 1; \
	fi
	@docker exec $(CONTAINER_NAME) $(CMD)

# Helper function to run commands in container (hot or cold)
define run_in_container
	@if docker ps --format "table {{.Names}}" | grep -q "^$(CONTAINER_NAME)$$"; then \
		docker exec $(CONTAINER_NAME) $(1); \
	else \
		docker run --rm -v "$(PWD)":/srv/jekyll:cached \
			-v /srv/jekyll/vendor \
			-v /srv/jekyll/.bundle \
			-w /srv/jekyll \
			$(IMAGE_NAME) \
			$(1); \
	fi
endef


