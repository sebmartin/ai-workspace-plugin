# Session: Service boundary and event contract - 2026-01-12

**Date**: 2026-01-12
**Thread**: [notifications-extraction](../README.md)

## Goal

Define what moves to the notifications service, what stays in the API, and how the two sides communicate.

## Discussion

### Key Points
- Notification logic is currently embedded in request handlers -- tightly coupled, hard to scale independently
- Explored direct HTTP vs async queue for inter-service communication
- Settled on async queue: decouples availability, retry logic lives in one place
- Drafted the event contract: API publishes `notification.requested` events with recipient, template, and payload

### Decisions Made
- Use async queue (not direct HTTP) → [decisions/20260112-use-async-queue-for-notification-delivery.md](../decisions/20260112-use-async-queue-for-notification-delivery.md)

## Outcomes

### Completed
- [x] Defined service boundary
- [x] Drafted event contract
- [x] Logged async queue decision

### Created Artifacts
- [decisions/20260112-use-async-queue-for-notification-delivery.md](../decisions/20260112-use-async-queue-for-notification-delivery.md)

## Next Session

### Next Steps
- [ ] Choose queue technology (SQS vs Redis Streams)
- [ ] Finalize deployment and rollout order

### Open Questions
- Which queue technology? SQS vs self-hosted Redis Streams
- Rollout order: new service first or API changes first?
