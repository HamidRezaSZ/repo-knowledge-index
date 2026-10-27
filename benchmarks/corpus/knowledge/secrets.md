---
id: secrets
title: Secrets Management
summary: Storing, reading and rotating credentials and API keys.
aliases: [credentials, vault]
tags: [security, operations]
related: [configuration]
---
# Storage

Secrets live in HashiCorp Vault under `secret/<service>/<environment>`. They are never committed to Git, even encrypted.

# Reading secrets

At startup the service reads its secrets from Vault using its Kubernetes service account and keeps them only in memory.

# Rotation

Database passwords rotate every 90 days automatically. Third-party API keys are rotated by hand; the owner listed in Vault metadata gets a reminder two weeks before they expire.

# Leaked secrets

If a secret is exposed, rotate it first, check the audit log for its use, and then remove it from wherever it leaked.
