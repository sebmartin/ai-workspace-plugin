# Deep Review — PR #33

`ordered-todo-list` → `release/3`, head `fdf32d4`. 22 files, ~1917 changed lines.

**10 findings: 1 blocker, 3 robustness, 6 cleanup. All CONFIRMED.** 1 refuted and dropped.

## Coverage, and what this review is missing

This run degraded to the skill's documented **solo fallback**, so treat it as partial:

| Reviewer | Result |
|---|---|
| codex `/review` | skipped, reported unusable by the operator |
| claude `/code-review high` | ran, 6 candidates (late write after a trust warning) |
| claude `/security-review` | **killed at 600s**, produced a 163-byte stub, no findings |
| data-integrity module | **stalled at 600s, three attempts**, no output |
| testing module | ran, 6 candidates |

Consequences worth stating plainly:

- **The untrusted-input surface the scout flagged went uncovered.** No security pass completed. I had separately probed the path-containment guard earlier (case variants, surrounding whitespace, traversal, absolute, `~`, `file://`, scheme look-alikes) and found it sound, but that is my own prior work, not an independent read.
- **No cross-tool agreement signal** for 8 of the 10 findings, since only two reviewers finished. Lone-source findings were verified harder to compensate; every one below was re-opened against the code and most were reproduced with a probe.
- **The persistence surface was still covered**, despite the data-integrity module never finishing: findings 1, 3 and 4 are data-integrity-shaped and came from the two reviewers that did complete.

---

## 🔴 Blocker

🔴 **A backslash in a todo title bricks the thread** — `lib/ai_workspace/threads/v2/render.py:92` · testing · **CONFIRMED**

**Mechanism.** Line 92 is `text = pattern.sub(section, text, count=1)`. `section` embeds each entry's user-supplied title via `e.render()`. `Pattern.sub` processes backslash escapes in a *string* replacement, so the title's backslashes are read as regex replacement syntax. The write guard `idx.unrepresentable` only checks the rendered line parses back through `_LINE_RE`, which is indifferent to backslashes, so it returns `None` for all of these. The guard validates survival of the **parser**, never of the **renderer**.

**Failure scenario.** Verified by probe. `add_todo(title=r"Fix the \d{4} regex", link="./todos/x.md")` → `unrepresentable()` returns `None`, `idx.write` persists the entry, then `render.render` raises `PatternError: bad escape \d`. The todo is in the index and the README is stale. It is then **persistent**: a second, innocent `add_todo` raises the same error, because every write re-renders from the index that still holds the title. The thread is unwritable by every tool until someone hand-edits the index, which SKILL.md forbids. Variants: `C:\temp\x` → `PatternError`; `see \g<id>` → `IndexError`; and `Escape the \n here` does **not** raise, it silently renders a real newline into the README, splitting the entry so `_LINE_RE` no longer matches it.

**Fix.** Pass a function so escape processing never happens: `pattern.sub(lambda _: section, text, count=1)`. Then extend the guard or add a render-side test so the invariant is "survives write **and** render" rather than "parses back".

---

## 🟠 Robustness

🟠 **`add_todo(state="started")` leaves two todos started** — `lib/ai_workspace/threads/v2/ops.py:369` · correctness · **CONFIRMED**

**Mechanism.** `add_todo` builds the `Entry` directly and implements half the invariant (`at = 0 if state == todos_mod.STARTED else len(entries)`, ops.py:359). It never calls `todos_mod.start`, which is what clears `STARTED` from whatever held it (todos.py:123-126). `set_state` routes through `start` and does enforce it.

**Failure scenario.** Verified by probe: two successive `add_todo(state="started")` calls leave `[('second','started'), ('first','started')]`. todos.py:119-121 states the invariant being broken: "Exactly one, because the state names what is being worked on now. A second one leaves the label meaning nothing."

**Fix.** Call `todos_mod.start(entries, todo_id)` when `state == STARTED` instead of relying on the `at = 0` placement, so one path owns the invariant. Add the two-started case to the `add_todo` tests, which cover only the `set_todo_state` path today.

---

🟠 **The migration audit reports a URL todo link as a lost file** — `lib/ai_workspace/threads/migrate.py:153` · correctness, testing · **CONFIRMED** (independent agreement, 2 sources)

