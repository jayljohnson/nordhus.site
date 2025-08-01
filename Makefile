.PHONY: help serve build clean create-issue generate-pr-content create-pr

IMAGE_NAME = nordhus-site-jekyll

# Default target
help:
	@echo "Available commands:"
	@echo "  make build              - Build Docker image and Jekyll site"
	@echo "  make clean              - Clean build artifacts and Docker resources"
	@echo "  make create-issue       - Create GitHub issue with pre-filled template"
	@echo "  make generate-pr-content - Generate PR content in .tmp/pr-content.txt"
	@echo "  make create-pr          - Create GitHub PR using existing pr-content.txt"
	@echo "  make serve              - Serve site locally using docker-compose"

# Serve using docker-compose (recommended for development)
serve:
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

# Generate PR content only
# Usage: make generate-pr-content
generate-pr-content:
	@echo "Checking for uncommitted changes..."
	@if [ -n "$$(git status --porcelain)" ]; then \
		echo "Error: You have uncommitted changes. Please commit them first:"; \
		echo ""; \
		git status --short; \
		echo ""; \
		echo "Run: git add . && git commit -m 'Your commit message'"; \
		exit 1; \
	fi
	@echo "Generating PR content..."
	@if [ ! -d .tmp ]; then mkdir .tmp; fi
	@rm -f .tmp/*
	@BRANCH=$$(git branch --show-current); \
	CHANGED_FILES=$$(git diff --name-only main...HEAD); \
	if echo "$$CHANGED_FILES" | grep -q "_config.yml\|_layouts\|google"; then \
		echo "TITLE: Add Google Analytics and comprehensive SEO improvements" > .tmp/pr-content.txt; \
		echo "DESCRIPTION: Enhanced site visibility and tracking capabilities with GA4 integration, improved meta tags, structured data, and SEO optimizations for better search engine discovery." >> .tmp/pr-content.txt; \
	elif echo "$$CHANGED_FILES" | grep -q "Makefile\|performance\|docker"; then \
		echo "TITLE: Optimize development workflow and performance" > .tmp/pr-content.txt; \
		echo "DESCRIPTION: Streamlined development processes with improved build performance, simplified commands, and enhanced developer experience." >> .tmp/pr-content.txt; \
	else \
		echo "TITLE: Repository updates and improvements" > .tmp/pr-content.txt; \
		echo "DESCRIPTION: Various enhancements and updates to improve functionality and user experience." >> .tmp/pr-content.txt; \
	fi
	@echo "Generated PR content saved to .tmp/pr-content.txt"
	@echo "Preview:"
	@cat .tmp/pr-content.txt

# Create GitHub PR using existing content
# Usage: make create-pr
create-pr:
	@if [ ! -f .tmp/pr-content.txt ]; then \
		echo "Error: No PR content found."; \
		echo "Run 'make generate-pr-content' first to create PR content."; \
		exit 1; \
	fi
	@echo "Creating PR with existing content..."
	@echo "Using content from .tmp/pr-content.txt:"
	@cat .tmp/pr-content.txt
	@echo ""
	@python3 scripts/create-pr.py .tmp/pr-content.txt

