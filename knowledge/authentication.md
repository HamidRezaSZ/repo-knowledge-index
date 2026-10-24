---
id: authentication
title: Authentication and Session Lifecycle
summary: Login, access tokens, refresh tokens, and session revocation.
aliases: [auth, jwt, login]
tags: [identity, security, tokens]
related: [authorization]
---
# Login

A user signs in with credentials. The application issues a short-lived access token and a rotating refresh token.

# Refresh tokens

Refresh tokens allow a client to obtain another access token. Rotate refresh credentials and reject replay of an already consumed refresh token.

# Revoking sessions

The server records revoked session identifiers and refuses requests for sessions that are no longer valid.
