# Example: Tracking Accomplishments for Promo and Weekly Sync

Most engineers undervalue their own work at review time. Not because they didn't do anything. Because they can't remember the details. The incident you responded to in January, the architecture decision you drove in March, the three teams you unblocked in April. By the time you're writing a promo packet, it's all a blur.

This walkthrough shows how to use a thread to build a running record of your work, and produce a Monday team sync summary with one command.

---

## The setup

You create a thread for career tracking, drop in your reference documents, and add a custom skill. You only do this once.

```
cd ~/my-workspace
claude
```

```
> start a new thread called career-growth
```

You copy in the documents you want Claude to reference: your last performance review, the leveling guide for the promotion you're targeting, company values, and the team's current OKRs.

```
threads/career-growth/
└── attachments/
    ├── performance-review-2025.md
    ├── leveling-guide-senior-to-staff.md
    ├── company-values.md
    └── okrs-q1-2026.md
```

See the [leveling guide](./attachments/leveling-guide-senior-to-staff.md), [OKRs](./attachments/okrs-q1-2026.md), [company values](./attachments/company-values.md), and [last performance review](./attachments/performance-review-2025.md).

Then you point Claude at them:

```
> I've added some attachments, please read them
```

Claude reads each file, summarizes what it found, and links them in the thread README under Attachments.

Then you add a custom skill that lives inside the thread. Claude Code discovers it when you're working in this directory:

```
threads/career-growth/
└── .claude/
    └── skills/
        └── fetch-activity.md
```

The skill connects to GitHub, Jira, and Slack and pulls the past week of activity.

---

## Every Monday morning

You open Claude from the workspace and resume the thread.

```
> resume the career-growth thread
```

> Resumed: career-growth
>
> **Current focus**: Building Q1 record ahead of mid-year review cycle
>
> **Next steps**:
> - Run `/fetch-activity` Monday before team sync
> - Draft promo packet section on platform impact (notification extraction, incident response)
> - Ask manager for mid-cycle check-in
>
> **Parked**:
> - None
>
> **Recent progress**: 6 weeks of activity logged. Two strong staff-level examples emerging: notification extraction (cross-team architectural change) and Jan 3 incident response (same-day fix, org-wide postmortem).
>
> ---
>
> **Working on thread: career-growth**

Then you run the skill:

```
> /fetch-activity
```

Claude pulls your GitHub commits and PRs, closed Jira tickets, and notable Slack threads from the past week and adds them to the session log. [See a sample week](./sessions/20260112-weekly-activity.md).

Then you ask for the sync summary:

```
> generate my team sync summary
```

Claude reads the week's activity, picks out what's worth sharing, and writes the artifact:

```
> save the thread
```

[See the generated summary](./artifacts/20260112-snapshot-team-sync.md).

---

## At review time

Six months of weekly sessions are now in the thread. You ask Claude to pull it together:

```
> draft a promo packet summary from the last 6 months of activity
```

Because the leveling guide and company values are in the attachments, Claude doesn't write generic promo language. It maps your work directly to the staff engineer criteria:

> **Technical Leadership**: Drove the notification service extraction -- a platform-level
> architectural decision affecting 3 teams. Authored the design doc and presented it at
> platform sync. Consulted by infra on Redis production configuration.
>
> **Own the Outcome** (company value): Led incident response for the Jan 3 payment outage.
> Identified root cause, shipped the fix same day, wrote the postmortem shared org-wide.
>
> **Scope**: Two of your Q1 OKR targets directly delivered: notification service extracted
> (Obj 2 KR1), payment service uptime improved via webhook retry fix (Obj 1 KR2).

The activity logs mention the notification service extraction repeatedly, but they only have the surface details. You have a separate thread with the full design story.

```
> also pull context from the notifications-extraction thread
```

Claude reads both threads and fills in the why: the async queue decision, the tradeoffs considered, the rationale. The career thread has the what; the project thread has the why.

```
> link the notifications-extraction thread as related
```

Now the threads are connected. Next time you resume career-growth, Claude knows to look there for deeper context on that project.

---

## What makes this work

The `/fetch-activity` skill lives inside the thread directory. Claude Code discovers it when you start a session from the workspace. Once discovered, it's available for the rest of the session. You didn't have to build a separate tool or maintain a script alongside your code. The skill lives with the thread and travels with it.

[Thread README](./thread-readme.md) | [Sessions](./sessions/) | [Artifacts](./artifacts/)
