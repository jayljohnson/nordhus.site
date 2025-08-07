# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a personal website (nordhus.site) built as a Jekyll static site with an advanced **Construction Project Management System**. The site combines traditional blogging with automated photo-to-blog workflows for documenting construction and home improvement projects.

## Construction Project Management Architecture

The core innovation of this site is its automated construction project workflow that transforms photo albums into documented blog posts through a sophisticated Python application layer.

### Project Lifecycle Workflow

**1. Project Initiation:**
```bash
make start-project PROJECT=deck-repair
```
- Creates dedicated git branch (`project/2025-08-04-deck-repair`)
- Sets up Cloudinary photo album with project tags
- Initializes project directory structure in `assets/images/`
- Creates GitHub issue for project tracking

**2. Photo Management:**
```bash
make add-photos PROJECT=deck-repair
```
- Downloads new photos from Cloudinary album
- Organizes images in dated project folders
- Commits changes to project branch
- Updates GitHub issue with sync status

**3. Automated Monitoring:**
- GitHub Actions runs daily construction monitor
- Scans all active project albums for new photos
- Automatically syncs photos to respective project branches
- Updates project issues with progress

**4. Project Completion:**
```bash
make finish-project PROJECT=deck-repair
```
- Generates blog post from project photos and metadata
- Creates pull request to merge project branch to main
- Blog post automatically publishes when PR is merged

### System Architecture

**Clean Architecture Pattern:**
```
CLI Layer (cli.py)
    ↓
Business Logic (project_manager.py, construction_workflow.py)
    ↓
Interfaces (photo_client_interface.py)
    ↓
Infrastructure (cloudinary_client.py)
```

**Key Components:**

- **`scripts/cli.py`** - Unified Click-based CLI with project subcommands
- **`scripts/project/project_manager.py`** - Core project lifecycle management
- **`scripts/workflows/construction_workflow.py`** - Automated monitoring and sync logic
- **`scripts/workflows/construction_monitor.py`** - GitHub Actions entry point
- **`scripts/clients/cloudinary_client.py`** - Photo service integration
- **`scripts/interfaces/photo_client_interface.py`** - Abstract base classes for extensibility

### Feature Flags and Configuration

**ENABLE_PHOTO_MONITORING Environment Variable:**
- `true`: Full photo integration with Cloudinary
- `false`: Disabled photo integration (default for security)

**GitHub Actions Configuration:**
```yaml
env:
  ENABLE_PHOTO_MONITORING: 'false'  # Set to 'true' to enable monitoring
```

**Required Secrets:**
- `GITHUB_TOKEN`: For automated issue/PR creation
- `CLOUDINARY_URL`: Cloud photo service credentials

### Error Handling and Reliability

The construction monitor now properly fails on critical errors:
- **403 GitHub API errors**: Workflow exits with error status
- **Git commit failures**: Throws exceptions instead of silent continuation
- **Photo service failures**: Proper error propagation and logging

## Jekyll Site Architecture

### Standard Jekyll Structure
- `_posts/` - Blog posts with `YYYY-MM-DD-title.md` naming convention
- `_layouts/` - Templates (default.html, post.html)
- `assets/images/` - Project images organized by date folders
- `_config.yml` - Main Jekyll configuration
- `_config_dev.yml` - Development overrides for faster builds

### Content Organization
- Blog posts automatically appear via Jekyll processing
- Images stored in dated project folders: `assets/images/2025-08-04-project-name/`
- Posts use permalink: `/blog/:title/` for clean URLs

## Development Workflow

### Local Development Commands

**Primary Development:**
```bash
make serve             # Start containerized Jekyll with live reload
make build             # Build Docker image and Jekyll site
make clean             # Clean all artifacts and Docker resources
```

**Project Management:**
```bash
make start-project PROJECT=name    # Initiate new construction project
make add-photos PROJECT=name       # Sync photos from cloud service
make finish-project PROJECT=name   # Generate blog post and create PR
make project-status PROJECT=name   # Check project state and photo count
```

**Quality Assurance:**
```bash
make check          # Run full quality check (lint + test coverage)
make test           # Run unit tests with pytest
make test-coverage  # Generate HTML coverage report
make lint           # Check code with ruff linter (150 char line limit)
make lint-fix       # Auto-fix formatting issues
```

### Containerized Development
- **Docker-First**: All commands run in containers for consistency
- **Live Reload**: Port 35729 for automatic browser refresh
- **Volume Optimization**: Cached mounts for source files, excluded for gems/cache
- **Multi-stage Builds**: Optimized for development and production

## Testing Architecture

**Comprehensive Test Suite:**
- `tests/test_cli.py` - Command-line interface testing
- `tests/test_construction_monitor.py` - Workflow automation testing
- `tests/test_construction_workflow.py` - Business logic testing
- `tests/test_cloudinary_client.py` - API integration testing
- `tests/test_project_manager.py` - Project lifecycle testing

**Quality Standards:**
- 62%+ test coverage requirement (enforced in CI)
- pytest framework with HTML coverage reports
- `__init__.py` files excluded from coverage calculations
- All tests run on every PR, blocking merge on failure
- Automatic test artifact cleanup

## Deployment and CI/CD

### GitHub Actions Workflows

**`.github/workflows/deploy.yml`** - Site deployment:
- Runs linting and tests before deployment
- Uses modern Jekyll 4.3+ instead of restrictive github-pages gem
- Only deploys main branch after passing quality checks

**`.github/workflows/construction-projects.yml`** - Project monitoring:
- Runs every 24 hours (configurable via cron)
- Scans for new construction projects and photos
- Creates GitHub issues and syncs photos automatically
- Proper error handling prevents silent failures

### Branch Strategy
- `main` - Production branch, auto-deployed to nordhus.site
- `project/YYYY-MM-DD-project-name` - Individual project branches
- `feature/description` - Feature development branches
- Pull requests required for all merges to main

## SEO and Analytics

### Google Analytics Integration
- GA4 tracking ID `G-5KRKCPHCGX` in `_config.yml`
- Conditional loading (only when `google_analytics` is set)
- Async loading with gtag.js for performance

### SEO Optimization
- Jekyll SEO Tag plugin for automated meta tags
- Open Graph and Twitter Cards support
- XML and HTML sitemaps generated
- Canonical URLs prevent duplicate content

## Automated PR Creation

```bash
make create-pr           # Intelligent PR creation based on git changes
```

**Features:**
- Analyzes file changes to determine PR type
- Generates contextual titles and descriptions
- Opens GitHub with pre-filled PR form
- Focuses on functional impact rather than technical details

## Domain and Hosting
- Custom domain: nordhus.site (via CNAME file)
- GitHub Pages hosting with automatic Jekyll processing
- DNS configured through domain registrar