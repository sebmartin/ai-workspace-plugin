# Commands: park, pop, parked

## Park a topic (`/threads park [topic]`)

- If topic not provided: ask "What would you like to park?"
- Append to `**Parked**:` field in Quick Resume with today's date: `- [YYYY-MM-DD] topic`
- If the Parked field shows `- None`, replace it; otherwise append below existing items
- Confirm: "Parked: [topic]"

## Pop a parked topic (`/threads pop`)

- Read README.md and find the first item in `**Parked**:`
- If nothing parked (shows `- None`): say "Nothing parked."
- Otherwise:
  - Show: "Picking up: [topic]"
  - Remove it from the Parked list (if it was the only item, replace with `- None`)
  - Write a one-line entry to the current session log: `Picked up parked topic: [topic]`
  - Update the README.md

## List parked topics (`/threads parked`)

- Read README.md and show the Parked section contents
- If `- None`: say "Nothing parked in [thread-name]."
- Otherwise list items with numbers for easy reference
