#!/usr/bin/env python3
"""
Jekyll Site CLI - Command line interface for site management

Provides unified access to all site management commands including:
- Construction project workflows
- Photo management
- Imgur integration
- Development tools
"""

import click
import sys
from pathlib import Path

# Add scripts directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from clients.imgur_client import ImgurClient, setup_imgur_auth  # noqa: E402
from project.project_manager import (  # noqa: E402
    start_project,
    add_photos,
    finish_project,
    get_project_branch,
    get_project_dir,
)


@click.group()
@click.version_option(version="1.0.0")
def cli():
    """Jekyll Site Management CLI

    Unified command line interface for managing the Jekyll site,
    construction projects, photo workflows, and development tasks.
    """
    pass


@cli.group()
def project():
    """Construction project management commands."""
    pass


@project.command("start")
@click.argument("name")
@click.option(
    "--enable-photos",
    is_flag=True,
    default=False,
    help="Enable photo album integration with Imgur",
)
def start_project_cmd(name, enable_photos):
    """Start a new construction project.

    Creates a new git branch, project directory, and optionally
    sets up photo album integration.

    NAME: Project name (e.g., 'deck-repair', 'window-replacement')
    """
    click.echo(f"Starting construction project: {name}")

    if enable_photos:
        click.echo("Photo integration enabled")
        # Set environment variable for project_manager
        import os

        os.environ["ENABLE_PHOTO_MONITORING"] = "true"

    try:
        start_project(name)
        branch = get_project_branch(name)
        project_dir = get_project_dir(name)

        click.echo(f"✅ Project '{name}' started successfully!")
        click.echo(f"   Branch: {branch}")
        click.echo(f"   Directory: {project_dir}")

        if enable_photos:
            click.echo("   Photo monitoring: Enabled")

    except Exception as e:
        click.echo(f"❌ Error starting project: {e}", err=True)
        sys.exit(1)


@project.command("add-photos")
@click.argument("name")
def add_photos_cmd(name):
    """Add photos to an existing project.

    Downloads new photos from the project's album and organizes
    them in the project directory.

    NAME: Project name
    """
    click.echo(f"Adding photos to project: {name}")

    try:
        add_photos(name)
        click.echo(f"✅ Photos added to project '{name}' successfully!")

    except Exception as e:
        click.echo(f"❌ Error adding photos: {e}", err=True)
        sys.exit(1)


@project.command("finish")
@click.argument("name")
def finish_project_cmd(name):
    """Finish a project and generate blog post.

    Analyzes project photos, generates a blog post with AI assistance,
    and creates a pull request for review.

    NAME: Project name
    """
    click.echo(f"Finishing project: {name}")

    try:
        finish_project(name)
        click.echo(f"✅ Project '{name}' finished successfully!")
        click.echo("   Blog post generated and PR created for review")

    except Exception as e:
        click.echo(f"❌ Error finishing project: {e}", err=True)
        sys.exit(1)


@project.command("status")
@click.argument("name")
def project_status_cmd(name):
    """Show status of a project.

    Displays project branch, directory, and photo information.

    NAME: Project name
    """
    branch = get_project_branch(name)
    project_dir = get_project_dir(name)

    click.echo(f"Project: {name}")
    click.echo(f"Branch: {branch}")
    click.echo(f"Directory: {project_dir}")
    click.echo(f"Directory exists: {project_dir.exists()}")

    if project_dir.exists():
        photos = list(project_dir.glob("*.jpg")) + list(project_dir.glob("*.png"))
        click.echo(f"Photos: {len(photos)} files")


@cli.group()
def imgur():
    """Imgur API integration commands."""
    pass


@imgur.command("setup")
def imgur_setup_cmd():
    """Set up Imgur API authentication.

    Interactive setup for Imgur API credentials and authentication.
    """
    click.echo("Setting up Imgur API integration...")

    try:
        setup_imgur_auth()
        click.echo("✅ Imgur API setup completed successfully!")

    except Exception as e:
        click.echo(f"❌ Error setting up Imgur: {e}", err=True)
        sys.exit(1)


