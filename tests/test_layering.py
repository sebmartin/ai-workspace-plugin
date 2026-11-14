"""The tool surface does not know which schemas exist.

Adding a schema version should touch the new schema and the registry, nothing
else. The way that guarantee decays is a tool reaching for a version directly,
which reads as harmless in the diff that adds it and is a fork in the road by
the time there are three schemas.
"""

import json
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


def test_only_the_schema_being_created_is_inlined_in_the_skill():
    """SKILL.md carries the current schema's model; every older one has a file.

    The skill assumes what the plugin creates, so a session touching a current
    thread fetches nothing. That only holds while the inlined prose and
    CURRENT_SCHEMA agree, and shipping a new schema without moving the old
    section out to its own file would leave SKILL.md documenting the wrong
    default. Nothing else would notice, which is why this is a test rather
    than a note.
    """
    from ai_workspace.threads import schema

    prose = REPO / "skills" / "threads"
    current = prose / f"v{schema.CURRENT_SCHEMA}" / "model.md"
    assert not current.exists(), (
        f"{current} exists, but schema {schema.CURRENT_SCHEMA} is what the plugin "
        f"creates, so its model belongs inline in SKILL.md."
    )
    for version in schema.SCHEMAS:
        if version == schema.CURRENT_SCHEMA:
            continue
        older = prose / f"v{version}" / "model.md"
        assert older.is_file(), (
            f"schema {version} is still readable but has no {older}. A schema the "
            f"plugin no longer creates needs its own prose, moved out of SKILL.md "
            f"when it stopped being current."
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
    assert not undeclared, "\n  ".join(["", *undeclared])

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
    assert not offenders, "\n  ".join(["import cycle waiting to happen:", *offenders])


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
    assert not offenders, "\n  ".join(["schema import skipped a level:", *offenders])


def test_no_ordered_index_is_appended_to_by_id():
    """`idx.add` places a new entry by comparing ids, which is right for the
    three date-ordered kinds and wrong for todos, whose order is the priority
    the user set. `ORDERED` says "nothing may re-sort one" and nothing enforced
    it, so the claim was prose.

    Two assertions, because there are two ways in. A literal kind is the one a
    future call site would be written with. A variable kind reaches `idx.add`
    only through the indexing path, which is gated by `_FILE_KINDS`, so the
    second assertion is what keeps that gate shut.
    """
    import ast

    from ai_workspace.threads.v2 import index as idx
    from ai_workspace.threads.v2 import ops

    assert not set(ops._FILE_KINDS) & set(idx.ORDERED), (
        "an indexable kind is also an ordered one, so the indexing path can "
        "now reach idx.add with it"
    )

    offenders = []
    for path in sorted((REPO / "lib").rglob("*.py")):
        for node in ast.walk(ast.parse(path.read_text())):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            if not (isinstance(func, ast.Attribute) and func.attr == "add"):
                continue
            args = node.args[1:2]
            if not (args and isinstance(args[0], ast.Constant)):
                continue
            if args[0].value not in idx.ORDERED:
                continue
            retired = next((k.value for k in node.keywords if k.arg == "retired"), None)
            if len(node.args) > 3:
                retired = node.args[3]
            if not (isinstance(retired, ast.Constant) and retired.value is True):
                offenders.append(
                    f"{path.relative_to(REPO)}:{node.lineno}: add(..., "
                    f"{args[0].value!r}) without retired=True"
                )

    assert offenders == [], "\n".join(offenders)


def test_the_todo_link_rule_is_stated_the_same_way_in_every_file():
    """One rule, four files, and it diverged once with the suite green.

    `add_todo`'s docstring said to use an external URL whenever there was an
    issue or PR; the migration procedure said to link the session the item came
    from. Both matched a todo with nothing of its own, so one took a PR as its
    link and lost any statement of its own work. Nothing failed, because no
    test read the prose.
    """
    RULE = "record of this todo"
    SCHEME = "todos/YYYYMMDD-slug.md"
    states = ("active", "started", "parked", "done", "dropped")

    for rel in ("skills/threads/SKILL.md",
                "skills/threads/scripts/mcp_server.py",
                "skills/threads/v2/migrate-from-v1.md"):
        text = (REPO / rel).read_text()
        assert RULE in text, (
            f"{rel} no longer says a todo's link names the {RULE}. Every file "
            f"that states the rule says it the same way, or they drift apart "
            f"again."
        )

    for rel in ("skills/threads/SKILL.md", "skills/threads/scripts/mcp_server.py"):
        text = (REPO / rel).read_text()
        assert SCHEME in text, (
            f"{rel} no longer names {SCHEME} as the todo filename. The other "
            f"scheme this once held, ./todos/<id>.md, cannot be produced by a "
            f"caller: the id is minted inside the call, after the link has "
            f"already been validated."
        )

    server = SERVER.read_text()
    assert "`MISSING` for a `./` path with no file behind it" in server, (
        "add_todo's enumerated refusal codes no longer list MISSING. The codes "
        "paragraph is what a caller recovers from, so a refusal the body "
        "describes in prose but the list omits reads as unreachable."
    )

    template = (REPO / "templates" / "v2" / "todo-template.md").read_text()
    for state in states:
        assert state in template, (
            f"templates/v2/todo-template.md does not offer `{state}`. It lists "
            f"every state a todo can hold, because a reader editing the file by "
            f"hand has only this comment to go on."
        )


def test_every_tool_that_can_return_file_unchanged_documents_it():
    """A reply key the surface does not mention is a key nobody surfaces.

    `file_unchanged` says the index and an entry file now disagree, and
    nothing else reports it, so a tool that can return it and does not say so
    leaves the human never finding out.
    """
    import ast

    tree = ast.parse(SERVER.read_text())
    tools = {f.name: (ast.get_docstring(f) or "")
             for f in tree.body if isinstance(f, ast.FunctionDef)}
    ops = (REPO / "lib" / "ai_workspace" / "threads" / "v2" / "ops.py").read_text()
    assert '"file_unchanged"' in ops, (
        "ops.py no longer sets file_unchanged; drop this test with it."
    )
    for name in ("retire_todo", "retire_decision", "set_todo_state"):
        assert name in tools, f"{name} is no longer a tool on the surface"
        assert "file_unchanged" in tools[name], (
            f"{name} can return `file_unchanged` and its docstring does not "
            f"mention it. The docstring is the model-facing API, so an "
            f"assistant that has not read it will drop the key and the index "
            f"and the file stay silently disagreeing."
        )


def test_the_skill_describes_the_resume_this_plugin_returns():
    skill = (REPO / "skills" / "threads" / "SKILL.md").read_text()
    assert "## Working with a schema 2 thread" in skill
    assert "Print only Status and Next steps" not in skill
    assert "When the user says to work on something, set its state to `started`" not in skill
    for phrase in ("About, Status and Todos", "set_todo_state", "`started`",
                   "set_about", "recently", "up_next", "`summary:` and `keywords:`"):
        assert phrase in skill, phrase
    assert "## Next steps" not in skill
    assert "14 days" not in SERVER.read_text()
    assert "in full" in SERVER.read_text()
    assert "artifacts-starred.md" in skill and "star_artifact" in skill
    assert "star_dropped" in SERVER.read_text()
    assert "a standing instruction for this thread" not in skill
    assert "what a session needs in hand before it starts" in skill

    migrate =(REPO / "skills" / "threads" / "v2" / "migrate-from-v1.md").read_text()
    assert "## Todos" in migrate and "set_about" in migrate and "**Recently**" in migrate
    assert "`## Next steps`" not in migrate

    for manifest in (".claude-plugin/plugin.json", ".codex-plugin/plugin.json"):
        version = json.loads((REPO / manifest).read_text())["version"]
        assert tuple(int(n) for n in version.split(".")) >= (3, 2, 0), version


def test_writes_to_another_thread_go_through_the_thread_writer():
    """The skill sends cross-thread writes to an agent the plugin ships.

    Resuming the other thread in the main conversation is what loaded its
    context next to the active thread's, and a reference to an agent that is
    not shipped would leave the skill pointing at nothing.
    """
    from ai_workspace.text import split_frontmatter

    agent = REPO / "agents" / "thread-writer.md"
    meta, body = split_frontmatter(agent.read_text(), agent)
    assert meta["name"] == "thread-writer"
    assert meta["codex-mirror"] is False
    for tool in ("resume_thread", "get_skill_file", "save_session"):
        assert f"`{tool}`" in body, tool
        assert f"def {tool}(" in SERVER.read_text(), tool

    skill = (REPO / "skills" / "threads" / "SKILL.md").read_text()
    assert "`ai-workspace:thread-writer`" in skill
    assert "Never write to a thread you have not resumed" not in skill
    # The agent learns the current schema from SKILL.md, so it never names one
    # and nothing in it goes stale when CURRENT_SCHEMA moves.
    from ai_workspace.threads.schema import CURRENT_SCHEMA

    named = re.search(r"schema[`:\s]*\d", body, re.IGNORECASE) or f"`{CURRENT_SCHEMA}`" in body
    assert not named, "thread-writer names a schema number"
    assert f"**Schema {CURRENT_SCHEMA} is what this plugin creates" in skill
    assert f"## Working with a schema {CURRENT_SCHEMA} thread" in skill

    link = (REPO / "skills" / "threads" / "v2" / "link-thread.md").read_text()
    assert "the one operation that writes to a thread you have not resumed" not in link
    assert "The thread you started from stays current" in link


# Budgets the model must never be told. Quoting one invites it to reason about
# the figure instead of the payload, and the figure moves.
_BUDGETS = ["SESSION_BODY_BUDGET", "MEMORY_BUDGET"]


def test_no_budget_figure_reaches_the_model():
    from ai_workspace.threads.v2 import thread
    files = [p for p in (REPO / "skills").rglob("*") if p.is_file() and p.suffix in (".md", ".py")]
    for name in _BUDGETS:
        tokens = getattr(thread, name)
        chars = round(tokens * thread.CHARS_PER_TOKEN)
        for figure in {str(tokens), f"{tokens:,}", str(chars), f"{chars:,}"}:
            pattern = rf"(?<![\d,]){re.escape(figure)}(?![\d,])"
            hits = [str(p.relative_to(REPO)) for p in files if re.search(pattern, p.read_text())]
            assert not hits, f"{name} ({figure}) is model-facing in {hits}"


def test_every_schema_provides_the_reads_resume_relies_on():
    from ai_workspace.threads import schema

    for version, module in schema.SCHEMAS.items():
        assert {"links", "about"} <= set(module.__all__), f"schema {version}"


_OUTSIDE_THE_THREAD = ("ai_workspace.workspace", "ai_workspace.config")


def test_no_schema_module_reaches_outside_its_own_thread():
    """A schema reads one thread. Anything spanning threads is done above it."""
    import ast

    problems = []
    for version in ("v1", "v2"):
        for path in sorted((_threads_pkg() / version).rglob("*.py")):
            rel = path.relative_to(REPO)
            for node in ast.walk(ast.parse(path.read_text())):
                if isinstance(node, ast.ImportFrom):
                    mod = node.module or ""
                    named = {mod, *(f"{mod}.{a.name}" for a in node.names)}
                    if named & set(_OUTSIDE_THE_THREAD):
                        problems.append(f"{rel}:{node.lineno} imports {mod}")
                elif isinstance(node, ast.Import):
                    for a in node.names:
                        if a.name in _OUTSIDE_THE_THREAD:
                            problems.append(f"{rel}:{node.lineno} imports {a.name}")
                elif isinstance(node, ast.Attribute):
                    if node.attr == "workspace":
                        problems.append(f"{rel}:{node.lineno} reads .workspace")
                    elif node.attr == "parent" and (
                        (isinstance(node.value, ast.Name) and node.value.id == "thread_dir")
                        or (isinstance(node.value, ast.Attribute) and node.value.attr == "dir")
                    ):
                        problems.append(f"{rel}:{node.lineno} leaves the thread directory")
    assert not problems, "\n  ".join(["", *problems])
