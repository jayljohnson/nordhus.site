---
layout: post
title: "From Manual Markdown to Automated Jekyll: Streamlining Blog Development"
date: 2025-07-31
excerpt: "How I transformed my static site development workflow from 30+ minutes of manual work to a 2-minute automated process using Jekyll, Docker, and Make."
---

*How I transformed my static site development workflow from 30+ minutes of manual work to a 2-minute automated process using Jekyll, Docker, and Make.*

## The Problem: Manual Everything

My personal website started as the simplest possible setup: raw Markdown files in a `blog/` directory with manual index updates. While this got me writing quickly, the development workflow had become painful:

**Previous Process (30-45 minutes):**
1. Create new `.md` file in `blog/` directory (~2 minutes)
2. Write content with proper formatting (~20-30 minutes)
3. Manually update `index.md` with new post link (~2 minutes)
4. Test changes by pushing to GitHub and waiting for Pages deployment (~5-10 minutes)
5. Fix any formatting issues and repeat cycle (~5+ minutes)

The biggest pain points were:
- **No local preview** - Had to push to see changes
- **Manual index maintenance** - Easy to forget or mess up
- **Inconsistent styling** - No templates or layouts
- **Slow feedback loop** - GitHub Pages deployment delays

## The Solution: Modern Jekyll Workflow

Working with Claude Code, I implemented a complete development workflow overhaul that maintains the simplicity I loved while adding professional tooling.

### Key Improvements

**1. Proper Jekyll Structure**
- Moved posts to `_posts/` directory with proper naming
- Added front matter to all posts for metadata
- Created `_layouts/` with consistent templates
- Automated post listing with Jekyll's post loop

**2. Local Development Environment**
- Docker-based Jekyll setup for consistency
- Custom Dockerfile with pre-installed dependencies  
- Make commands for one-click development
- Live reload for instant preview

**3. Streamlined Commands**
```bash
make serve        # Start local server + open browser
make build        # Build site
make create-issue # GitHub issue creation
```

### New Process (2-3 minutes)

**Creating a new post now:**
1. Run `make serve` (starts local server, opens browser automatically)
2. Create `_posts/YYYY-MM-DD-title.md` with front matter
3. Write content with instant preview
4. Commit and push when ready

That's it. The index updates automatically, styling is consistent, and I can see changes instantly.

## Technical Implementation

The transformation involved several key components:

**Jekyll Configuration:**
- `_config.yml` with GitHub Pages compatibility
- Automated post discovery and listing
- Proper permalink structure

**Docker Setup:**
- Custom image with dependencies pre-installed
- Volume mounting for live file editing
- Optimized layer caching to avoid repeated installs

**Makefile Automation:**
- One-command local development
- Browser auto-opening
- GitHub integration helpers

**Content Migration:**
- Moved 9 blog posts from `blog/` to `_posts/`
- Added proper front matter to all posts
- Removed duplicate titles (layout handles display)

## Results: 15x Faster Iteration

The workflow improvements created dramatic time savings:

| Task | Before | After | Improvement |
|------|--------|-------|-------------|
| Start development | Push to GitHub (~5-10 min) | `make serve` (~30 sec) | **10-20x faster** |
| See changes | Wait for deployment (~5-10 min) | Instant with live reload | **Immediate** |
| Add new post | Manual index update (~2 min) | Automatic | **Eliminated** |
| Fix styling issues | Multiple deploy cycles (~15+ min) | Instant local preview | **15x+ faster** |

**Total time to publish:** Down from 30-45 minutes to 2-3 minutes.

## Key Learnings

1. **Start simple, evolve thoughtfully** - The basic Markdown approach got me writing, then I added tooling when pain points became clear.

2. **Local development is essential** - The feedback loop improvement alone was worth the setup effort.

3. **Automation eliminates errors** - No more forgetting to update the index or inconsistent formatting.

4. **Docker makes environments predictable** - Same Jekyll version as GitHub Pages, works everywhere.

5. **Make is still relevant** - Simple, universal, and perfect for project-specific commands.

## The Meta Moment

This blog post itself demonstrates the new workflow in action. I created it in under 3 minutes:
- Ran `make serve`
- Created the file with proper front matter
- Wrote while previewing changes locally
- No manual index updates needed

The conversation that led to these improvements is preserved in the [full transcript](../docs/assets/transcripts/2025-07-31-jekyll-improvements-conversation.html) - a detailed record of the iterative development process with Claude Code.

## Next Steps

The foundation is now solid for consistent blogging with minimal friction. Future improvements might include:
- CLI tool modernization (tracked in [GitHub issue](https://github.com/jayljohnson/nordhus.site/issues))
- Content categories and tags
- RSS feed optimization
- Search functionality

Sometimes the best way to improve your writing is to eliminate everything that makes writing harder.