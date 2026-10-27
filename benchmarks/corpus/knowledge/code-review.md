---
id: code-review
title: Code Review and Branching
summary: Branch names, pull request size and approval rules.
aliases: [pull-requests, branching]
tags: [process]
related: [testing, deployment]
---
# Branches

Branch from `main` and name branches `<ticket>-<short-description>`, for example `PAY-142-refund-webhook`. Rebase on `main` before asking for review.

# Pull request size

Keep pull requests under 400 changed lines. Split larger changes behind a feature flag.

# Approvals

Every pull request needs one approval. Changes to payments, authentication or migrations need two, including one from the owning team.
