# Command: restore an archive from before 3.0

Archives created before 3.0 are `.tar.gz` files. The plugin no longer unpacks tarballs, so
this is done by hand, once per archive, when the user asks for that thread back.

There is no bulk conversion and none is needed. An archive nobody restores can stay a
tarball forever at no cost.

## Steps

1. Find it. `list_archived_threads` shows legacy archives alongside the rest. The file is
   `archive/{year}-{name}.tar.gz`.

2. Check what is inside before extracting anything:

   ```
   tar -tzf archive/{year}-{name}.tar.gz | head
   ```

   Expect a single top-level directory named after the thread. If there is more than one
   top-level entry, stop and show the user what you found rather than extracting it.

3. Extract into `threads/`:

   ```
   tar -xzf archive/{year}-{name}.tar.gz -C threads/
   ```

4. Confirm `threads/{name}/README.md` exists. The thread is now ordinary and every tool
   works on it.

## The companion summary

Older archives have a sibling `archive/{year}-{name}.md` holding a summary and keywords
written when the thread was archived. That content is not carried over automatically.

Read it. If it says something the thread does not already record, add it to the thread as a
session. If it is just dates and a restatement of the README, it can be left alone. This is
a judgement call and it is the reason this step is prose rather than code.

## Afterwards

The tarball and its summary are superseded once the thread is back, and
`list_archived_threads` stops listing them as soon as the thread exists. They are the user's
files: say they are now redundant and leave any deleting to them.

Archiving the thread again produces the new directory format.
