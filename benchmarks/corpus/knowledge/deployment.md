---
id: deployment
title: Deployment and Releases
summary: How code reaches production, release days, canaries and rolling back.
aliases: [deploy, release]
tags: [ci, operations]
related: [feature-flags, database-migrations]
---
# Pipeline

Merges to `main` build a container image, run the test suite and deploy to staging automatically. Production deploys start from the Promote button in the pipeline once staging checks pass.

# Release schedule

Production releases happen Monday to Thursday before 15:00 UTC. Fridays and public holidays are frozen except for urgent fixes approved by the on-call lead.

# Rollback

To undo a bad release, run `deployctl rollback <service>`, which redeploys the previous image in about two minutes. Database migrations are not reverted automatically.

# Canary releases

A new version first receives 5% of traffic for 15 minutes. The pipeline promotes it only if its error rate and p95 latency stay within 10% of the stable version.
