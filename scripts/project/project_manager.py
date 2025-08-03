#!/usr/bin/env python3
"""
Mobile Construction Project Manager
Handles photo organization, branch creation, and blog post generation for construction projects.
"""

import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from scripts.clients.imgur_client import ImgurClient


def get_project_dir(project_name):
    """Get the project directory path"""
    return Path(f"assets/images/{datetime.now().strftime('%Y-%m-%d')}-{project_name}")


def get_project_branch(project_name):
    """Get the git branch name for the project"""
    return f"project/{datetime.now().strftime('%Y-%m-%d')}-{project_name}"


def create_project_branch(project_name):
    """Create and switch to project branch"""
    branch_name = get_project_branch(project_name)
    try:
        # Check if branch already exists
        result = subprocess.run(["git", "branch", "--list", branch_name], check=False, capture_output=True, text=True)

        if branch_name in result.stdout:
            print(f"Branch {branch_name} already exists, switching to it...")
            subprocess.run(["git", "checkout", branch_name], check=True)
        else:
            # Create new branch from main
            subprocess.run(["git", "checkout", "main"], check=True)
            subprocess.run(["git", "pull", "origin", "main"], check=True)
            subprocess.run(["git", "checkout", "-b", branch_name], check=True)
            print(f"Created and switched to branch: {branch_name}")

        return branch_name
    except subprocess.CalledProcessError as e:
        print(f"Error creating branch: {e}")
        return None


def setup_project_directory(project_name):
    """Create project directory structure"""
    project_dir = get_project_dir(project_name)
    project_dir.mkdir(parents=True, exist_ok=True)

    # Create project metadata file
    metadata = {"project_name": project_name, "start_date": datetime.now().isoformat(), "photos": [], "status": "active"}

    with open(project_dir / "project.json", "w") as f:
        json.dump(metadata, f, indent=2)

    print(f"Created project directory: {project_dir}")
    return project_dir


def start_project(project_name):
    """Start a new construction project"""
    print(f"Starting project: {project_name}")

    # Validate project name
    if not re.match(r"^[a-zA-Z0-9-_]+$", project_name):
        print("Error: Project name can only contain letters, numbers, hyphens, and underscores")
        return False

    # Create branch
    branch = create_project_branch(project_name)
    if not branch:
        return False

    # Setup directory
    project_dir = setup_project_directory(project_name)

    # Create photo album (if enabled)
    photo_integration_enabled = os.environ.get("ENABLE_PHOTO_MONITORING", "false").lower() == "true"
    if photo_integration_enabled:
        album_title = f"Construction: {project_name.replace('-', ' ').replace('_', ' ').title()}"
        try:
            photos_client = ImgurClient()
            album = photos_client.create_album(album_title)

            if album:
                # Save album info to project metadata
                metadata_file = project_dir / "project.json"
                with open(metadata_file) as f:
                    metadata = json.load(f)

                metadata["google_photos_album"] = {"id": album["id"], "title": album["title"], "url": album.get("productUrl", "")}

                with open(metadata_file, "w") as f:
                    json.dump(metadata, f, indent=2)

                print(f"Created Google Photos album: {album_title}")
                if album.get("productUrl"):
                    print(f"Album URL: {album['productUrl']}")
            else:
                print("Warning: Could not create Google Photos album. You can create it manually.")

        except Exception as e:
            print(f"Warning: Google Photos integration failed: {e}")
            print("You can still use the project without Google Photos integration.")
    else:
        print("Photo album integration is disabled (ENABLE_PHOTO_MONITORING=false)")
        print("Project created without photo album integration")

    # Create initial commit
    try:
        subprocess.run(["git", "add", str(project_dir)], check=True)
        subprocess.run(["git", "commit", "-m", f"Start project: {project_name}"], check=True)
        print("Initial commit created")
    except subprocess.CalledProcessError as e:
        print(f"Error creating initial commit: {e}")
        return False

    print(f"""
Project setup complete!

Next steps:
1. Take photos on your mobile device
2. Add them to Google Photos album: {album_title}
3. When ready to sync photos, run: make add-photos PROJECT={project_name}
4. When project is complete, run: make finish-project PROJECT={project_name}

Note: Photos will be downloaded from Google Photos and organized locally.
""")
    return True


