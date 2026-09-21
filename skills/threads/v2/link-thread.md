# Command: link one thread to another

Three fields in the README header hold the graph:

```
**Parent Thread**: None
**Child Threads**: None
**Related Threads**: None
```

Each entry is `[Title](../thread-name/README.md)`, several separated by
`, `, and the literal `None` when there are none. The title is the other
thread's README heading, falling back to its directory name.

No tool writes these. Edit the README directly, as you would Status or About.
The renderer owns `## Next steps` and nothing else, so a header edit is safe.

## What each link means

| The user says | Write on the current thread | Write on the other thread |
|---|---|---|
| link parent X | `**Parent Thread**` = X | add current to `**Child Threads**` |
| create child X | add X to `**Child Threads**` | `**Parent Thread**` = current |
| link related X | add X to `**Related Threads**` | add current to `**Related Threads**` |

A thread has at most one parent. Related links are symmetric. Both ends are
always written: a link recorded on one side only is worse than no link, because
it reads as complete from the side that has it.

If no thread name was given, list the threads, number them, ask which, and wait.
For `create child`, create the thread first, then link it.

## Look at the other thread before you write to it

This is the one operation that writes to a thread you have not resumed, so it is
the one place the rule against that does not apply. It is still someone else's
thread. Open its README before editing it.

**Check its schema.** A `schema-version` file at its root holding `2` means the
model you are working in. Anything else, or no file at all, means an older
schema, which is readable and never writable. Do not edit it. Say which thread
needs migrating and offer to migrate it, then link once it is converted. A one
sided link is not the fallback: it silently claims a relationship the other
thread does not know about.

The reason is not that an old README is hard to edit. It is that keeping every
retired schema writable means carrying all of them forever, and the whole point
of an older schema is that it costs nothing but the ability to read it.

**Read what is already there.** The field may be absent, may say `None`, may
already name this thread, or may name a different parent. Absent is normal on an
older README and you add the line to the header block. Already present is
nothing to do, and say so rather than writing a duplicate.

**A parent that is already set is a question for the user, not a decision for
you.** Name the current parent and ask. If they replace it, remove this thread
from the old parent's `**Child Threads**` in the same breath, which is a third
README to edit and is easy to forget. If that old parent is at an older schema,
the entry cannot be removed, so say that before the user chooses.

## Afterwards

Nothing else records a link. It is not a decision, not a todo, and not an
artifact. If the reason for the connection matters, it belongs in the session
log.
