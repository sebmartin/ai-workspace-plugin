"""Access to files inside the plugin directory."""

from pathlib import Path


def get_plugin_dir() -> Path:
    """Get plugin directory by walking up from this file's location.

    This module is <plugin>/lib/ai_workspace/plugin.py, so the root is three
    levels up.
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


def get_skill_file(relative_path: str) -> str:
    """Return the contents of a file from the plugin directory.

    Use this to read skill reference files (e.g. commands/save-thread.md)
    without needing direct filesystem access. Paths are resolved relative
    to the plugin root and must not escape it.

    Args:
        relative_path: Path relative to the plugin root (e.g., "skills/threads/commands/save-thread.md").
    """
    plugin_root = get_plugin_dir().resolve()
    target = (plugin_root / relative_path).resolve()
    try:
        target.relative_to(plugin_root)
    except ValueError:
        return "Error: Path escapes plugin directory."
    if not target.exists():
        return f"Error: File '{relative_path}' not found in plugin."
    if not target.is_file():
        return f"Error: '{relative_path}' is not a file."
    return target.read_text()
