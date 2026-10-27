---
id: feature-flags
title: Feature Flags
summary: Turning features on and off at runtime, gradual rollouts and flag cleanup.
aliases: [flags, toggles]
tags: [release]
related: [deployment]
---
# Creating a flag

Define flags in `config/flags.yaml` with an owner and an expiry date. Code reads them through `flags.enabled("name", user)`.

# Gradual rollout

A flag can target a percentage of users. Users are bucketed by a hash of their ID, so each person keeps the same experience.

# Kill switch

Any flag can be switched off from the admin console without a deploy, and the change reaches every server within 30 seconds.

# Removing flags

Remove a flag within two sprints after it reaches 100%. The weekly `flag-audit` job opens a ticket for every flag past its expiry date.
