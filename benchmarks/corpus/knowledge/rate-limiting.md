---
id: rate-limiting
title: Rate Limiting
summary: Request quotas per client and how throttled requests are answered.
aliases: [throttling, quotas]
tags: [api, security]
related: [api-errors]
---
# Limits

Each API key may send 100 requests per minute, and unauthenticated clients get 20 per minute per IP address. Counters use a sliding window stored in Redis.

# Responses

A request over the limit gets HTTP 429 with the error code `ERR_RATE_LIMITED` and a `Retry-After` header in seconds.

# Raising limits

Partners can ask for higher limits through a support ticket. A higher limit is a row in the `api_quotas` table, not a code change.