**Mechanism.** migrate.py:150-154 loops `for kind in idx.TYPES` (including `todos`) and tests `(converted / entry.link.lstrip("./")).exists()`. An http(s) URL is an explicitly blessed todo link as of this PR (ops.py:351; the tests call it "the documented use") but it is not a path, so the test always fails. This is the same false-positive class the `ORDERED` exemption two lines below exists to avoid, with the consequence its own comment names: "which is how a gate stops being read."

**Failure scenario.** Verified by probe. A thread migrated exactly as `skills/threads/v2/migrate-from-v1.md` instructs, whose v1 Next steps said to chase an upstream issue, audits as `{"clean": false, "dangling": {"todos": ["https://github.com/owner/repo/issues/16"]}}`. `audit_migration` is the gate that tells the user whether it is safe to delete the original thread, so a false `clean: false` either stalls a correct migration or trains the user to ignore the audit.

**Fix.** Skip the existence test when the link carries a scheme, reusing the writer's own predicate: `if link.lower().startswith(("http://", "https://")): continue`. Better, lift that predicate into one shared helper so the writer's definition of "external" and the auditor's cannot drift. Pre-existing at the PR base (where `add_todo` had no link gate), but this diff edits that loop and is what blessed URL links, so it is in scope.

---

🟠 **A repeated id in a legacy window becomes a permanent duplicate entry** — `lib/ai_workspace/threads/v2/index.py:178` · data-integrity · **CONFIRMED**

**Mechanism.** `_window_first` builds `first = [by_id[i] for i in named if i in by_id]` without de-duplicating `named`, then appends everything not in `set(named)`. A block naming one id twice yields the same `Entry` twice. Indexes are rendered wholesale rather than edited, so the next write persists the duplicate line, and the docstring's "The next write makes it permanent" is true of the duplicate too.

**Failure scenario.** Reachable from data already on disk: the removed `idx.set_window` stored the caller's list verbatim (`windows[section] = ids`) and validated only that each id was *known*, never that they were distinct. So `set_window(..., ["a", "a"])` wrote `next_steps: [a, a]`. Reading that index returns entry `a` twice; the next write produces two identical lines for one todo, and retiring one leaves the other.

**Fix.** `named = list(dict.fromkeys(i.strip() for i in found.group(1).split(",") if i.strip()))`. Add a read test over a block with a repeated id asserting the entry appears once.

---

## 🟡 Cleanup

🟡 **The README never mentions parked todos unless nothing is active** — `lib/ai_workspace/threads/v2/render.py:51` · **CONFIRMED**

**Mechanism.** The parked note is an `elif` guarded by `not shown`, so it fires only when nothing active is displayed. `next_steps_body`'s own docstring promises the opposite: "Says how much it is not showing, whether that is todos below the window or todos that were parked, because a section that hides the rest in silence is worse for the person reading it than one that points at the index."

**Failure scenario.** Verified by probe: three active and ten parked renders the three with no mention of the ten, which is exactly the silence the docstring argues against. Mitigated, not hidden: `resume` reports both counts and lists the parked entries (thread.py:110-129), so only the README view loses it.

**Fix.** Make the two notes independent rather than exclusive, or narrow the docstring. Prefer the former; the docstring is making the better argument.

---

🟡 **`save_session`'s docstring still promises the stub this PR deleted** — `lib/ai_workspace/threads/v2/ops.py:537` · **CONFIRMED**

**Mechanism.** It reads "A session that dies before this still leaves its stub and a record of what it touched." This diff removed `STUB_MARKER`, `note_created` and the `## Created during this session` section, and split `ensure_stub` into `next_id` and `ensure_indexed`. SKILL.md and session.py were updated; this copy was missed.

**Failure scenario.** A reader, human or agent, looks on disk for a recoverable stub that nothing writes. No runtime consequence.

**Fix.** Replace it with what now happens: `session.save` writes the file before indexing it, so a failure leaves no dangling index entry.

---

🟡 **`ORDERED` claims an invariant nothing enforces** — `lib/ai_workspace/threads/v2/index.py:37` · **CONFIRMED**

**Mechanism.** The comment asserts "Nothing may re-sort one", but `add` (index.py:220-236) is an ordinary public function accepting `kind="todos", retired=False`, and 12 call sites across `tests/test_schema_v2.py` and `tests/test_migrate.py` do exactly that. **Correcting the reporting module:** `add` does *not* date-sort the existing list. It scans back from the end while `entries[at-1].id > entry.id` and inserts there, explicitly "rather than silently reordering lines nobody asked about" (index.py:228-230). Misuse misplaces the new entry; it does not destroy the order.

