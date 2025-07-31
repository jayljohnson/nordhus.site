.PHONY: help build-image serve serve-compose build clean docker-clean create-issue create-pr generate-pr-content

IMAGE_NAME = nordhus-site-jekyll

# Default target
help:
	@echo "Available commands:"
	@echo "  make serve              - Serve site locally (builds image if needed)"
	@echo "  make serve-compose      - Serve using docker-compose (recommended)"
	@echo "  make build-image        - Build custom Docker image with dependencies"
	@echo "  make build              - Build the site"
	@echo "  make clean              - Clean build artifacts"
	@echo "  make docker-clean       - Clean Docker images and containers"
	@echo "  make create-issue       - Create GitHub issue with pre-filled template"
	@echo "  make generate-pr-content - Generate PR content with Claude Code"
	@echo "  make create-pr          - Create GitHub PR with pre-generated content"

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

# Generate PR content using Claude Code
# Usage: make generate-pr-content
generate-pr-content:
	@echo "Generating PR content with Claude Code..."
	@if [ ! -d .tmp ]; then mkdir .tmp; fi
	@echo "## Git Status and Changes\n" > .tmp/pr-context.md
	@echo "\`\`\`" >> .tmp/pr-context.md
	@git status >> .tmp/pr-context.md 2>&1 || echo "Not a git repository" >> .tmp/pr-context.md
	@echo "\`\`\`\n" >> .tmp/pr-context.md
	@echo "## Files Changed\n" >> .tmp/pr-context.md
	@echo "\`\`\`" >> .tmp/pr-context.md
	@git diff --name-only main...HEAD >> .tmp/pr-context.md 2>&1 || echo "No changes or not on a branch" >> .tmp/pr-context.md
	@echo "\`\`\`\n" >> .tmp/pr-context.md
	@echo "## Commit History\n" >> .tmp/pr-context.md
	@echo "\`\`\`" >> .tmp/pr-context.md
	@git log --oneline main..HEAD >> .tmp/pr-context.md 2>&1 || echo "No commits ahead of main" >> .tmp/pr-context.md
	@echo "\`\`\`\n" >> .tmp/pr-context.md
	@echo "## Change Summary\n" >> .tmp/pr-context.md
	@echo "\`\`\`" >> .tmp/pr-context.md
	@git diff --stat main...HEAD >> .tmp/pr-context.md 2>&1 || echo "No diff available" >> .tmp/pr-context.md
	@echo "\`\`\`" >> .tmp/pr-context.md
	@echo "Context saved to .tmp/pr-context.md"
	@echo "Now running: claude code 'Based on the git changes above, write a concise GitHub PR title and description that explains what was changed and why. Format as: TITLE: <title> followed by DESCRIPTION: <description>. Focus on user impact and key improvements.'"
	@claude code "Based on the git changes in .tmp/pr-context.md, write a concise GitHub PR title and description that explains what was changed and why. Format as: TITLE: <title> followed by DESCRIPTION: <description>. Focus on user impact and key improvements." > .tmp/pr-content.txt
	@echo "PR content generated and saved to .tmp/pr-content.txt"
	@echo "Preview:"
	@cat .tmp/pr-content.txt

# Create GitHub PR with pre-generated content
# Usage: make create-pr (requires generate-pr-content to be run first)
create-pr:
	@echo "Creating PR with generated content..."
	@if [ ! -f .tmp/pr-content.txt ]; then echo "Error: No PR content found. Run 'make generate-pr-content' first."; exit 1; fi
	@python3 scripts/create-pr.py .tmp/pr-content.txt

# Simple Python server fallback (no Jekyll processing)
serve-simple:
	@echo "Starting simple Python server at http://localhost:8000"
	@echo "Note: This serves raw files without Jekyll processing"
	@echo "Press Ctrl+C to stop the server"
	cd _site 2>/dev/null && python3 -m http.server 8000 || \
	python3 -m http.server 8000