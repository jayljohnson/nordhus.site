# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a personal website (nordhus.site) built as a static Jekyll site hosted on GitHub Pages. The site features a minimal design with a blog section containing personal writing and project documentation.

## Site Architecture

### Structure
- `index.md` - Main landing page with contact info and blog post links
- `blog/` - Individual blog posts in markdown format with date-prefixed filenames
- `docs/assets/images/` - Image assets organized by project/date folders
- `_config.yml` - Jekyll configuration (currently minimal/empty)
- `CNAME` - Custom domain configuration for nordhus.site

### Content Organization
- Blog posts follow naming convention: `YYYY-MM-DD-descriptive-title.md`
- Images are organized in dated project folders under `docs/assets/images/`
- Recent posts include project documentation with detailed photos (shed organization, window repair)

## Development Workflow

### Content Creation
- Create new blog posts in `blog/` directory following date naming convention
- Add images to appropriate subfolder in `docs/assets/images/`
- Update `index.md` to include new blog post links in chronological order (newest first)

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
- Include relevant images with proper paths to `docs/assets/images/`
- Maintain consistent front matter if needed

### Image Management
- Store images in date/project-specific folders
- Use descriptive filenames from camera (e.g., `IMG20250726132239.jpg`)
- Organize by project theme for easy reference

## Local Development

### Preview Changes Locally
Use the Makefile commands for easy local development:

```bash
# Start local server (recommended)
make serve

# Alternative commands
make help          # Show all available commands
make build         # Build site only
make clean         # Clean build artifacts
```

The server will be available at `http://localhost:4000` with live reload enabled.

### Development Dependencies
- Docker (for containerized Jekyll)
- Gemfile and Dockerfile provided for consistent environment
- GitHub Pages compatible gem versions

## Domain and Hosting
- Custom domain: nordhus.site (configured via CNAME file)
- Hosted on GitHub Pages with automatic Jekyll processing
- DNS configured through domain registrar to point to GitHub Pages