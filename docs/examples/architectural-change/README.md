# Example: Planning and Executing an Architectural Change

Extracting a service takes weeks and touches multiple repos. By the time you're writing code, the planning sessions are long gone from your context window. This walkthrough shows how a thread keeps the work coherent across both phases, and how decisions you log during planning end up answering questions during execution, across two separate repos.

---

## The situation

Your API server has grown to the point where the notification logic is tightly coupled to the main request handlers. You want to extract it into a separate notifications service. That means changes to the API repo and a new service repo: two codebases, one coherent plan.

---

## Week 1: Planning

You start a thread. No code yet, just working through the design.

```
cd ~/my-workspace
claude
```

```
> start a new thread called notifications-extraction
```

You spend a session on the design: what moves to the new service, what stays, how the two sides communicate. After some back and forth you lean toward an async queue rather than direct HTTP. Before committing, you run a debate to stress-test it.

```
> /ai-workspace:debate
```

A proponent and a skeptic run two rounds. The proponent argues for async: decoupled availability, retry logic in one place, independently scalable. The skeptic pushes back: added operational complexity, harder to reason about failure modes, debugging across a queue is painful. The proponent refines the argument: the complexity is real but bounded, and the alternative (tight availability coupling) compounds over time as the service grows.

The debate surfaces one concern worth addressing: what happens to in-flight notifications if the queue goes down? That gets added to the design before anything is built.

```
> log this decision
```

Claude drafts the decision file and links it from the thread README. The key part:

> Use an async queue between the API and the notifications service rather than direct HTTP
> calls. Direct HTTP couples availability -- if the notifications service is slow or down,
> API latency spikes. An async queue lets the API fire-and-forget; retry logic lives in
> the queue, not scattered across callers.

[Full decision](./decisions/20260112-use-async-queue-for-notification-delivery.md)

By end of the session you've sketched the full contract: what events the API publishes, what the notifications service consumes.

```
> park "decide on queue technology: SQS vs Redis Streams"
> save the thread
```

---

## A few days later

You've done some reading on the queue options. You pick up where you left off.

```
> resume the notifications-extraction thread
```

> Resumed: notifications-extraction
>
> **Current focus**: Choose queue technology
>
> **Next steps**:
> - Decide on queue technology (SQS vs Redis Streams)
> - Finalize deployment and rollout order
>
> **Parked**:
> - [2026-01-12] decide on queue technology: SQS vs Redis Streams
>
> **Recent progress**: Defined service boundary and event contract. Decided on async queue over direct HTTP. One decision logged.
>
> ---
>
> **Working on thread: notifications-extraction**

You work through the queue decision and log it. Redis Streams wins: already running Redis for caching, no new infrastructure, local dev stays simple.

[Full decision](./decisions/20260115-redis-streams-over-sqs.md)

End of week 1: a clear plan, two logged decisions, a parked list of follow-ups.

---

## Week 2: Execution

Time to write code. You open the API repo.

```
cd ~/api-repo
claude
```

```
> resume the notifications-extraction thread
```

> (Using threads from /Users/you/my-workspace)
>
> Resumed: notifications-extraction
>
> **Current focus**: Implement event publisher in API repo
>
> **Next steps**:
> - Implement event publisher in API repo (`~/api-repo`)
> - Stand up notifications service repo (`~/notifications-service`)
> - Wire up Redis Streams consumer
>
> **Parked**:
> - [2026-01-15] Deployment and rollout order
>
> **Recent progress**: Planning complete. Defined service boundary and event contract. Decided on async queue (Redis Streams) for inter-service communication. Two decisions logged.
>
> ---
>
> **Working on thread: notifications-extraction**

You're in the API repo with the full thread context loaded. You start implementing the event publisher. Midway through, a question comes up: should the API wait for Redis to acknowledge the event before returning a response?

Claude references the decision log:

```
Based on the decision to use fire-and-forget async delivery (see
decisions/20260112-use-async-queue-for-notification-delivery.md), the API should
not wait for acknowledgment. Waiting for Redis re-introduces the availability coupling
you were trying to avoid. Publish and move on; retry logic lives downstream.
```

You finish the API-side changes and save.

```
> save the thread
```

[Session log](./sessions/20260115-queue-technology-decision.md)

---

## Moving to the second repo

```
cd ~/notifications-service
claude
```

```
> resume the notifications-extraction thread
```

Same thread, different repo. Claude has the event contract, both decisions, and where you left off.

---

[Thread README](./thread-readme.md) | [All sessions](./sessions/) | [All decisions](./decisions/)