def add_photos(project_name):
    """Add photos to existing project from Google Photos"""
    project_dir = get_project_dir(project_name)

    if not project_dir.exists():
        print(f"Error: Project {project_name} not found. Run 'make start-project PROJECT={project_name}' first.")
        return False

    # Switch to project branch
    branch = get_project_branch(project_name)
    try:
        subprocess.run(["git", "checkout", branch], check=True)
    except subprocess.CalledProcessError:
        print(f"Error: Could not switch to branch {branch}")
        return False

    # Get project metadata to find Google Photos album
    metadata_file = project_dir / "project.json"
    metadata = {}
    if metadata_file.exists():
        with open(metadata_file) as f:
            metadata = json.load(f)

    album_info = metadata.get("google_photos_album")
    if not album_info:
        print("No Google Photos album found for this project.")
        print("Falling back to local photo discovery...")
        return add_photos_fallback(project_name, project_dir)

    # Download photos from Google Photos album
    try:
        photos_client = ImgurClient()
        album_title = album_info["title"]

        print(f"Downloading photos from Google Photos album: {album_title}")
        downloaded_files = photos_client.download_album_photos(album_title, str(project_dir))

        if downloaded_files:
            print(f"Downloaded {len(downloaded_files)} photos from Google Photos")

            # Update project metadata
            existing_photos = set(metadata.get("photos", []))
            new_photos = [f.name for f in downloaded_files if f.name not in existing_photos]

            metadata["photos"] = list(existing_photos) + new_photos
            metadata["last_updated"] = datetime.now().isoformat()
            metadata["last_sync"] = {"date": datetime.now().isoformat(), "photos_downloaded": len(downloaded_files), "new_photos": len(new_photos)}

            with open(metadata_file, "w") as f:
                json.dump(metadata, f, indent=2)

            # Commit changes
            if new_photos:
                try:
                    subprocess.run(["git", "add", str(project_dir)], check=True)
                    subprocess.run(["git", "commit", "-m", f"Sync {len(new_photos)} new photos from Google Photos: {project_name}"], check=True)
                    print("New photos committed to git")
                except subprocess.CalledProcessError as e:
                    print(f"Warning: Could not commit photos: {e}")
            else:
                print("No new photos to commit")
        else:
            print("No photos found in Google Photos album")

    except Exception as e:
        print(f"Error downloading from Google Photos: {e}")
        print("Falling back to local photo discovery...")
        return add_photos_fallback(project_name, project_dir)

    return True


def add_photos_fallback(project_name, project_dir):
    """Fallback method to add photos from local sources"""
    # Look for new photos in common locations
    photo_sources = [Path.home() / "Downloads", Path.home() / "Pictures", Path("/tmp"), Path.cwd() / "tmp"]

    photos_found = []
    for source in photo_sources:
        if source.exists():
            for ext in ["*.jpg", "*.jpeg", "*.png", "*.JPG", "*.JPEG", "*.PNG"]:
                photos_found.extend(list(source.glob(ext)))

    if not photos_found:
        print("No photos found in common locations.")
        print(f"Manual option: Copy photos directly to {project_dir}/")
        return True

    print(f"Found {len(photos_found)} potential photos:")
    for i, photo in enumerate(photos_found[:10]):
        print(f"  {i + 1}. {photo.name} ({photo.stat().st_size // 1024}KB)")

    if len(photos_found) > 10:
        print(f"  ... and {len(photos_found) - 10} more")

    response = input(f"Copy all photos to {project_name}? (y/n): ")
    if response.lower() != "y":
        return True

    # Copy photos to project directory
    copied_count = 0
    for photo in photos_found:
        try:
            dest = project_dir / photo.name
            if not dest.exists():
                shutil.copy2(photo, dest)
                copied_count += 1
        except Exception as e:
            print(f"Warning: Could not copy {photo.name}: {e}")

    if copied_count > 0:
        print(f"Copied {copied_count} photos to project directory")

        try:
            subprocess.run(["git", "add", str(project_dir)], check=True)
            subprocess.run(["git", "commit", "-m", f"Add {copied_count} photos to {project_name}"], check=True)
            print("Photos committed to git")
        except subprocess.CalledProcessError as e:
            print(f"Warning: Could not commit photos: {e}")

    return True


