---
id: api-versioning
title: API Versioning
summary: URL versions, the breaking-change policy and deprecation timelines.
aliases: [versioning, deprecation]
tags: [api]
related: [api-errors]
---
# Version in the URL

Public endpoints live under `/v1/` and `/v2/`. A new major version is needed only for breaking changes; adding optional fields is not breaking.

# Breaking changes

Removing a field, renaming it, changing its type or making an optional parameter required are breaking changes.

# Deprecation

A deprecated version keeps working for 12 months. Its responses carry a `Sunset` header with the shutdown date, and the API changelog announces it.
