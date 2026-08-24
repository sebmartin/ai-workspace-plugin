"""The server actually starts and serves over stdio.

Everything else imports mcp_server and calls its functions, which passes
happily even when the module cannot run as a program. That gap is not
hypothetical: a refactor of this file once dropped its
`if __name__ == "__main__": mcp.run()` and the whole unit suite stayed green
while the server would not have started at all.

These launch it the way a client does — as a subprocess speaking JSON-RPC on
stdin and stdout — so a missing entry point, a broken import, or a tool that
fails to register is a test failure rather than a support ticket.
"""

import json
import selectors
import subprocess
import sys
import time
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
SERVER = REPO / "skills" / "threads" / "scripts" / "mcp_server.py"

# The path clients launch. .mcp.json and .claude-plugin/plugin.json both
# hardcode it, so it is part of the plugin's contract, not an implementation
# detail.
LAUNCH_PATH = "skills/threads/scripts/mcp_server.py"


def _talk(requests: list[dict], expect_ids: list[int], timeout: int = 60) -> dict:
    """Run the server as a client would and collect the replies we asked for.

    Requests go down a live pipe rather than being fed as one batch: the server
    exits on stdin EOF, and a tool call that is still running when that happens
    never answers. tools/list survives the batch form and tools/call does not,
    which is exactly the kind of difference this file exists to notice.

    Reads wait on a selector rather than blocking in readline, so `timeout`
    bounds the whole wait. A server that starts, answers the handshake and then
    goes quiet with its pipe still open is the case this file exists to catch,
    and a bare readline would block in it forever.
    """
    proc = subprocess.Popen(
        [sys.executable, str(SERVER)],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, bufsize=1, cwd=REPO,
    )
    replies: dict[int, dict] = {}
    try:
        for request in requests:
            proc.stdin.write(json.dumps(request) + "\n")
            proc.stdin.flush()

        selector = selectors.DefaultSelector()
        selector.register(proc.stdout, selectors.EVENT_READ)
        deadline = time.monotonic() + timeout
        while set(expect_ids) - set(replies) and time.monotonic() < deadline:
            if not selector.select(timeout=deadline - time.monotonic()):
                break
            line = proc.stdout.readline()
            if not line:
                break
            line = line.strip()
            if line.startswith("{"):
                try:
                    message = json.loads(line)
                except ValueError:
                    continue
                if "id" in message:
                    replies[message["id"]] = message
    finally:
        try:
            proc.stdin.close()
        except OSError:
            pass
        try:
            selector.close()
        except (NameError, OSError):
            pass
        proc.terminate()
        try:
            _, stderr = proc.communicate(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
            stderr = ""

    missing = set(expect_ids) - set(replies)
    if missing:
        pytest.fail(
            f"server never answered {sorted(missing)} — it may not have started.\n"
            f"got {sorted(replies)}\nstderr:\n{stderr[-2000:]}"
        )
    return replies


HANDSHAKE = [
    {"jsonrpc": "2.0", "id": 1, "method": "initialize",
     "params": {"protocolVersion": "2025-06-18", "capabilities": {},
                "clientInfo": {"name": "launch-test", "version": "0"}}},
    {"jsonrpc": "2.0", "method": "notifications/initialized"},
]


@pytest.fixture(scope="module")
def tools() -> dict:
    replies = _talk(HANDSHAKE + [{"jsonrpc": "2.0", "id": 2, "method": "tools/list"}], [2])
    return {t["name"]: t for t in replies[2]["result"]["tools"]}


def test_the_entry_point_exists():
    """The literal guard whose absence broke the server while tests passed."""
    assert 'if __name__ == "__main__":' in SERVER.read_text()


def test_server_starts_and_completes_a_handshake():
    replies = _talk(HANDSHAKE, [1])
    assert "serverInfo" in replies[1]["result"]


def test_server_lists_its_tools(tools):
    assert len(tools) >= 10, sorted(tools)


def test_every_tool_describes_itself(tools):
    """A tool with no description is one the model cannot choose correctly."""
    undocumented = [n for n, t in tools.items() if not t.get("description", "").strip()]
    assert not undocumented, undocumented


def test_a_tool_actually_runs(tmp_path):
    """End to end through the protocol, not just registered."""
    (tmp_path / "threads").mkdir()
    replies = _talk(HANDSHAKE + [{
        "jsonrpc": "2.0", "id": 3, "method": "tools/call",
        "params": {"name": "list_threads", "arguments": {"workspace_dir": str(tmp_path)}},
    }], [3])
    assert "No threads found" in json.dumps(replies[3]["result"])


def test_launch_path_matches_what_clients_are_told():
    """.mcp.json and the Claude manifest hardcode this path."""
    assert (REPO / LAUNCH_PATH).is_file()
    mcp_json = json.loads((REPO / ".mcp.json").read_text())
    assert LAUNCH_PATH in mcp_json["mcpServers"]["threads"]["args"]
    claude = json.loads((REPO / ".claude-plugin" / "plugin.json").read_text())
    assert LAUNCH_PATH in json.dumps(claude)