def generate_blog_post(project_name):
    """Generate blog post using Claude analysis"""
    project_dir = get_project_dir(project_name)

    if not project_dir.exists():
        print(f"Error: Project {project_name} not found")
        return None

    # Get project metadata
    metadata_file = project_dir / "project.json"
    metadata = {}
    if metadata_file.exists():
        with open(metadata_file) as f:
            metadata = json.load(f)

    # Count photos
    photo_files = []
    for ext in ["*.jpg", "*.jpeg", "*.png", "*.JPG", "*.JPEG", "*.PNG"]:
        photo_files.extend(list(project_dir.glob(ext)))

    # Create blog post filename
    today = datetime.now()
    post_filename = f"{today.strftime('%Y-%m-%d')}-{project_name.replace('_', '-')}.md"
    post_path = Path("_posts") / post_filename

    # Generate blog post content using Claude
    claude_prompt = f"""
Create a blog post for a construction project documentation. 

Project: {project_name}
Photos: {len(photo_files)} images in {project_dir}
Start date: {metadata.get("start_date", "Unknown")}

Write a Jekyll blog post with:
1. Proper front matter (title, date, categories)
2. Introduction explaining the project
3. Photo gallery section with markdown image references
4. Conclusion with lessons learned or next steps

Use this format for images: ![Description](/{project_dir}/filename.jpg)

Make it personal and conversational, as this is for a personal blog.
Focus on the project process, challenges, and outcomes.
"""

    try:
        # Use Claude CLI to generate blog post
        result = subprocess.run(["claude", claude_prompt], capture_output=True, text=True, check=True)
        blog_content = result.stdout

        # Write blog post
        with open(post_path, "w") as f:
            f.write(blog_content)

        print(f"Generated blog post: {post_path}")
        return post_path

    except subprocess.CalledProcessError as e:
        print(f"Error generating blog post with Claude: {e}")
        # Fallback: create basic blog post template
        fallback_content = f"""---
title: "{project_name.replace("-", " ").replace("_", " ").title()}"
date: {today.strftime("%Y-%m-%d")}
categories: [construction, projects]
---

# {project_name.replace("-", " ").replace("_", " ").title()}

Project started on {metadata.get("start_date", "recently")} with {len(photo_files)} photos documented.

## Photos

"""

        # Add photo references
        for photo in sorted(photo_files):
            fallback_content += f"![{photo.stem}](/{project_dir}/{photo.name})\n\n"

        fallback_content += """
## Summary

Project documentation and photos captured above.

*Blog post generated automatically by project management system.*
"""

        with open(post_path, "w") as f:
            f.write(fallback_content)

        print(f"Generated basic blog post: {post_path}")
        return post_path


def finish_project(project_name):
    """Finish project and create PR"""
    project_dir = get_project_dir(project_name)

    if not project_dir.exists():
        print(f"Error: Project {project_name} not found")
        return False

    # Switch to project branch
    branch = get_project_branch(project_name)
    try:
        subprocess.run(["git", "checkout", branch], check=True)
    except subprocess.CalledProcessError:
        print(f"Error: Could not switch to branch {branch}")
        return False

    # Generate blog post
    blog_post = generate_blog_post(project_name)
    if not blog_post:
        return False

    # Update project metadata
    metadata_file = project_dir / "project.json"
    if metadata_file.exists():
        with open(metadata_file) as f:
            metadata = json.load(f)

        metadata["status"] = "completed"
        metadata["completion_date"] = datetime.now().isoformat()
        metadata["blog_post"] = str(blog_post)

        with open(metadata_file, "w") as f:
            json.dump(metadata, f, indent=2)

    # Commit blog post
    try:
        subprocess.run(["git", "add", str(blog_post), str(project_dir)], check=True)
        subprocess.run(["git", "commit", "-m", f"Complete project: {project_name} - add blog post"], check=True)
        print("Blog post committed")
    except subprocess.CalledProcessError as e:
        print(f"Error committing blog post: {e}")
        return False

    # Generate and create PR
    print("Creating pull request...")
    try:
        subprocess.run(["make", "generate-pr-content"], check=True)
        subprocess.run(["make", "create-pr"], check=True)
        print("Pull request created successfully!")
    except subprocess.CalledProcessError as e:
        print(f"Error creating PR: {e}")
        print("You can manually create a PR with:")
        print(f"  git push origin {branch}")
        print(f"  gh pr create --title 'Project: {project_name}' --body 'Construction project documentation'")

    return True


def main():
    if len(sys.argv) < 3:
        print("Usage: python3 project-manager.py {start|add-photos|finish} <project-name>")
        sys.exit(1)

    command = sys.argv[1]
    project_name = sys.argv[2]

    if command == "start":
        success = start_project(project_name)
    elif command == "add-photos":
        success = add_photos(project_name)
    elif command == "finish":
        success = finish_project(project_name)
    else:
        print(f"Unknown command: {command}")
        success = False

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
