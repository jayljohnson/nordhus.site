# nordhus.site

A personal Jekyll website with automated construction project documentation workflows.

## Overview

This site combines traditional blogging with an innovative **Construction Project Management System** that automatically transforms photo albums into documented blog posts. The system handles the entire lifecycle from project initiation to published documentation.

🏗️ **Live Site**: [nordhus.site](https://nordhus.site)

## Key Features

- **Automated Project Workflows**: Photo-to-blog automation for construction projects
- **Containerized Development**: Docker-based Jekyll environment with live reload
- **Quality-First CI/CD**: Comprehensive testing and linting before deployment
- **Cloud Photo Integration**: Cloudinary API for organized photo management
- **SEO Optimized**: Modern Jekyll with comprehensive meta tags and analytics

## Quick Start

### Prerequisites
- Docker and Docker Compose
- Git

### Local Development

1. **Clone and start development server:**
   ```bash
   git clone https://github.com/jayljohnson/nordhus.site.git
   cd nordhus.site
   make serve
   ```

2. **View the site:**
   Open http://localhost:4000 in your browser

3. **Make changes:**
   Edit files and see live updates with automatic browser refresh

### Available Commands

```bash
# Development
make serve             # Start Jekyll server with live reload
make build             # Build Docker image and Jekyll site
make clean             # Clean build artifacts and Docker resources

# Quality Assurance
make check             # Run all quality checks (lint + tests)
make test              # Run unit tests
make lint              # Check code quality
make lint-fix          # Auto-fix formatting issues

# Project Management (requires photo service setup)
make start-project PROJECT=name    # Create new construction project
make add-photos PROJECT=name       # Sync photos from cloud service
make finish-project PROJECT=name   # Generate blog post and create PR
```

## Construction Project System

### How It Works

1. **Start Project**: Creates git branch, photo album, and project structure
2. **Add Photos**: Automatically downloads and organizes photos from cloud service
3. **Monitor Progress**: GitHub Actions sync new photos daily
4. **Finish Project**: Generates blog post and creates pull request

### Example Workflow

```bash
# Start a new deck repair project
make start-project PROJECT=deck-repair

# Add photos as you work (or they sync automatically)
make add-photos PROJECT=deck-repair

# Generate blog post when complete
make finish-project PROJECT=deck-repair
```

### Project Structure
```
assets/images/2025-08-04-deck-repair/
├── IMG001.jpg                    # Project photos
├── IMG002.jpg
└── project.json                  # Project metadata
```

## Architecture

### Technology Stack
- **Frontend**: Jekyll 4.3+ static site generator
- **Backend**: Python 3.11 with Click CLI framework
- **Infrastructure**: Docker, GitHub Actions, GitHub Pages
- **Photo Management**: Cloudinary API integration
- **Testing**: pytest with 62%+ coverage requirement

### System Design
```
CLI Layer (scripts/cli.py)
    ↓
Business Logic (project/, workflows/)
    ↓
Interfaces (photo service abstraction)
    ↓
Infrastructure (Cloudinary, GitHub APIs)
```

## Development

### File Organization
- `_posts/` - Jekyll blog posts (`YYYY-MM-DD-title.md`)
- `assets/images/` - Project images organized by date
- `scripts/` - Python application for project management
- `tests/` - Comprehensive test suite
- `.github/workflows/` - CI/CD and automation

### Creating Content

**Blog Posts:**
Create markdown files in `_posts/` following Jekyll conventions:
```markdown
---
layout: post
title: "My Project"
---

Content here...
```

**Construction Projects:**
Use the project management commands to automate the entire workflow from photos to published posts.

### Testing
```bash
make test              # Run all tests
make test-coverage     # Generate HTML coverage report
```

Tests are located in `/tests/` with comprehensive coverage of all Python modules.

### Code Quality
- **Linting**: ruff with 150 character line limit
- **Formatting**: Automatic code formatting
- **Coverage**: 62%+ test coverage enforced
- **CI/CD**: All checks run on every PR

## Configuration

### Feature Flags

**Photo Monitoring** (disabled by default):
```bash
# Enable for local development
ENABLE_PHOTO_MONITORING=true make start-project PROJECT=test

# Enable in GitHub Actions
# Set ENABLE_PHOTO_MONITORING: 'true' in workflow file
```

### Required Secrets (for photo integration)
- `GITHUB_TOKEN` - GitHub API access
- `CLOUDINARY_URL` - Photo service credentials

## Deployment

The site automatically deploys to GitHub Pages when changes are pushed to the `main` branch, after passing all quality checks.

### Branch Strategy
- `main` - Production branch (auto-deployed)
- `project/YYYY-MM-DD-name` - Individual project branches
- `feature/description` - Feature development branches

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes with tests
4. Run `make check` to ensure quality
5. Submit a pull request

All PRs must pass linting, tests, and code coverage requirements.

## License

This is a personal website project. Feel free to use the construction project management system concepts in your own projects.