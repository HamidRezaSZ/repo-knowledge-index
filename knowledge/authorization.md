---
id: authorization
title: Authorization and Object Access
summary: Verify permissions at the resource level before exposing records.
aliases: [permissions, access-control]
tags: [security, permissions, object-access]
related: [authentication]
---
# Object-level permissions

Authenticated callers may still lack permission to inspect a specific resource. Check ownership or membership before accessing that object.

# Default deny

A missing authorization policy must not turn into implicit access. Prefer explicit checks and secure defaults.