@imgur.command("test")
def imgur_test_cmd():
    """Test Imgur API connection.

    Verifies that Imgur API credentials are working correctly.
    """
    click.echo("Testing Imgur API connection...")

    try:
        client = ImgurClient()
        if client.authenticate():
            click.echo("✅ Imgur API connection successful!")
        else:
            click.echo("❌ Imgur API authentication failed", err=True)
            sys.exit(1)

    except Exception as e:
        click.echo(f"❌ Error testing Imgur connection: {e}", err=True)
        sys.exit(1)


@imgur.command("projects")
def imgur_projects_cmd():
    """List construction projects from Imgur.

    Shows all albums and images tagged with construction projects.
    """
    click.echo("Fetching construction projects from Imgur...")

    try:
        client = ImgurClient()
        if not client.authenticate():
            click.echo("❌ Failed to authenticate with Imgur", err=True)
            sys.exit(1)

        projects = client.get_construction_projects()

        if not projects:
            click.echo("No construction projects found")
            return

        click.echo(f"Found {len(projects)} project(s):")
        for project_name, data in projects.items():
            click.echo(f"  📁 {project_name}")
            click.echo(f"     Album: {data.get('album_title', 'N/A')}")
            click.echo(f"     Images: {len(data.get('images', []))}")

    except Exception as e:
        click.echo(f"❌ Error fetching projects: {e}", err=True)
        sys.exit(1)


@cli.group()
def dev():
    """Development and maintenance commands."""
    pass


@dev.command("lint")
@click.option("--fix", is_flag=True, help="Auto-fix formatting issues")
def lint_cmd(fix):
    """Run code linting and formatting.

    Checks Python code quality using flake8 and black.
    """
    import subprocess

    if fix:
        click.echo("Running code formatter (black)...")
        result = subprocess.run(["black", "scripts/", "tests/", "--line-length=88"])
        if result.returncode == 0:
            click.echo("✅ Code formatting completed")
        else:
            click.echo("❌ Code formatting failed", err=True)
            sys.exit(1)

    click.echo("Running linter (flake8)...")
    result = subprocess.run(
        [
            "flake8",
            "scripts/",
            "tests/",
            "--max-line-length=88",
            "--extend-ignore=E501,E203,E251,E302,E131,E128,E127",
        ]
    )

    if result.returncode == 0:
        click.echo("✅ Code linting passed")
    else:
        click.echo("❌ Code linting failed", err=True)
        sys.exit(1)


@dev.command("test")
@click.option("--coverage", is_flag=True, help="Run with coverage report")
def test_cmd(coverage):
    """Run the test suite.

    Executes all unit tests for the photo management system.
    """
    import subprocess

    cmd = ["python", "-m", "pytest", "tests/", "-v"]

    if coverage:
        cmd.extend(["--cov=scripts", "--cov-report=html", "--cov-report=term"])

    click.echo("Running test suite...")
    result = subprocess.run(cmd)

    if result.returncode == 0:
        click.echo("✅ All tests passed")
        if coverage:
            click.echo("Coverage report generated in htmlcov/index.html")
    else:
        click.echo("❌ Some tests failed", err=True)
        sys.exit(1)


@dev.command("clean")
def clean_cmd():
    """Clean up build artifacts and test files.

    Removes temporary files, test artifacts, and build outputs.
    """
    import shutil
    from pathlib import Path

    click.echo("Cleaning build artifacts...")

    # Remove Jekyll build artifacts
    for path in ["_site", ".jekyll-cache", ".jekyll-metadata"]:
        if Path(path).exists():
            if Path(path).is_dir():
                shutil.rmtree(path)
            else:
                Path(path).unlink()
            click.echo(f"  Removed {path}")

    # Remove Python cache
    for path in Path(".").rglob("__pycache__"):
        shutil.rmtree(path)
        click.echo(f"  Removed {path}")

    # Remove test artifacts
    for pattern in ["*test-project*"]:
        for path in Path("assets/images").glob(pattern):
            if path.is_dir():
                shutil.rmtree(path)
            else:
                path.unlink()
            click.echo(f"  Removed {path}")

        for path in Path("_posts").glob(pattern):
            path.unlink()
            click.echo(f"  Removed {path}")

    # Remove coverage reports
    if Path("htmlcov").exists():
        shutil.rmtree("htmlcov")
        click.echo("  Removed htmlcov")

    if Path(".coverage").exists():
        Path(".coverage").unlink()
        click.echo("  Removed .coverage")

    click.echo("✅ Cleanup completed")


if __name__ == "__main__":
    cli()
