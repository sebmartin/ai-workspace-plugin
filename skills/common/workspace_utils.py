"""Shared workspace utilities for thread and TODO management."""

import os
import re
import shutil
import sys
from pathlib import Path


def get_plugin_dir() -> Path:
    """
    Get plugin directory by walking up from workspace_utils.py location.

    workspace_utils.py is located in: <plugin>/skills/common/workspace_utils.py
    So we walk up 3 levels to reach the plugin root.
    """
    return Path(__file__).resolve().parent.parent.parent


def get_template_path(template_name: str) -> Path:
    """
    Get path to template file in plugin.

    Args:
        template_name: Name of the template file (e.g., "thread-template.md")

    Returns:
        Path to the template file in the plugin's templates/ directory
    """
    return get_plugin_dir() / "templates" / template_name


def get_workspace_dir() -> Path:
    """Get the workspace directory (current working directory)."""
    return Path.cwd()


def ensure_settings() -> None:
    """Ensure .claude/settings.json exists."""
    claude_dir = Path.cwd() / ".claude"
    settings_file = claude_dir / "settings.json"

    if settings_file.exists():
        return

    # Create .claude/ directory
    claude_dir.mkdir(parents=True, exist_ok=True)

    # Copy settings template from plugin
    template_path = get_template_path("settings.json.template")

    if not template_path.exists():
        error_exit(f"Settings template not found: {template_path}")

    # Copy template as-is (no variable substitution needed)
    shutil.copy(template_path, settings_file)

    print(f"✓ Created settings: {settings_file}")


def get_threads_dir() -> Path:
    """Get the threads directory within the workspace."""
    workspace_dir = get_workspace_dir()
    threads_dir = workspace_dir / "threads"

    # Auto-create if missing
    threads_dir.mkdir(parents=True, exist_ok=True)

    # Auto-create settings on first use
    ensure_settings()

    return threads_dir


def get_thread_dir(thread_name: str) -> Path:
    """Get the directory path for a specific thread."""
    return get_threads_dir() / thread_name


def validate_thread_exists(thread_name: str) -> bool:
    """Check if a thread exists (has a README.md file)."""
    thread_dir = get_thread_dir(thread_name)
    readme_path = thread_dir / "README.md"
    return readme_path.exists()


def error_exit(message: str, exit_code: int = 1) -> None:
    """Print an error message and exit with the specified code."""
    print(message, file=sys.stderr)
    sys.exit(exit_code)


def validate_thread_name(name: str) -> bool:
    """
    Validate that a thread name follows kebab-case conventions.

    Valid names:
    - Lowercase letters (a-z)
    - Numbers (0-9)
    - Hyphens (-)
    - Must start with a letter or number (not a hyphen)
    - Must end with a letter or number (not a hyphen)
    - No consecutive hyphens

    Returns:
        True if valid, False otherwise
    """
    if not name:
        return False

    # Check for valid kebab-case pattern
    # ^[a-z0-9]+ - Start with lowercase letter or number
    # ([a-z0-9-]*[a-z0-9]+)? - Optional middle section with hyphens, must end with letter/number
    # $ - End of string
    pattern = r'^[a-z0-9]+([a-z0-9-]*[a-z0-9]+)?$'

    if not re.match(pattern, name):
        return False

    # Check for consecutive hyphens
    if '--' in name:
        return False

    return True


def validate_thread_name_or_exit(name: str) -> None:
    """
    Validate thread name and exit with error message if invalid.

    Args:
        name: The thread name to validate
    """
    if not validate_thread_name(name):
        error_exit(
            f"Invalid thread name: '{name}'\n"
            f"Thread names must be kebab-case:\n"
            f"  - Lowercase letters (a-z), numbers (0-9), hyphens (-)\n"
            f"  - Must start and end with a letter or number\n"
            f"  - No consecutive hyphens\n"
            f"Examples: my-thread, project-2024, api-v2"
        )
