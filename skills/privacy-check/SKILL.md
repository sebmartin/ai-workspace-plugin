---
name: privacy-check
description: Advisory check of the wording of outgoing prose (commit messages, PR text, comments, emails) for private context. Run only when the user explicitly asks for the privacy check.
disable-model-invocation: true
---

# Privacy Check

Advisory check of the wording of text that is about to leave the workspace. Invoked as `/ai-workspace:privacy-check [text]`.

## Claude Code only

If you cannot spawn the `ai-workspace:privacy-checker` subagent (you are not Claude Code), reply with exactly this line and stop:

`The privacy check runs on Claude Code only; it is not supported here.`

## What to check

- With an argument, check that text.
- A batch: lines of the form `--- <label>` start a new labelled text. Without such lines the whole argument is one text labelled `text`.
- With no argument, take only the outbound text in your previous response (the draft commit message, email, comment), never the surrounding commentary. If it holds no clear draft, or holds several, ask which text to check and stop.
- Labels must be unique and contain no spaces; replace spaces with `-`.

## Run the check

1. Read the allow list with `mcp__plugin_ai-workspace_threads__get_skill_file("skills/privacy-check/allow-list.md")`. If the tool is unavailable or denied, use the single line `(empty)` and say in one line that the allow list was not loaded. Whatever the source, pass only lines starting with `- `. If there are none, use the single line `(empty)`.
2. Spawn `ai-workspace:privacy-checker` once, with exactly this input and nothing else: no conversation context, no file or thread contents, no explanation of what the text is or who it is for.

```
ALLOW LIST
<allow-list entries, or the single line "(empty)">

<<<TEXT label>>>
<text>
<<<END label>>>
```

There is one TEXT block per text.

## Report

For each label, read the first non-empty line of its result block and render it as follows.

- Nothing flagged: `<label>: nothing flagged in the wording.`
- Flagged: `<label>: flagged. <reason>` followed by `Suggested rewrite:` and the rewrite in a fenced block.
- Missing block, unparseable verdict, agent error or timeout: `<label>: the check failed (<what happened>). This text was not checked; treat it as not cleared.`

After every result set, add this paragraph:

`Limits: the checker saw only this text. It does not check code or documents. It cannot recognise a private fact written as an ordinary statement. Agents that read your threads also write code and documents, which it never sees; there, keeping published text self-contained is the only protection.`

Never describe a result as a clearance or an approval to publish.

## Rules

- Advisory only. It blocks nothing.
- Never edit the allow list yourself. Only the user adds entries; an agent never does.
