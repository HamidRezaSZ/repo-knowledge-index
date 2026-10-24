---
id: caching
title: Caching and Invalidation
summary: Cache-aside patterns, key design, and invalidation on writes.
aliases: [cache, redis]
tags: [performance, latency, cache]
related: []
---
# Cache-aside

Read from cache, then fall back to the primary database. Store the result with an appropriate expiration policy.

# Invalidation

Invalidate or update cache keys after durable database writes so readers do not serve obsolete values.
