---
id: background-jobs
title: Background Jobs
summary: Job queues, workers, retries, dead letters and scheduled jobs.
aliases: [jobs, workers, celery]
tags: [async]
related: [email]
---
# Queues

Jobs run on Celery workers with three queues: `default`, `critical` and `bulk`. Long exports go to `bulk`, so they cannot delay password resets in `critical`.

# Retries

A failed job is retried up to 5 times with exponential backoff, starting at 30 seconds. Jobs must be idempotent, because a retry can run after a partial success.

# Dead letters

After the last retry, the job moves to the dead-letter queue and an alert is posted to the team channel. Replay it with `jobs replay <job-id>` once the cause is fixed.

# Scheduled jobs

Periodic jobs are declared in `jobs/schedule.py` with cron syntax and run in UTC.
