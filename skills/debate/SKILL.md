---
name: debate
description: Pressure-test a proposal through structured dialogue between a proponent and skeptic. Extracts the current proposal from context, runs rounds of challenge and refinement, and saves a synthesized plan as a thread artifact.
---

# Debate Skill

Pressure-test the current proposal by running a structured dialogue between a `proponent` and a `skeptic`. Both agents share the same goal: a stronger, more honest proposal. Neither is trying to win.

## Invocation

```
/ai-workspace:debate        # 2 rounds (default, Claude Code)
/ai-workspace:debate 3      # custom number of rounds (Claude Code)
/debate                     # 2 rounds (default, Codex CLI)
/debate 3                   # custom number of rounds (Codex CLI)
```

## Steps

### 1. Extract the Proposal

Identify the current proposal or idea from:
- The active thread's README.md Quick Resume section
- The current conversation context

Summarize it in 2-3 sentences: what is being proposed, what problem it solves, and what the key assumptions are.

Check whether any specialist agents are available beyond the `proponent` and `skeptic`. If none are found, warn the user before starting:

```
Note: no specialist agents are available. The debate will rely solely on the proponent
and skeptic without external validation of assumptions, which limits its rigor.

On Claude Code, install the specialist agents pack:
  /plugin install tech-expert-agents@sebmartin

On Codex CLI, specialist subagents are not yet distributed as a plugin.
You can install them manually by placing .toml agent files in ~/.codex/agents/.
```

Then confirm the proposal with the user before starting:

```
I'll pressure-test the following proposal:

[summary]

Starting debate — N rounds. I'll pause if either agent needs clarification from you.
```

---

### 2. Run Debate Rounds

Each round follows this structure:

1. **Proponent** — given the proposal and all previous round output, develops the strongest honest version and addresses any unresolved concerns from the previous round
2. **Skeptic** — given the proponent's output, counters specific assumptions, surfaces blind spots, and acknowledges concerns the proponent resolved well
3. **Proponent** — responds to the skeptic's counters, refines the proposal

Invoke each agent as a subagent so they run in isolated context. The exact mechanism depends on the CLI:

- **Claude Code**: use the `Task` tool with `subagent_type: "proponent"` or `subagent_type: "skeptic"`. Multiple subagents can run in parallel.
- **Codex CLI**: ask Codex to spawn the `proponent` or `skeptic` subagent by name (Codex spawns subagents on explicit request). Requires the agent `.toml` files to be present in `~/.codex/agents/` — the `init` skill installs these.

In either case, pass the full debate context so far so each agent builds on, not repeats, what came before.

Between each agent turn, briefly summarize what changed: which concerns were raised, which were resolved, which remain open.

#### Handling User Questions

If either agent needs clarification from the user (signaled by language like "I need to ask the user:" or "Before I can continue, I need to know:"), **pause the debate immediately**. Present the question clearly:

```
[Proponent / Skeptic] needs clarification before continuing:

[question]
```

Wait for the user's answer. Resume the debate from where it paused with the new information included in context.

#### Specialist Agent Delegation

Either agent may delegate to any available specialist agents (architect, security reviewer, cost analyst, etc.) to validate assumptions. On Claude Code these are invoked via the Task tool; on Codex CLI they are spawned by name from `~/.codex/agents/`. Their findings are included in that agent's turn output and carried forward in the debate context. The richer the set of available specialist agents, the more rigorous the debate.

---

### 3. Synthesize

After all rounds complete, synthesize a final plan that incorporates the strongest elements from the debate. Do not simply pick a side — integrate the refinements made across all rounds.

The synthesis should cover:

- **Refined proposal**: What the idea looks like after pressure-testing
- **Key strengths**: What held up under scrutiny and why
- **Resolved weaknesses**: Concerns that were raised and how the proposal addressed them
- **Remaining open questions**: Things neither agent could resolve without more information or user decisions
- **Recommended next steps**

Present the synthesis to the user before saving.

---

### 4. Save as Artifact

Save to the active thread:

- **First debate on this thread**: Create `threads/{thread-name}/artifacts/debate-YYYYMMDD.md`
- **Additional rounds requested**: Update the existing debate artifact in place. Do not create a new file.

Show the relative file path (e.g. `./threads/my-thread/artifacts/debate-20260307.md`) so the user can open it directly.

If no active thread is set, present the synthesis inline and ask the user if they want to save it.

---

## Artifact Format

```markdown
# Debate: [Proposal Title] ([YYYY-MM-DD])

## Proposal

[Original proposal summary]

## Debate

### Round 1

**Proponent**: [strongest case for the proposal]

**Skeptic**: [specific counters and blind spots]

**Proponent (refined)**: [response to counters, updated proposal elements]

### Round 2

...

## Refined Proposal

[The strengthened version of the proposal, integrating all refinements]

## Key Strengths

- [What held up under scrutiny]

## Resolved Weaknesses

- [Concern raised]: [How the proposal addressed it]

## Remaining Open Questions

- [What still needs a decision or more information]

## Next Steps

- [Concrete actions]
```
