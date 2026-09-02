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


def test_every_schema_directory_is_registered():
    """SCHEMAS and the vN/ directories say the same thing.

    Nothing derives the registry from the filesystem, because importing by
    name is what lets a type checker follow dispatch into a schema. The cost
    is that adding or deleting a directory without editing the dict goes
    unnoticed, so this is the thing that notices.
    """
    from ai_workspace.threads import schema

    threads_dir = REPO / "lib" / "ai_workspace" / "threads"
    on_disk = {
        int(d.name[1:]) for d in threads_dir.iterdir()
        if d.is_dir() and re.fullmatch(r"v\d+", d.name)
    }
    assert on_disk == set(schema.SCHEMAS), (
        f"directories {sorted(on_disk)} but SCHEMAS registers "
        f"{sorted(schema.SCHEMAS)}"
    )


def test_every_registered_schema_declares_its_surface():
    """A schema's __all__ is its surface, and dispatch resolves against it.

    Checked through the registry rather than by globbing threads/v*, so a
    directory left behind by a branch switch, holding nothing but stale
    bytecode, is not mistaken for a schema.
    """
    from ai_workspace.threads import schema

    assert schema.SCHEMAS, "no schemas registered"
    for version, module in sorted(schema.SCHEMAS.items()):
        surface = getattr(module, "__all__", None)
        assert surface, f"schema {version} ({module.__name__}) declares no __all__"
        for op in surface:
            assert hasattr(module, op), (
                f"schema {version} lists {op!r} in __all__ but does not provide it"
            )


def _dispatched_operations() -> set[str]:
    """Every operation name the package hands off to a schema.

    Both call shapes count, and reading only one of them is how a guard stops
    guarding: `_for(..., "add_todo")` in the API, and `implementation(thread).op`
    wherever a caller already holds a resolved thread. note_restore and
    last_active are dispatched only the second way, so a list built from
    __all__ or from _for alone would never have covered them.
    """
    import ast

    names = set()
    for module in sorted((REPO / "lib" / "ai_workspace").rglob("*.py")):
        for node in ast.walk(ast.parse(module.read_text())):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "_for"
                and len(node.args) >= 3
                and isinstance(node.args[2], ast.Constant)
            ):
                names.add(node.args[2].value)
            elif (
                isinstance(node, ast.Attribute)
                and isinstance(node.value, ast.Call)
                and isinstance(node.value.func, ast.Name)
                and node.value.func.id == "implementation"
            ):
                names.add(node.attr)
    return names


def test_every_dispatched_operation_resolves_on_the_newest_schema():
    """Every operation handed to a schema exists on the newest one.

    Checked against max(SCHEMAS) rather than CURRENT_SCHEMA, because those
    diverge on purpose: CURRENT_SCHEMA is what the plugin creates and can lag
    what it can read. An older schema legitimately lacks newer operations, and
    refusing with NEEDS_MIGRATION is the intended behaviour there. The newest
    schema is the one that has to be complete.
    """
    from ai_workspace.threads import schema

    dispatched = _dispatched_operations()
    assert dispatched, "no dispatched operations found"

    newest = schema.SCHEMAS[max(schema.SCHEMAS)]
    missing = sorted(op for op in dispatched if not hasattr(newest, op))
    assert not missing, (
        f"dispatched {missing}, which schema {max(schema.SCHEMAS)} does not "
        f"implement"
    )


def test_dispatched_operations_are_declared_on_every_schema_that_has_them():
    """An operation a schema provides is named in its __all__.

    __all__ is the surface dispatch resolves against, so an operation that
    exists as a function but is not declared is reachable by accident today and
    silently dropped by the next schema that re-exports the declared set.
    """
    from ai_workspace.threads import schema

    undeclared = []
    for version, module in sorted(schema.SCHEMAS.items()):
        surface = set(getattr(module, "__all__", ()))
        for op in sorted(_dispatched_operations()):
            if hasattr(module, op) and op not in surface:
                undeclared.append(f"schema {version} provides {op!r} but omits it from __all__")
    assert not undeclared, "\n  ".join([""] + undeclared)
