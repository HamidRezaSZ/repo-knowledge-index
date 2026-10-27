---
id: tracing
title: Tracing and Metrics
summary: Distributed tracing with OpenTelemetry, Prometheus metrics and Grafana dashboards.
aliases: [opentelemetry, metrics]
tags: [observability]
related: [logging, alerting]
---
# Traces

Every inbound request starts an OpenTelemetry trace, and its ID is returned in the `X-Request-Id` header. Outgoing HTTP calls and database queries are recorded as child spans automatically.

# Metrics

Services expose Prometheus metrics at `/metrics`. Each endpoint records its request count, error count and a latency histogram.

# Dashboards

Grafana has one dashboard per service, generated from `observability/dashboards/`. Edit the files there, not in the Grafana UI, or the next sync overwrites your changes.
