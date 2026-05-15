# Decision: Use async queue for notification delivery

**Date**: 2026-01-12
**Thread**: [notifications-extraction](../README.md)
**Status**: Accepted

## Decision

Use an async queue between the API and the notifications service rather than direct HTTP calls.

## Why

Direct HTTP couples the availability of both services. If the notifications service is slow or down, API request latency spikes. An async queue lets the API fire-and-forget; the notifications service drains at its own pace. Retry logic lives in the queue, not scattered across callers.

## Alternatives Considered

- **Direct HTTP** (rejected): tight availability coupling, retry logic bleeds into the API
- **Shared database table** (rejected): polling overhead, harder to scale independently

## Consequences

- API publishes events and returns immediately
- Notifications service is independently deployable and scalable
- Need to choose a queue technology (parked for next session)
