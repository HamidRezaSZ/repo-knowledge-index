---
id: database-connections
title: Database Connections and Pooling
summary: Connection pool sizing, timeouts and read replicas for PostgreSQL.
aliases: [connection-pool, pgbouncer]
tags: [database, postgres, performance]
related: [database-migrations, backups]
---
# Pool size

Each application process opens at most `APP_DATABASE_POOL_SIZE` connections, 10 by default. PgBouncer in transaction mode sits in front of PostgreSQL and caps the total at 400.

# Timeouts

Queries are cancelled after `statement_timeout`: 5 seconds for web requests and 60 seconds for background jobs. A request that waits more than 2 seconds for a free connection fails with `ERR_DB_POOL_EXHAUSTED`.

# Read replicas

Reports and exports read from the replica through `db.replica()`. The replica can lag a few seconds behind, so never read from it right after a write the user expects to see.
