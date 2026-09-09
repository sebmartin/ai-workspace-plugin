"""The user-global config file.

Not part of any workspace: one file per user, shared across CLI installs, with
its own format. Kept separate from workspace.py so that versioning a workspace
later does not drag the config along with it.
"""

import json
import os
from pathlib import Path


def get_config_dir() -> Path:
    """Get the user-global config directory shared across CLI installs.

    Uses AI_WORKSPACE_CONFIG_DIR if set (explicit override, primarily for tests),
    otherwise ${XDG_CONFIG_HOME:-~/.config}/ai-workspace/. The path is
    install-method-independent so a default_workspace set under one install
    (marketplace, inline, local-dev, Codex) is visible from all the others.
    """
    env_dir = os.environ.get("AI_WORKSPACE_CONFIG_DIR")
    if env_dir:
        return Path(env_dir).expanduser()

    xdg = os.environ.get("XDG_CONFIG_HOME")
    base = Path(xdg).expanduser() if xdg else Path.home() / ".config"
    return base / "ai-workspace"


def read_config() -> dict:
    """Read plugin config from the user-global config directory.

    Returns empty dict if config file doesn't exist.
    """
    config_path = get_config_dir() / "config.json"
    if not config_path.exists():
        return {}
    return json.loads(config_path.read_text())


def write_config(config: dict) -> None:
    """Write plugin config to the user-global config directory.

    Creates the config directory if it doesn't exist.
    """
    config_dir = get_config_dir()
    config_dir.mkdir(parents=True, exist_ok=True)
    config_path = config_dir / "config.json"
    config_path.write_text(json.dumps(config, indent=2) + "\n")
