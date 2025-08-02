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
<<<<<<< Updated upstream
	@rm -f .tmp/*
	@echo "Analyzing git changes to generate PR content..."
	@BRANCH=$$(git branch --show-current); \
	COMMITS=$$(git log --oneline main..HEAD | head -3); \
	FILES=$$(git diff --name-only main...HEAD | tr '\n' ' '); \
	if command -v claude >/dev/null 2>&1; then \
		echo "Using Claude CLI to generate PR content..."; \
		claude "Create a GitHub PR title and description for branch $$BRANCH. Files changed: $$FILES. Recent commits: $$COMMITS. Format: First line 'TITLE: <title>', second line 'DESCRIPTION: <description with markdown formatting like bullet points, bold text, etc>'. Focus on functional impact, not technical details." > .tmp/pr-content.txt; \
	else \
		echo "Claude CLI not found, using fallback..."; \
		echo "TITLE: Updates from $$BRANCH branch" > .tmp/pr-content.txt; \
		echo "DESCRIPTION: **Functional improvements** based on recent commits and file changes." >> .tmp/pr-content.txt; \
		echo "" >> .tmp/pr-content.txt; \
		echo "### Changes in this branch:" >> .tmp/pr-content.txt; \
		echo "- Updated files: $$FILES" >> .tmp/pr-content.txt; \
		echo "- Recent commits: $$COMMITS" >> .tmp/pr-content.txt; \
	fi
	@echo "Generated PR content saved to .tmp/pr-content.txt"
=======
	@echo "## Commit Messages\n" > .tmp/pr-context.md
	@echo "\`\`\`" >> .tmp/pr-context.md
	@git log --oneline main..HEAD >> .tmp/pr-context.md 2>&1 || echo "No commits ahead of main" >> .tmp/pr-context.md
	@echo "\`\`\`\n" >> .tmp/pr-context.md
	@echo "## Actual Changes (diff)\n" >> .tmp/pr-context.md
	@echo "\`\`\`" >> .tmp/pr-context.md
	@git diff main...HEAD >> .tmp/pr-context.md 2>&1 || echo "No diff available" >> .tmp/pr-context.md
	@echo "\`\`\`" >> .tmp/pr-context.md
	@echo "Context saved to .tmp/pr-context.md"
	@echo "Now running Claude Code to generate PR content..."
	@claude code "Based on the git changes in .tmp/pr-context.md, write a GitHub PR title and description. Focus on the PURPOSE and IMPACT of the changes, not on listing files that changed. Use this format:\n\nTITLE: [Brief descriptive title about what this accomplishes]\n\nDESCRIPTION:\n## What this does\n[1-2 sentences explaining the purpose and goals]\n\n## Why this matters\n[1-2 sentences about the impact - user benefits, improvements, fixes]\n\n## Key changes\n• [High-level change 1 - focus on what it accomplishes]\n• [High-level change 2 - focus on what it accomplishes]\n\nAnalyze the actual code changes (git diff) and commit messages to understand the intent and impact. Avoid mentioning specific filenames unless absolutely necessary for understanding." > .tmp/pr-content.txt
	@echo "PR content generated and saved to .tmp/pr-content.txt"
>>>>>>> Stashed changes
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

