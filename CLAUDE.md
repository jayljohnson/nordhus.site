# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a personal website (nordhus.site) built as a static Jekyll site hosted on GitHub Pages. The site features a minimal design with a blog section containing personal writing and project documentation.

## Site Architecture

### Structure
- `index.md` - Main landing page with contact info and blog post links
- `_posts/` - Blog posts in markdown format with date-prefixed filenames (Jekyll standard)
- `_layouts/` - Jekyll templates (default.html, post.html)
- `assets/images/` - Image assets organized by project/date folders
- `_config.yml` - Main Jekyll configuration with plugins and site settings
- `_config_dev.yml` - Development-specific config overrides for faster builds
- `CNAME` - Custom domain configuration for nordhus.site

### Content Organization
- Blog posts use Jekyll's standard `_posts/` directory with `YYYY-MM-DD-title.md` naming
- Posts use permalink: `/blog/:title/` for clean URLs
- Images organized in dated project folders under `assets/images/`
- Recent posts include project documentation with detailed photos

## Development Workflow

### Content Creation
- Create new blog posts in `_posts/` directory following Jekyll's `YYYY-MM-DD-title.md` convention
- Add images to appropriate subfolder in `assets/images/`
- Posts automatically appear on the site via Jekyll's processing - no manual index updates needed

### Deployment
- GitHub Pages automatically builds and deploys the site on push to main branch
- No build commands needed - GitHub handles Jekyll processing
- Changes typically take a few minutes to appear due to CDN caching

### Branch Strategy
- `main` - Production branch, auto-deployed to nordhus.site
- Feature branches for new content (e.g., `2025-07-26-window-repair-photos`)
- Use pull requests for merging feature branches

## File Patterns

### Blog Posts
- Always include descriptive title and date
- Use markdown formatting
- Include relevant images with proper paths to `assets/images/`
- Maintain consistent front matter if needed

### Image Management
- Store images in date/project-specific folders
- Use descriptive filenames from camera (e.g., `IMG20250726132239.jpg`)
- Organize by project theme for easy reference

## Local Development

### Preview Changes Locally
Use the Makefile commands for easy local development:

```bash
# Recommended: Docker Compose (fastest startup)
make serve-compose     # Uses docker-compose for optimized workflow

# Alternative: Custom Docker image (good for repeated use)
make serve            # Builds custom image, then serves with live reload

# Other commands
make help             # Show all available commands
make build            # Build site only
make clean            # Clean build artifacts
make docker-clean     # Clean Docker resources
```

The server will be available at `http://localhost:4000` with live reload enabled.

### Development Architecture
- **Containerized Development**: Uses Docker with Jekyll 4.2.2 base image
- **Multi-config Setup**: `_config.yml` for production, `_config_dev.yml` for development overrides
- **Volume Optimization**: Cached mounts for source files, excluded volumes for gems/cache
- **Live Reload**: Port 35729 for automatic browser refresh on file changes
- **Performance**: Incremental builds and force polling for file watching

### Development Dependencies
- Docker (for containerized Jekyll environment)
- `Gemfile` with GitHub Pages gem and compatible versions
- `Dockerfile` with optimized Jekyll setup and caching
- `docker-compose.yml` for streamlined development workflow

## Automated Workflows

### GitHub PR Creation
Streamlined PR workflow with AI-generated content:

```bash
make generate-pr-content  # Creates PR title/description using Claude Code
make create-pr           # Opens GitHub with pre-filled PR form
```

The PR generation script (`scripts/create-pr.py`) analyzes git changes and creates contextual PR content, including Claude Code attribution.

### Development Performance Optimizations
Current branch focuses on `make serve` startup performance improvements:
- Pre-built Docker images with dependencies baked in
- Optimized volume mounts to exclude gems/cache from host
- Parallel browser opening and server readiness detection

## Domain and Hosting
- Custom domain: nordhus.site (configured via CNAME file)
- Hosted on GitHub Pages with automatic Jekyll processing
- DNS configured through domain registrar to point to GitHub Pages