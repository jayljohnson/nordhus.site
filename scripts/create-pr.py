#!/usr/bin/env python3
import subprocess
import urllib.parse
import webbrowser
import os
import sys
import re

def main():
    try:
        # Check if we have a pre-generated content file
        generated_content_file = sys.argv[1] if len(sys.argv) > 1 else None
        
        if generated_content_file and os.path.exists(generated_content_file):
            # Use pre-generated content
            with open(generated_content_file, 'r') as f:
                content = f.read()
            
            # Parse the content for title and description
            title_match = re.search(r'TITLE:\s*(.+)', content)
            desc_match = re.search(r'DESCRIPTION:\s*(.+?)(?=\n\n|\Z)', content, re.DOTALL)
            
            if title_match and desc_match:
                title = title_match.group(1).strip()
                description = desc_match.group(1).strip()
                
                # Get current branch
                branch = subprocess.check_output(['git', 'branch', '--show-current']).decode().strip()
                
                # Add Claude Code attribution
                body = f"""{description}

🤖 Generated with [Claude Code](https://claude.ai/code)

Co-Authored-By: Claude <noreply@anthropic.com>"""
                
                # Create GitHub URL for PR creation
                encoded_title = urllib.parse.quote(title)
                encoded_body = urllib.parse.quote(body)
                
                # GitHub URL length limit is ~8000 chars, truncate if needed
                full_url = f'https://github.com/jayljohnson/nordhus.site/compare/main...{branch}?expand=1&title={encoded_title}&body={encoded_body}'
                
                if len(full_url) > 7500:  # Leave some buffer
                    # Use shorter description for URL
                    short_body = "See full details in PR description after creation."
                    encoded_short_body = urllib.parse.quote(short_body)
                    url = f'https://github.com/jayljohnson/nordhus.site/compare/main...{branch}?expand=1&title={encoded_title}&body={encoded_short_body}'
                    print("Note: Full description too long for URL, using shortened version")
                else:
                    url = full_url
                
                print(f'Opening PR for branch: {branch} (AI-generated content)')
                webbrowser.open(url)
                return
            else:
                print("Error: Could not parse TITLE and DESCRIPTION from generated content")
                print("Content should be formatted as:")
                print("TITLE: Your PR Title")
                print("DESCRIPTION: Your PR description...")
                sys.exit(1)
        # Get current branch
        branch = subprocess.check_output(['git', 'branch', '--show-current']).decode().strip()
        
        if branch == 'main':
            print('Cannot create PR from main branch. Switch to feature branch first.')
            sys.exit(1)
        
        # Check for uncommitted changes
        status = subprocess.check_output(['git', 'status', '--porcelain']).decode()
        if status.strip():
            print('Uncommitted changes detected. Commit changes first.')
            sys.exit(1)
        
        # Get change information
        diff = subprocess.check_output(['git', 'diff', 'main...HEAD']).decode()
        stats = subprocess.check_output(['git', 'diff', '--stat', 'main...HEAD']).decode()
        files = subprocess.check_output(['git', 'diff', '--name-only', 'main...HEAD']).decode().strip().split('\n')
        files = [f for f in files if f]
        commits = subprocess.check_output(['git', 'log', '--oneline', 'main..HEAD']).decode().strip().split('\n')
        commits = [c for c in commits if c]
        
        # Generate PR content
        title = f'Feature: {branch.replace("-", " ").title()}'
        
        file_list = '\n'.join([f'- {f}' for f in files])
        commit_list = '\n'.join([f'- {c}' for c in commits])
        
        files_added = len([f for f in files if not os.path.exists(f)])
        files_modified = len([f for f in files if os.path.exists(f)])
        total_lines = len(diff.split('\n'))
        
        # Analyze impact based on file types and changes
        jekyll_files = [f for f in files if f.endswith(('.md', '.yml', '.yaml', '_config.yml')) or '_posts/' in f or '_layouts/' in f]
        docker_files = [f for f in files if 'Dockerfile' in f or 'docker-compose' in f]
        makefile_changes = [f for f in files if 'Makefile' in f or 'makefile' in f]
        script_files = [f for f in files if f.endswith(('.py', '.sh')) or 'scripts/' in f]
        
        impact_summary = []
        if jekyll_files:
            impact_summary.append(f"**Jekyll/Content**: {len(jekyll_files)} files - Site structure and content improvements")
        if docker_files:
            impact_summary.append(f"**Development Environment**: {len(docker_files)} files - Local development workflow enhancements")
        if makefile_changes:
            impact_summary.append("**Build Automation**: Streamlined development commands and workflows")
        if script_files:
            impact_summary.append(f"**Tooling**: {len(script_files)} scripts - Development productivity improvements")
        
        # Generate dynamic description based on changes
        description_parts = []
        
        if jekyll_files:
            layout_changes = [f for f in jekyll_files if '_layouts/' in f]
            post_changes = [f for f in jekyll_files if '_posts/' in f]
            config_changes = [f for f in jekyll_files if '_config.yml' in f or 'index.md' in f]
            
            if layout_changes:
                description_parts.append(f"• Updated {len(layout_changes)} layout template(s) for improved functionality")
            if post_changes:
                description_parts.append(f"• Modified {len(post_changes)} blog post(s) with content improvements")
            if config_changes:
                description_parts.append(f"• Enhanced site configuration and main pages")
        
        if docker_files:
            description_parts.append("• Improved Docker development environment")
        if makefile_changes:
            description_parts.append("• Enhanced build automation and developer workflows")
        if script_files:
            description_parts.append(f"• Updated {len(script_files)} development script(s)")
        
        # Analyze commit messages for better context
        commit_themes = []
        for commit in commits:
            commit_lower = commit.lower()
            if 'seo' in commit_lower or 'meta' in commit_lower or 'schema' in commit_lower:
                commit_themes.append('SEO optimization')
            elif 'dark' in commit_lower or 'theme' in commit_lower:
                commit_themes.append('UI/UX improvements')
            elif 'excerpt' in commit_lower:
                commit_themes.append('Content enhancement')
            elif 'json-ld' in commit_lower or 'structured' in commit_lower:
                commit_themes.append('Search engine optimization')
        
        commit_themes = list(set(commit_themes))  # Remove duplicates
        
        body = f"""## Summary

{chr(10).join(description_parts) if description_parts else 'Various improvements and updates to the site.'}

## Changes Made

{chr(10).join([f'• {theme}' for theme in commit_themes]) if commit_themes else ''}

## Files Modified
{file_list}

## Commits
{commit_list}

## Technical Details
```
{stats}
```

🤖 Generated with [Claude Code](https://claude.ai/code)

Co-Authored-By: Claude <noreply@anthropic.com>"""
        
        # Create GitHub URL - check length and handle accordingly
        full_url = f'https://github.com/jayljohnson/nordhus.site/compare/{branch}?expand=1&title={urllib.parse.quote(title)}&body={urllib.parse.quote(body)}'
        
        if len(full_url) > 8000:  # GitHub URL limit
            # Create shorter version focusing on impact
            short_body = f"""## Summary

{chr(10).join(description_parts) if description_parts else 'Various improvements and updates to the site.'}

## Changes Made

{chr(10).join([f'• {theme}' for theme in commit_themes]) if commit_themes else ''}

## Files Modified ({len(files)})
{chr(10).join(files[:5])}{'...' if len(files) > 5 else ''}

🤖 Generated with [Claude Code](https://claude.ai/code)

Co-Authored-By: Claude <noreply@anthropic.com>"""
            
            url = f'https://github.com/jayljohnson/nordhus.site/compare/{branch}?expand=1&title={urllib.parse.quote(title)}&body={urllib.parse.quote(short_body)}'
            print(f'Opening PR for branch: {branch} (description optimized for impact)')
        else:
            url = full_url
            print(f'Opening PR for branch: {branch}')
        
        webbrowser.open(url)
        
    except subprocess.CalledProcessError as e:
        print(f'Git command failed: {e}')
        sys.exit(1)
    except Exception as e:
        print(f'Error: {e}')
        sys.exit(1)

if __name__ == '__main__':
    main()