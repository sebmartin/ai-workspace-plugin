# Team Sync Summary - Week of Jan 12

## Shipped
- **Payment webhook retry logic** (PLAT-1847) -- same-day fix during the Jan 3 outage, incident postmortem shared org-wide
- **Notification service extraction, API side** (PLAT-1863) -- Redis Streams queue now live, decouples notification delivery from API availability

## In Progress
- **Notification service consumer** (PLAT-1871) -- PR open in notifications-service repo, on track for this week
- **Redis production config** -- working with infra (@alex) on sizing and failover

## Heads Up
- I'm now the point of contact for Redis Streams questions -- a few teams are looking at adopting it