**Failure scenario.** A future operation or migration helper appends a todo with `idx.add(thread.dir, "todos", entry)` instead of the read/insert/write at ops.py:358-377. The todo lands at a position decided by id comparison against a list that is not in id order, and nothing objects, because the suite itself uses that call shape for live todos.

**Fix.** A layering guard in the style of `tests/test_layering.py`: walk `lib/ai_workspace/**/*.py` with `ast` and assert no `idx.add`/`index.add` call passes a literal in `idx.ORDERED` as `kind` without `retired=True`. AGENTS.md already asks for guards to be verified by breaking them.

---

🟡 **The README-equals-projection invariant test passes vacuously** — `tests/test_v2_ops.py:987` · **CONFIRMED**

**Mechanism.** It extracts the section as `split("## Next steps\n\n")[1].split("\n\n")[0]`, the first paragraph only, and uses exactly two todos. `next_steps_body` appends its hidden and parked notes as a *second* paragraph (render.py:49-54), so with two todos there is no tail and the comparison is trivially satisfied.

**Failure scenario.** A change to how the hidden-count tail is composed, dropping it, or rendering it into the README but not the projection, leaves the two out of step for any thread with more than five todos. The one test that exists to catch that stays green, because it never looks at the paragraph where the divergence lives.

**Fix.** Slice to the next `^## ` heading instead of the next blank line, and parametrize over two active todos, six active todos (exercises the "more in todos" tail), and three parked with none active (exercises the parked tail).

---

🟡 **The amend path's restore-on-refusal is untested** — `lib/ai_workspace/threads/v2/ops.py:188-192` · **CONFIRMED**

**Mechanism.** The amend mutates the live entry in place, checks representability, and restores on failure. The restore is correct but unexercised: the only rejected-amendment test trips the length cap at ops.py:169-170, which returns before any entry is touched.

**Failure scenario.** Reordering those four lines so the write precedes the check, or adding a second mutated field without a matching restore, writes an unparseable line into `artifacts-index.md` during an amend, losing the entry on the next read. Nothing fails.

**Fix.** Index an artifact with a good description, re-index with a description containing a line break, and assert UNREPRESENTABLE, the description unchanged, and the index file byte-identical to before the call.

---

🟡 **No test covers UNREPRESENTABLE for a filename-derived link** — `lib/ai_workspace/threads/v2/ops.py:210-215` · **CONFIRMED**

**Mechanism.** For an indexed file the link comes from the filename, so the realistic breaker is a name containing `)` or `]`, which macOS and browsers produce by default. Every UNREPRESENTABLE test uses a todo title, a todo link or an artifact description; none uses a filename. **Verified correct today:** a probe of `index_file("./artifacts/Screenshot (1).png")` returns `{"error": "UNREPRESENTABLE", "detail": "link cannot be read back from a line"}`, writes no index file, and leaves the index empty. This is a missing regression test, not a live bug.

**Failure scenario.** If the check moved below `idx.add`, or a later kind routed around it, that line's `[^)]*` link group would stop at the first `)` and the tail would fail to parse, so the entry would vanish from the index on the next read. The guard preventing this has no test naming it.

**Fix.** In `TestIndexDirectory`, create `./artifacts/Screenshot (1).png` beside a well-named file; assert `index_file` returns UNREPRESENTABLE with `"link"` in the detail and leaves the index empty, and that `index_directory` skips it while still indexing its neighbour.

---

## Refuted and dropped

**`set_todo_state` documents `active` as unpark-only** (`skills/threads/scripts/mcp_server.py:255`, claude-code-review). The docstring states plainly that `started` "sends it to the top of the list and clears the label from whatever held it before", which covers starting a parked todo. A probe confirms parked → started moves the entry to position 0 with state `started`. The documentation is accurate.

**Suppressed trivial nits: 0.**

One self-restrained non-finding from `claude-code-review` is worth keeping on file rather than acting on: `log_decision` tests `index_file`'s result with `startswith("Error:")`, which no longer matches any reachable refusal from that call, since they are all JSON now and the one bare-string path (`render.blocked`) is already called earlier. Dead defensive code, worth tidying only if you touch the function.
