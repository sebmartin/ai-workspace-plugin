# Commands: link-parent, create-child, link-related

## Link to parent thread (`/threads link-parent [thread-name]`)

- If thread name not provided: list threads with numbers, ask which is the parent, wait for reply.
- **Bidirectional** (both updates required):
  1. Update current thread's README.md "Parent Thread" field: `[Thread Name](../thread-name/README.md)`
  2. Update parent thread's README.md "Child Threads" field — add `[Current Thread Name](../current-thread-name/README.md)`. If "None", replace it; otherwise append.
- A thread can only have ONE parent. If already set, confirm before replacing.

## Create a child thread (`/threads create-child [thread-name]`)

- Requires an active thread (current thread becomes the parent)
- Create the new child thread (same as `/threads create`, see `commands/create.md`)
- Set up bidirectional links:
  1. Set child's "Parent Thread" to `[Parent Thread Name](../parent-thread-name/README.md)`
  2. Add child to current thread's "Child Threads" — `[Child Thread Name](../child-thread-name/README.md)`. If "None", replace; otherwise append.
- Active thread remains the parent after creation (not the child)

## Link a related thread (`/threads link-related [thread-name]`)

- If thread name not provided: list threads with numbers, ask which is related, wait for reply.
- **Bidirectional** (both updates required):
  1. Update current thread's README.md "Related Threads": add `[Thread Name](../thread-name/README.md)`
  2. Update related thread's README.md "Related Threads": add `[Current Thread Name](../current-thread-name/README.md)`
  - If "None", replace; otherwise append.
- Related threads are symmetric. A thread can have multiple related threads.
