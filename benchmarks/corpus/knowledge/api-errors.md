---
id: api-errors
title: API Errors
summary: The error response format and what each error code means.
aliases: [errors, error-codes]
tags: [api]
related: [rate-limiting, api-versioning]
---
# Error format

Errors are JSON objects with `code`, `message` and `request_id`. Clients should branch on `code`; `message` is for humans and may change.

# Validation errors

Invalid input returns HTTP 422 with `ERR_VALIDATION` and a `fields` object that maps each bad field to a reason.

# Server errors

Unexpected exceptions return HTTP 500 with `ERR_INTERNAL`. The stack trace goes to the error tracker, never to the client.
