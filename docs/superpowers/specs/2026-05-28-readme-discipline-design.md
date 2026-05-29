# README Discipline: Read Model and Write Model

**Date**: 2026-05-28
**Thread**: ai-workspace-setup
**Status**: Approved

---

## Problem

Thread READMEs grow unbounded because the skill has no clear model for what belongs in them. The LLM invents new sections, dumps inline content, and appends to Quick Resume indefinitely. Two consequences:

1. The README becomes too long to read and retain fully — the map becomes incomplete and untrustworthy.
2. Information buried in inline README sections is not reliably recalled on resume, unlike named linked files which the LLM can retrieve on demand.

---

## The README Model

The README is a lean index — the complete map of a thread. It must be short enough to read in full and retain entirely. That is not a style preference; it is what makes the map trustworthy. Every line of inline content competes for context with the links that matter.

The README's job: tell the LLM what files exist and where the work stands. Not to hold content itself.

---

## Read Discipline (on resume)

Read the entire README, every section. No skipping.

- **Quick Resume** — current state: focus, next steps, parked items
- **Decisions section** — what constraints exist and where to find them
- **Resources** — what session logs, artifacts, and attachments are available

Missing any section means navigating with an incomplete map. The README is lean precisely so this full read is fast and the result is fully retained.

After reading the README, the LLM knows what files exist. It does not read those files eagerly — it pulls them on demand when specific work requires them.

**Goals the read model optimises for:**
1. Speed — show the user the Quick Resume immediately
2. Orientation — the LLM has the complete map after one read
3. Token efficiency — nothing beyond the README is read until needed
4. Correctness at work time — because the LLM knows the map, it knows which files to read before starting any planning or recommendation

---

## Write Discipline (on save/update)

**Fixed sections only.** Do not add sections that are not in the template. If content doesn't fit the allowed sections, create a linked artifact or decision instead. The README holds the link and a one-line description; the file holds the content.

**What belongs inline:**
- Metadata header (dates, status, thread links)
- Quick Resume (see constraints below)
- Problem / Current State / Desired State — 1–3 sentences each
- Decisions — links with one-line descriptions only
- Open Questions — bullet list only, no discussion
- Resources — links with one-line descriptions only (sessions, attachments, artifacts)

**What does NOT belong inline:** workflow descriptions, architecture notes, directory trees, risk registers, design details, resolved questions, notes, anything requiring more than a sentence to explain. These become artifacts or decisions.

**When in doubt:** create a linked artifact. A README that needs a new section is a README that needs a new artifact instead.

---

## Quick Resume Constraints

Quick Resume is the legitimate exception to the no-inline-content rule. Current focus, next steps, and recent progress belong here because they are the fast-orientation content. But they decay.

**Recent progress**: rolling window of the last 3–5 entries. Older entries already live in session logs — do not duplicate them here. When adding a new entry, remove the oldest if the list exceeds 5.

**Next steps**: ideal length is 5 items. On save, if "Next steps" exceeds 10 items, ask the user whether any should be removed or parked. Items that have appeared across multiple sessions without progress are stale candidates.

---

## Template Changes

Remove from thread template:
- `## Resolved Questions` — decisions/ handles this with proper structure
- `## Notes` — artifacts/ handles this; Notes is a blank canvas with no ceiling

Add to thread template (top, visible):
> Fixed structure — do not add sections. Everything substantive goes in a linked artifact or decision.

---

## Changes Required

### `skills/threads/SKILL.md`
1. Add README model section explaining the index purpose and why lean = trustworthy
2. Replace "Context Building for Resume" with the read discipline above (read all, pull on demand)
3. Add write discipline rules with explicit "what does NOT belong inline" list
4. Add Quick Resume decay constraints (rolling recent progress, 10-item pruning prompt)
5. Revise "What to read internally before further work" — remove eager loading; the read is the README only; files are pulled on demand

### `templates/thread-template.md`
1. Remove `## Resolved Questions`
2. Remove `## Notes`
3. Add fixed-structure warning at top
