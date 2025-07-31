.PHONY: help build-image serve serve-compose build clean docker-clean create-issue create-pr

IMAGE_NAME = nordhus-site-jekyll

# Default target
help:
	@echo "Available commands:"
	@echo "  make serve        - Serve site locally (builds image if needed)"
	@echo "  make serve-compose - Serve using docker-compose (recommended)"
	@echo "  make build-image  - Build custom Docker image with dependencies"
	@echo "  make build        - Build the site"
	@echo "  make clean        - Clean build artifacts"
	@echo "  make docker-clean - Clean Docker images and containers"
	@echo "  make create-issue - Create GitHub issue with pre-filled template"
	@echo "  make create-pr    - Create GitHub PR with automated change summary"

# Build custom Docker image with dependencies baked in
build-image:
	@echo "Building custom Jekyll image with dependencies..."
	docker build -t $(IMAGE_NAME) .

# Serve using custom image (fast startup)
serve: build-image
	@echo "Starting Jekyll server at http://localhost:4000"
	@echo "Opening browser..."
	@(sleep 3 && (xdg-open http://localhost:4000 2>/dev/null || open http://localhost:4000 2>/dev/null || echo "Please open http://localhost:4000 in your browser")) &
	@echo "Press Ctrl+C to stop the server"
	docker run --rm -p 4000:4000 -p 35729:35729 \
		-v "$(PWD)":/srv/jekyll:cached \
		-v /srv/jekyll/vendor \
		-v /srv/jekyll/.bundle \
		$(IMAGE_NAME)

# Serve using docker-compose (recommended for development)
serve-compose:
	@echo "Starting Jekyll server with docker-compose..."
	@echo "Opening browser..."
	@(sleep 5 && (xdg-open http://localhost:4000 2>/dev/null || open http://localhost:4000 2>/dev/null || echo "Please open http://localhost:4000 in your browser")) &
	@echo "Press Ctrl+C to stop the server"
	docker-compose up --build

# Build the site
build: build-image
	@echo "Building Jekyll site..."
	docker run --rm -v "$(PWD)":/srv/jekyll:cached \
		-v /srv/jekyll/vendor \
		-v /srv/jekyll/.bundle \
		$(IMAGE_NAME) \
		jekyll build

# Clean build artifacts
clean:
	@echo "Cleaning build artifacts..."
	rm -rf _site .jekyll-cache .jekyll-metadata

# Clean Docker resources
docker-clean:
	@echo "Cleaning Docker resources..."
	docker-compose down --volumes --remove-orphans 2>/dev/null || true
	docker rmi $(IMAGE_NAME) 2>/dev/null || true
	docker system prune -f

# Create GitHub issue (opens browser with pre-filled content if provided)
# Usage: TITLE="Issue Title" BODY="Issue description" make create-issue
create-issue:
	@echo "Opening GitHub issue page..."
	@python3 -c "import urllib.parse, os, webbrowser; title = os.environ.get('TITLE', ''); body = os.environ.get('BODY', ''); url = 'https://github.com/jayljohnson/nordhus.site/issues/new'; url = url + '?title=' + urllib.parse.quote(title) + '&body=' + urllib.parse.quote(body) if (title or body) else url; webbrowser.open(url)"

# Create GitHub PR with automated change analysis
# Usage: make create-pr
create-pr:
	@echo "Analyzing changes and creating PR..."
	@python3 scripts/create-pr.py

# Simple Python server fallback (no Jekyll processing)
serve-simple:
	@echo "Starting simple Python server at http://localhost:8000"
	@echo "Note: This serves raw files without Jekyll processing"
	@echo "Press Ctrl+C to stop the server"
	cd _site 2>/dev/null && python3 -m http.server 8000 || \
	python3 -m http.server 8000