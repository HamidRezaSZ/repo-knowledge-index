---
id: database-migrations
title: Database Migrations
summary: Writing, reviewing and running schema migrations safely.
aliases: [migrations, schema-changes]
tags: [database, postgres]
related: [database-connections, deployment]
---
# Creating a migration

Run `make migration name=add_orders_index` to generate a timestamped file in `db/migrations/`. Every migration has an `up` and a `down` step, and both are required.

# Zero-downtime changes

Never rename or drop a column in the same release that stops using it. Add the new column, backfill it, ship code that reads it, and remove the old column in a later release.

# Large tables

On tables with more than a million rows, create indexes with `CREATE INDEX CONCURRENTLY`, which does not block writes. Backfills run in batches of 10,000 rows from a background job, not inside the migration.

# Running migrations

The deploy pipeline applies pending migrations before new application pods start. To apply them locally, run `make migrate`.
