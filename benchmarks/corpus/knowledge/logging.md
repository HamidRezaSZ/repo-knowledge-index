---
id: logging
title: Logging
summary: Log format, log levels, sensitive data and retention.
aliases: [logs]
tags: [observability]
related: [tracing, privacy]
---
# Format

Logs are JSON lines with `timestamp`, `level`, `message`, `request_id` and `service` fields. Use the shared `log` helper rather than `print`.

# Levels

Use `error` for failures that need a human, `warning` for recoverable problems, `info` for state changes, and `debug` only when `LOG_LEVEL=debug` is set.

# Sensitive data

Never log passwords, tokens, full card numbers or home addresses. The log helper masks the fields listed in `REDACTED_FIELDS`; add new sensitive fields there.

# Retention

Logs stay in the log store for 30 days and in cold storage for one year, for audits.
