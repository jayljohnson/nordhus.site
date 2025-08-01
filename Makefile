.PHONY: help serve build clean create-issue create-pr

IMAGE_NAME = nordhus-site-jekyll

# Default target
help:
	@echo "Available commands:"
	@echo "  make build              - Build Docker image and Jekyll site"
	@echo "  make clean              - Clean build artifacts and Docker resources"
	@echo "  make create-issue       - Create GitHub issue with pre-filled template"
	@echo "  make create-pr          - Create GitHub PR with AI-generated content"
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

# Create GitHub PR with AI-generated content
# Usage: make create-pr
create-pr:
	@echo "Checking for uncommitted changes..."
	@if [ -n "$$(git status --porcelain)" ]; then \
		echo "Error: You have uncommitted changes. Please commit them first:"; \
		echo ""; \
		git status --short; \
		echo ""; \
		echo "Run: git add . && git commit -m 'Your commit message'"; \
		exit 1; \
	fi
	@echo "Generating PR content with Claude Code..."
	@if [ ! -d .tmp ]; then mkdir .tmp; fi
	@echo "## Git Status and Changes" > .tmp/pr-context.md
	@echo "" >> .tmp/pr-context.md
	@echo "\`\`\`" >> .tmp/pr-context.md
	@git status >> .tmp/pr-context.md 2>&1 || echo "Not a git repository" >> .tmp/pr-context.md
	@echo "\`\`\`" >> .tmp/pr-context.md
	@echo "" >> .tmp/pr-context.md
	@echo "## Files Changed" >> .tmp/pr-context.md
	@echo "" >> .tmp/pr-context.md
	@echo "\`\`\`" >> .tmp/pr-context.md
	@git diff --name-only main...HEAD >> .tmp/pr-context.md 2>&1 || echo "No changes or not on a branch" >> .tmp/pr-context.md
	@echo "\`\`\`" >> .tmp/pr-context.md
	@echo "" >> .tmp/pr-context.md
	@echo "## Commit History" >> .tmp/pr-context.md
	@echo "" >> .tmp/pr-context.md
	@echo "\`\`\`" >> .tmp/pr-context.md
	@git log --oneline main..HEAD >> .tmp/pr-context.md 2>&1 || echo "No commits ahead of main" >> .tmp/pr-context.md
	@echo "\`\`\`" >> .tmp/pr-context.md
	@echo "" >> .tmp/pr-context.md
	@echo "## Change Summary" >> .tmp/pr-context.md
	@echo "" >> .tmp/pr-context.md
	@echo "\`\`\`" >> .tmp/pr-context.md
	@git diff --stat main...HEAD >> .tmp/pr-context.md 2>&1 || echo "No diff available" >> .tmp/pr-context.md
	@echo "\`\`\`" >> .tmp/pr-context.md
	@echo "Generating PR content..."
	@claude code "Based on the git changes in .tmp/pr-context.md, write a GitHub PR title and description. Format as 'TITLE: <title>' followed by 'DESCRIPTION: <description>'. Focus on performance improvements, code simplification, and quantitative impact. Include up to 5 bullet points with specific metrics where possible." > .tmp/pr-content.txt
	@echo "Generated PR content saved to .tmp/pr-content.txt"
	@echo "Preview:"
	@cat .tmp/pr-content.txt
	@echo ""
	@echo "Creating PR with generated content..."
	@python3 scripts/create-pr.py .tmp/pr-content.txt

