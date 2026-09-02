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

_SCHEMA_MODULE = re.compile(r"^_?v\d+$")


def test_tool_surface_names_no_schema_version():
    """No tool reaches for a schema directly; they all go through the API.

    Parses the module rather than grepping lines, so a version that appears in
    prose is not mistaken for one that appears in code. Docstrings legitimately
    name things like my-thread-v1 when explaining a migration to the model.
    """
    import ast

    tree = ast.parse(SERVER.read_text())
    offenders = []

    def _flag(node, text):
        offenders.append(f"line {node.lineno}: {text}")

    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            if _SCHEMA_MODULE.search(node.module):
                _flag(node, f"from {node.module} import ...")
            for alias in node.names:
                if _SCHEMA_MODULE.search(alias.name):
                    _flag(node, f"from {node.module} import {alias.name}")
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if _SCHEMA_MODULE.search(alias.name):
                    _flag(node, f"import {alias.name}")
        elif isinstance(node, ast.Attribute) and _SCHEMA_MODULE.search(node.attr):
            _flag(node, f"...{node.attr}")
        elif isinstance(node, ast.Name) and _SCHEMA_MODULE.search(node.id):
            _flag(node, node.id)

    assert not offenders, (
        "mcp_server.py names a schema version in code. Call the threads API "
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


def test_every_module_in_a_schema_is_reachable_from_its_surface():
    """A schema ships no module its own __init__.py cannot reach.

    An unreachable module is either dead or filed in the wrong place, and
    both are invisible: the tests import it directly, so it passes CI while
    nothing in the product ever calls it. Written after this PR shipped four
    such modules, three of which belonged one PR later and one of which had
    been superseded by prose in a command reference.
    """
    import ast

    threads_dir = REPO / "lib" / "ai_workspace" / "threads"
    for vdir in sorted(threads_dir.glob("v*")):
        if not (vdir / "__init__.py").exists():
            continue
        present = {p.stem for p in vdir.glob("*.py")} - {"__init__"}

        def imports(mod, vdir=vdir, present=present):
            tree = ast.parse((vdir / f"{mod}.py").read_text())
            out = set()
            for node in ast.walk(tree):
                if not isinstance(node, ast.ImportFrom) or not node.module:
                    continue
                if vdir.name not in node.module.split("."):
                    continue
                tail = node.module.split(f".{vdir.name}")[-1].lstrip(".")
                if tail:
                    out.add(tail)
                out |= {a.name for a in node.names if a.name in present}
            return out & present

        seen, stack = set(), ["__init__"]
        while stack:
            mod = stack.pop()
            if mod in seen:
                continue
            seen.add(mod)
            stack.extend(imports(mod) - seen)

        assert not present - seen, (
            f"{vdir.name}/ ships {sorted(present - seen)}, which nothing "
            f"reachable from {vdir.name}/__init__.py imports"
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
    wherever a caller already holds a resolved thread. `create` is dispatched
    only the second way, because a thread being created has no marker to read
    and so is never resolved through `_for`.
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

def _threads_pkg() -> Path:
    return REPO / "lib" / "ai_workspace" / "threads"


def _names_defined_in(init: Path) -> set[str]:
    import ast

    names = set()
    for node in ast.parse(init.read_text()).body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(node.name)
        elif isinstance(node, ast.Assign):
            names.update(t.id for t in node.targets if isinstance(t, ast.Name))
    return names


def test_no_module_imports_a_name_from_the_package_that_imports_it():
    """Inside threads/, import sibling modules, never names from __init__.py.

    threads/__init__.py imports schema.py, which imports every schema, so a
    schema is loaded while the package is only partly initialised. Python
    resolves a submodule import at that point; an attribute of the package does
    not exist yet, and the failure is an ImportError at server start rather
    than anything a unit test would notice.
    """
    import ast

    pkg = _threads_pkg()
    init_only = _names_defined_in(pkg / "__init__.py") - {
        p.stem for p in pkg.iterdir()
    }
    offenders = []
    for module in sorted(pkg.rglob("*.py")):
        if module == pkg / "__init__.py":
            continue
        for node in ast.walk(ast.parse(module.read_text())):
            if isinstance(node, ast.ImportFrom) and node.module == "ai_workspace.threads":
                for alias in node.names:
                    if alias.name in init_only:
                        offenders.append(
                            f"{module.relative_to(REPO)}:{node.lineno} imports "
                            f"{alias.name!r}, which is defined in threads/__init__.py"
                        )
    assert not offenders, "\n  ".join(["import cycle waiting to happen:"] + offenders)


def test_a_schema_imports_only_the_one_directly_below_it():
    """v3 names v2, never v1, even for a function whose body is v1's.

    That is what keeps retiring a schema to one hop: move what its successor
    still uses into that successor, and nothing above it changes.
    """
    import ast

    pkg = _threads_pkg()
    versions = sorted(
        (int(p.name[1:]), p) for p in pkg.iterdir()
        if p.is_dir() and re.fullmatch(r"v\d+", p.name)
    )
    assert versions, "no schema packages found"

    offenders = []
    for n, (version, directory) in enumerate(versions):
        allowed = f"v{versions[n - 1][0]}" if n else None
        for module in sorted(directory.rglob("*.py")):
            for node in ast.walk(ast.parse(module.read_text())):
                if not isinstance(node, ast.ImportFrom) or not node.module:
                    continue
                m = re.search(r"ai_workspace\.threads\.(v\d+)", node.module)
                if not m or m.group(1) == f"v{version}":
                    continue
                if m.group(1) != allowed:
                    offenders.append(
                        f"{module.relative_to(REPO)}:{node.lineno} imports "
                        f"{m.group(1)}; v{version} may import only "
                        f"{allowed or 'nothing'}"
                    )
    assert not offenders, "\n  ".join(["schema import skipped a level:"] + offenders)
