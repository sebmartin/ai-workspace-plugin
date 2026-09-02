# Command: archive, restore, list archived

Archiving moves a thread out of the way. Nothing is compressed and nothing is deleted.

## Archive

`archive_thread(workspace_dir, thread_name)` moves `threads/{name}` to `archive/{name}`.

Confirm with the user first. Archiving is reversible, but it removes the thread from
`list_threads`, so it should not be a surprise.

## Restore

`restore_thread(workspace_dir, thread_name)` moves it back. Takes the thread's own name,
the same one it had before.

A thread is either active or archived, never both, so nothing collides and nothing is
overwritten. If both `threads/{name}` and `archive/{name}` somehow exist, the move refuses
rather than merging them, and the user has to say which one to keep.

## List

`list_archived_threads(workspace_dir)` shows what is in `archive/`.

## Archived threads are read-only

An archived thread keeps its shape, so it looks exactly like a live one. Read one when
asked. Never write to one: no sessions, no decisions, no edits. To work on it, restore it.

## Archives from before 3.0

Those are `.tar.gz` files and this plugin does not unpack them. `restore_thread` returns
`Status: LEGACY_ARCHIVE` and names the reference to follow; see
`commands/unpack-legacy-archive.md`.
