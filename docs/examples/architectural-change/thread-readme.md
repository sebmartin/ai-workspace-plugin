# Thread: notifications-extraction

**Started**: 2026-05-08
**Status**: Active
**Last Session**: 2026-05-08
**Parent Thread**: None
**Child Threads**: None
**Related Threads**: None

## Quick Resume

> **Purpose**: Quick context for resuming after days/weeks/months. Keep this BRIEF and CURRENT.

**Current focus**: Implement event publisher in API repo

**Next steps**:
- [ ] Implement event publisher in API repo (`~/api-repo`)
- [ ] Stand up notifications service repo (`~/notifications-service`)
- [ ] Wire up Redis Streams consumer

**Parked**:
- [2026-01-15] Deployment and rollout order

**Recent progress**: Planning complete. Defined service boundary and event contract. Decided on async queue (Redis Streams) for inter-service communication. Two decisions logged.

---

## Problem

Notification logic is tightly coupled to API request handlers. Hard to scale independently, and any slowness in notification delivery affects API response times.

## Current State

Notifications sent synchronously inside request handlers in the API monolith.

## Desired State

Separate notifications service. API publishes events to a Redis Streams queue; notifications service consumes and delivers them independently.

## Existing Infrastructure

- **Tech stack**: Node.js API, Redis (already running for caching)
- **Systems**: `~/api-repo`, `~/notifications-service` (new)
- **Constraints**: Avoid new AWS dependencies at current scale

---

## Open Questions

- Rollout order: deploy new service first or ship API changes first?

## Resolved Questions

> **Keep this high-level.** For detailed decision rationale, see decisions/ directory.

- Use async queue, not direct HTTP (see decision 2026-01-12)
- Redis Streams over SQS (see decision 2026-01-15)

---

## Resources

> **Important**: This README should NOT duplicate content from sessions, decisions, or todos.
> It's a landing page with links to the details.

### Sessions
 - [Service boundary and event contract](./sessions/20260112-service-boundary-and-event-contract.md)
 - [Queue technology decision](./sessions/20260115-queue-technology-decision.md)

### Decisions
 - [Use async queue for notification delivery](./decisions/20260112-use-async-queue-for-notification-delivery.md) -- async over direct HTTP to decouple availability
 - [Redis Streams over SQS](./decisions/20260115-redis-streams-over-sqs.md) -- no new infrastructure, simpler local dev

### Attachments
 - None

### Artifacts
 - None

---

## Notes



---

**Last updated**: 2026-05-08
