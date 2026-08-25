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


def _script_metadata() -> str:
    """The PEP 723 block at the top of the server script."""
    text = (PLUGIN_ROOT / "skills" / "threads" / "scripts" / "mcp_server.py").read_text()
    start = text.index("# /// script")
    return text[start:text.index("# ///", start + 1)]


def test_the_script_declares_its_own_dependencies():
    """One place names them, so adding one is one line rather than six."""
    meta = _script_metadata()
    assert 'requires-python = ">=3.12"' in meta, meta
    assert "mcp>=2" in meta, meta


def test_both_launch_configs_read_that_declaration():
    """--script rather than --with, so neither manifest can drift from the script.

    Explicit rather than relying on uv auto-detecting the block, because
    --script also makes uv ignore any surrounding project.
    """
    codex_args = json.loads((PLUGIN_ROOT / ".mcp.json").read_text())["mcpServers"]["threads"]["args"]
    claude_args = json.loads(
        (PLUGIN_ROOT / ".claude-plugin" / "plugin.json").read_text()
    )["mcpServers"]["threads"]["args"]

    for args in (codex_args, claude_args):
        assert "--script" in args, args
        assert "--with" not in args, args
        assert args[-1].endswith("skills/threads/scripts/mcp_server.py"), args


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
