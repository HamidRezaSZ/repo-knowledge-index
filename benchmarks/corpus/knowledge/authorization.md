---
id: authorization
title: Authorization and Roles
summary: Roles, permission checks and resource ownership rules.
aliases: [permissions, rbac]
tags: [security]
related: [authentication]
---
# Roles

Every account has one role per workspace: `viewer`, `editor` or `admin`. Roles live on the membership record, so one person can be an admin in one workspace and a viewer in another.

# Permission checks

Handlers call `require_permission(user, action, resource)` before reading or changing data. The check runs in the service layer, never only in the UI, because API clients can bypass the UI.

# Ownership

Users may edit records they created even with the `viewer` role, unless the workspace is archived. Admins can transfer ownership from the record's settings page.

# Default deny

If no policy matches an action, the request is refused with HTTP 403. New endpoints must declare their policy before they can be merged.
