"""Access to files inside the plugin directory."""

from workspace_utils import get_plugin_dir


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
