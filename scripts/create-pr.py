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
        
        body = f"""## Summary

This PR contains {len(commits)} commit(s) across {len(files)} file(s).

### Files Changed
{file_list}

### Statistics
```
{stats}
```

### Impact Analysis
- **Files added:** {files_added}
- **Files modified:** {files_modified}
- **Total changes:** {total_lines} lines

### Commits
{commit_list}

🤖 Generated with [Claude Code](https://claude.ai/code)

Co-Authored-By: Claude <noreply@anthropic.com>"""
        
        # Create GitHub URL
        url = f'https://github.com/jayljohnson/nordhus.site/compare/{branch}?expand=1&title={urllib.parse.quote(title)}&body={urllib.parse.quote(body)}'
        
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