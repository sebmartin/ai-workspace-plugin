# Example: Planning a Cottage Build

A cottage build takes years and involves dozens of decisions: zoning, permits, contractors, materials, tradeoffs. The details matter and the timeline is long. This walkthrough shows how to use a thread to keep it all organized, with a custom skill built from the municipality's own bylaw documents.

---

## The setup

You create a thread and load it with the reference documents you'll need throughout the project.

```
> start a new thread called cottage-build
```

You download the zoning bylaw PDFs and building permit guide from the township website, drop them in `attachments/`, and ask Claude to convert them to Markdown. Then you ask Claude to build a bylaw expert skill around those documents. From that point on, any question about setbacks, permitted uses, or permit requirements gets answered from the actual bylaw text, no manual document searching.

```
threads/cottage-build/
└── attachments/
    ├── zoning-bylaw-section4-residential.md
    └── building-permit-requirements.md
```

See the [zoning bylaw](./attachments/zoning-bylaw-section4-residential.md) and [permit requirements](./attachments/building-permit-requirements.md).

Then you tell Claude to read the attachments.

---

## Checking your design against zoning

You have a proposed footprint sketched out. Before paying for drawings, you want to know if anything needs to change.

```
> my lot is 0.6 ha with 52 m of water frontage. I'm planning an 11 x 14 m cottage,
> 7.5 m tall, placed 33 m from the high water mark. Does this work?
```

Claude recognizes this as a bylaw question, invokes the skill, and answers:

> Checking against SR zone requirements (Bylaw 2019-50, Section 4):
>
> **Setbacks** (s.4.3): water 33 m ✓ (min 30 m), road 9 m ✓ (min 7.5 m), side 4.5 m ✓ (min 3 m)
> **Height** (s.4.4): 7.5 m ✓ (max 9 m)
> **Lot coverage** (s.4.4): 154 m² / 6,000 m² = 2.6% ✓ (max 10%)
> **Impervious surface** (s.4.4): cottage + driveway + deck = 274 m² / 6,000 m² = 4.6% ✓ (max 15%)
>
> Two blockers before you can submit (from Building Permit Guide, Rev. 2024):
> 1. Septic permit must be obtained from the Health Unit before the building permit can be issued. Budget 4-6 weeks.
> 2. Your main beam span is 5.2 m. Stamped structural drawings are required for spans over 4.8 m.

You decide to shift the cottage 1 m further from the water for margin, and log it.

```
> log this decision
```

One of the next steps is to engage a septic designer. You ask Claude to draft the email.

```
> draft an email to the septic designer
```

Claude pulls the lot details, setback constraints, and permit sequencing from the thread and writes a complete email:

> **To**: [septic designer]
> **Subject**: Septic design needed -- new cottage build, Muskoka Lakes
>
> Hi,
>
> I'm planning a new cottage build on a lot in Muskoka Lakes Township (SR zone) and need a septic designer to complete a design for the permit application. I'd like to get started as soon as possible -- I understand the Health Unit approval needs to come before the building permit can be issued.
>
> Here are the relevant details:
>
> **Lot**: 0.6 ha, 52 m water frontage, Muskoka Lakes Township (Bylaw 2019-50, SR zone)
>
> **Proposed cottage**: 11 m x 14 m footprint, placed 34 m from the high water mark, 9 m from the road
>
> **Constraints**: Septic must be minimum 30 m from any water body and 15 m from any well. I don't yet have a proposed septic location and would welcome your input on placement given the lot layout.
>
> Could you let me know your availability, typical turnaround for a design at this stage, and what you'd need from me to get started?
>
> Thanks,
> Alex Johnson
> 555-867-5309

[Full session log](./sessions/20260203-zoning-check.md)

---

## Picking it up weeks later

You've lined up a septic designer and structural engineer. You open the thread to figure out what else needs to happen before you can submit.

```
> resume the cottage-build thread
```

> Resumed: cottage-build
>
> **Current focus**: Permit application prep -- get septic designer and structural engineer engaged
>
> **Next steps**:
> - Engage septic designer (4-6 week lead time)
> - Get structural drawings started (flag 5.2 m beam span)
> - Commission site plan drawing to scale
>
> **Parked**:
> - Boathouse design (after main permit approved)
>
> **Recent progress**: Zoning check complete. Proposed footprint clears all setbacks, height, and coverage limits. Two blockers identified before permit can be submitted: septic approval and structural engineer stamp.
>
> ---
>
> **Working on thread: cottage-build**

You ask what's still needed for a complete permit application:

```
> what do I still need to submit a complete permit application?
```

Claude checks against the permit requirements document and gives you the gap list.

---

## What the thread holds

By the time you submit the permit, the thread has:

- Bylaw documents available for any question that comes up during design
- A decision log with the reasoning behind placement, materials, and tradeoffs
- Session logs tracking what was checked, what changed, and why
- A parked list of things to tackle after the permit is approved

The build takes two years. The thread travels with it.

---

[Thread README](./thread-readme.md) | [Sessions](./sessions/) | [Decisions](./decisions/) | [Attachments](./attachments/)
