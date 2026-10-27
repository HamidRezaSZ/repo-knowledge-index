---
id: payments
title: Payments
summary: Charging customers, idempotency, refunds and payment webhooks.
aliases: [billing, stripe]
tags: [payments]
related: [background-jobs, api-errors]
---
# Charges

Charges go through Stripe's Payment Intents API. Amounts are integers in the smallest currency unit, so 10.50 EUR is stored as 1050.

# Idempotency

Every charge request carries an `Idempotency-Key` header derived from the order ID, so a retried request never charges twice.

# Refunds

Refunds are issued from the order page or with `POST /v2/orders/{id}/refunds`. Partial refunds may not exceed the captured amount.

# Webhooks

Stripe events arrive at `/webhooks/stripe`. Verify the signature with `STRIPE_WEBHOOK_SECRET` before trusting the payload, and process each event ID only once.
