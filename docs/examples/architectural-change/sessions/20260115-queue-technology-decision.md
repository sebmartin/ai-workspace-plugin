# Session: Queue technology decision - 2026-01-15

**Date**: 2026-01-15
**Thread**: [notifications-extraction](../README.md)

## Goal

Pick a queue technology and wrap up the planning phase.

## Discussion

### Key Points
- Compared SQS and Redis Streams
- Already running Redis for caching -- Streams adds no new infrastructure
- SQS would require mocking in local dev, adds an AWS dependency
- Decided on Redis Streams at current scale, with a clear revisit condition

### Decisions Made
- Redis Streams over SQS → [decisions/20260115-redis-streams-over-sqs.md](../decisions/20260115-redis-streams-over-sqs.md)

## Outcomes

### Completed
- [x] Queue technology decided
- [x] Planning phase complete

## Next Session

### Next Steps
- [ ] Implement event publisher in API repo
- [ ] Stand up notifications service repo
- [ ] Wire up Redis Streams consumer

### Context for Next Time
Planning is done. Two decisions logged. Start with the API repo: add the Redis Streams publisher to the notification code paths, then move to the new service repo to build the consumer.
