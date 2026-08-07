"""Regression tests for Codex plugin packaging constraints."""

import json
from pathlib import Path


PLUGIN_ROOT = Path(__file__).resolve().parent.parent


def test_codex_manifest_uses_companion_mcp_file():
    manifest = json.loads((PLUGIN_ROOT / ".codex-plugin" / "plugin.json").read_text())

    assert manifest["skills"] == "./skills/"
    assert manifest["mcpServers"] == "./.mcp.json"
    assert (PLUGIN_ROOT / ".mcp.json").is_file()


def test_codex_mcp_config_uses_relative_paths():
    mcp_config = json.loads((PLUGIN_ROOT / ".mcp.json").read_text())
    threads_server = mcp_config["mcpServers"]["threads"]
    serialized = json.dumps(mcp_config)

    assert "type" not in threads_server
    assert threads_server["cwd"] == "."
    assert "skills/threads/scripts/mcp_server.py" in threads_server["args"]
    assert "${PLUGIN_ROOT}" not in serialized
    assert "${PLUGIN_DATA}" not in serialized
    assert "${CLAUDE_PLUGIN_ROOT}" not in serialized
    assert "${CLAUDE_PLUGIN_DATA}" not in serialized


def test_both_launch_configs_require_mcp_2x():
    """The server imports mcp.server.mcpserver, which only exists on mcp>=2."""
    codex_args = json.loads((PLUGIN_ROOT / ".mcp.json").read_text())["mcpServers"]["threads"]["args"]
    claude_args = json.loads(
        (PLUGIN_ROOT / ".claude-plugin" / "plugin.json").read_text()
    )["mcpServers"]["threads"]["args"]

    for args in (codex_args, claude_args):
        assert "mcp>=2" in args, args


def test_manifest_versions_stay_in_sync():
    claude = json.loads((PLUGIN_ROOT / ".claude-plugin" / "plugin.json").read_text())
    codex = json.loads((PLUGIN_ROOT / ".codex-plugin" / "plugin.json").read_text())

    assert claude["version"] == codex["version"]


def test_codex_manifest_has_required_interface_metadata():
    manifest = json.loads((PLUGIN_ROOT / ".codex-plugin" / "plugin.json").read_text())
    interface = manifest["interface"]

    for field in (
        "displayName",
        "shortDescription",
        "longDescription",
        "developerName",
        "category",
    ):
        assert isinstance(interface[field], str)
        assert interface[field].strip()
    assert isinstance(interface["capabilities"], list)
    assert interface["defaultPrompt"]


def test_every_top_level_skill_directory_has_skill_manifest():
    skills_root = PLUGIN_ROOT / "skills"
    skill_dirs = [path for path in skills_root.iterdir() if path.is_dir()]

    assert skill_dirs
    for skill_dir in skill_dirs:
        assert (skill_dir / "SKILL.md").is_file(), skill_dir.name
