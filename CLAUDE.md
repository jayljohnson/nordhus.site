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
Use the Makefile commands for streamlined development:

```bash
make serve             # Start Jekyll server with Docker Compose (recommended)
make build             # Build Docker image and Jekyll site
make clean             # Clean build artifacts and Docker resources
make help              # Show all available commands
```

The server will be available at `http://localhost:4000` with live reload enabled.

### Development Architecture
- **Containerized Development**: Uses Docker with Jekyll 4.2.2 base image
- **Multi-config Setup**: `_config.yml` for production, `_config_dev.yml` for development overrides
- **Volume Optimization**: Cached mounts for source files, excluded volumes for gems/cache
- **Live Reload**: Port 35729 for automatic browser refresh on file changes
- **Performance**: Incremental builds and force polling for file watching
- **Image Optimization**: 108MB of images moved to `assets/` to avoid Jekyll processing overhead

### Development Dependencies
- Docker (for containerized Jekyll environment)
- `Gemfile` with GitHub Pages gem and compatible versions
- `Dockerfile` with optimized Jekyll setup and caching
- `docker-compose.yml` for streamlined development workflow

## SEO and Analytics

### Google Analytics
- **GA4 Integration**: Tracking ID `G-5KRKCPHCGX` configured in `_config.yml`
- **Conditional Loading**: Analytics code only loads when `google_analytics` is set
- **Performance Optimized**: Uses async loading with gtag.js

### SEO Features
- **Meta Tags**: Comprehensive Open Graph, Twitter Cards, and semantic HTML
- **Structured Data**: JSON-LD schema for blog posts with keywords and metadata
- **Sitemaps**: Both XML (`sitemap.xml`) and HTML (`sitemap.html`) versions
- **Robots.txt**: Optimized for search engine crawling
- **Canonical URLs**: Prevents duplicate content issues

## Automated Workflows

### GitHub PR Creation
Intelligent PR workflow that analyzes changes:

```bash
make create-pr           # Analyzes git changes and opens GitHub PR with contextual content
```

**How it works:**
- Detects file changes to determine PR type (analytics, performance, general)
- Generates appropriate title and description focusing on functional impact
- Opens GitHub with pre-filled PR form using URL parameters
- Requires all changes to be committed before running

## Photo Album Integration Feature Flag

The construction project workflow includes photo album integration that can be controlled via feature flags:

### Environment Variable
- **ENABLE_PHOTO_MONITORING**: Controls photo album integration
  - `true`: Enables Imgur album creation and monitoring
  - `false`: Disables photo integration (default)

### GitHub Actions
Photo monitoring in GitHub Actions is controlled by the workflow environment variable:
```yaml
env:
  ENABLE_PHOTO_MONITORING: 'false'  # Set to 'true' to enable
```

### Local Development
For local project creation:
```bash
ENABLE_PHOTO_MONITORING=true make start-project PROJECT=my-project
```

When disabled:
- Projects are created without photo albums
- No Imgur API calls are made
- GitHub Actions monitoring is skipped
- All other functionality remains intact

## Domain and Hosting
- Custom domain: nordhus.site (configured via CNAME file)
- Hosted on GitHub Pages with automatic Jekyll processing
- DNS configured through domain registrar to point to GitHub Pages