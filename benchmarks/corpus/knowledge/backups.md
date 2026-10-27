---
id: backups
title: Backups and Disaster Recovery
summary: Database backups, restores, recovery targets and restore drills.
aliases: [disaster-recovery, restore]
tags: [operations, database]
related: [database-connections, privacy]
---
# Backup schedule

PostgreSQL takes a full snapshot every night and streams write-ahead logs continuously, so data can be restored to any point in the last 14 days.

# Restoring

Restores go to a new database instance first. Check row counts and recent orders there before switching the application over.

# Recovery targets

The target is to lose at most 5 minutes of data and to be back online within 4 hours after losing the primary region.

# Restore drills

Every quarter the platform team restores production into an isolated environment and records how long it took.
