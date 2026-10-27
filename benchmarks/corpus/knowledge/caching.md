---
id: caching
title: Caching
summary: Redis cache usage, key naming, expiry and invalidation.
aliases: [redis, cache]
tags: [performance]
related: [database-connections]
---
# Cache-aside reads

Read the key from Redis; on a miss, load the value from PostgreSQL and store it with a TTL. The default TTL is 300 seconds, set by `APP_CACHE_TTL`.

# Key naming

Keys follow `<service>:<entity>:<id>:v<schema>`, for example `orders:order:42:v3`. Bump the version suffix when the cached shape changes, so old entries are ignored.

# Invalidation

Delete the key in the same code path that commits the write, after the transaction succeeds. Never update cached values in place, because concurrent writers can store stale data.

# Stampede protection

When a popular key expires, one worker holding a short lock rebuilds it while other callers keep serving the old value.
