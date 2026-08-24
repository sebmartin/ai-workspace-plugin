"""The tool surface does not know which schemas exist.

Adding a schema version should touch the new schema and the registry, nothing
else. The way that guarantee decays is a tool reaching for a version directly,
which reads as harmless in the diff that adds it and is a fork in the road by
the time there are three schemas.
"""

import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SERVER = REPO / "skills" / "threads" / "scripts" / "mcp_server.py"
sys.path.insert(0, str(REPO / "lib"))

_VERSION_REF = re.compile(r"\bv\d+\b|\b_v\d+\w*\b")


def test_tool_surface_names_no_schema_version():
    offenders = [
        f"{n}: {line.strip()}"
        for n, line in enumerate(SERVER.read_text().splitlines(), 1)
        if _VERSION_REF.search(line)
    ]
    assert not offenders, (
        "mcp_server.py names a schema version directly. Call the threads API "
        "instead, which resolves the schema itself:\n  " + "\n  ".join(offenders)
    )


def test_every_registered_schema_declares_its_surface():
    """A schema's __all__ is its surface, and dispatch resolves against it.

    Checked through the registry rather than by globbing threads/v*, so a
    directory left behind by a branch switch, holding nothing but stale
    bytecode, is not mistaken for a schema.
    """
    from ai_workspace.threads import _schema

    assert _schema.SCHEMAS, "no schemas registered"
    for version, module in sorted(_schema.SCHEMAS.items()):
        surface = getattr(module, "__all__", None)
        assert surface, f"schema {version} ({module.__name__}) declares no __all__"
        for op in surface:
            assert hasattr(module, op), (
                f"schema {version} lists {op!r} in __all__ but does not provide it"
            )


def test_every_public_thread_operation_resolves_on_the_current_schema():
    """Each op the threads API exposes has an implementation to hand off to.

    Catches the accidental omission: an operation added to one schema and never
    re-exported by its successor, which would otherwise show up as a silent
    refusal rather than a failure.
    """
    from ai_workspace import threads
    from ai_workspace.threads import _schema

    current = _schema.SCHEMAS[_schema.CURRENT_SCHEMA]
    # Operations that act on archive/ rather than on one thread take no schema.
    collection_ops = {
        "restore", "list_archived_threads", "inspect_archive",
        "purge_archive_tmp", "list_threads", "validate_thread_name",
    }
    dispatched = [op for op in threads.__all__ if op not in collection_ops]
    assert dispatched, "no dispatched operations found"
    missing = [op for op in dispatched if not hasattr(current, op)]
    assert not missing, (
        f"threads exposes {missing} but schema {_schema.CURRENT_SCHEMA} "
        f"does not implement them"
    )
