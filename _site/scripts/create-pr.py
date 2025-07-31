#!/usr/bin/env python3
import subprocess
import urllib.parse
import webbrowser
import os
import sys

def main():
    try:
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
        
        body = f"""## Impact Summary

{chr(10).join(impact_summary)}

## Key Improvements
- **Development Speed**: Automated workflows reduce setup time
- **Consistency**: Standardized templates and layouts
- **Developer Experience**: One-command local development with live reload
- **Maintainability**: Automated content management and PR/issue creation

## Technical Changes
```
{stats}
```

## Quality Assurance
- [ ] Local development tested (`make serve`)
- [ ] All changes committed and pushed
- [ ] Documentation updated where needed

🤖 Generated with [Claude Code](https://claude.ai/code)

Co-Authored-By: Claude <noreply@anthropic.com>"""
        
        # Create GitHub URL - check length and handle accordingly
        full_url = f'https://github.com/jayljohnson/nordhus.site/compare/{branch}?expand=1&title={urllib.parse.quote(title)}&body={urllib.parse.quote(body)}'
        
        if len(full_url) > 8000:  # GitHub URL limit
            # Create shorter version focusing on impact
            short_body = f"""## Impact Summary

{chr(10).join(impact_summary)}

## Key Improvements
- **Development Speed**: Automated workflows reduce setup time
- **Developer Experience**: One-command local development with live reload
- **Maintainability**: Automated content management and tooling

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