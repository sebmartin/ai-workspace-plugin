# Decision: Use Redis Streams over SQS

**Date**: 2026-01-15
**Thread**: [notifications-extraction](../README.md)
**Status**: Accepted

## Decision

Use Redis Streams (self-hosted) as the queue rather than AWS SQS.

## Why

Already running Redis for caching. Adding Streams avoids a new AWS dependency and keeps the local dev environment simple -- no mocking SQS. Acceptable tradeoff at current scale.

## Alternatives Considered

- **AWS SQS** (rejected): adds an AWS dependency, complicates local dev setup, overkill at current volume

## Consequences

- No new infrastructure needed
- Local dev works without AWS credentials or mocking
- Should revisit if volume grows beyond ~10k events/day or ops burden increases with team growth
