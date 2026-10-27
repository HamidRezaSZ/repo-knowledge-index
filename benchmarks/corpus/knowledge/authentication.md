---
id: authentication
title: Authentication
summary: How users sign in, how access and refresh tokens work, and how sessions end.
aliases: [login, sign-in]
tags: [security, identity]
related: [authorization, secrets]
---
# Password login

Users sign in with an email address and a password. Passwords are hashed with Argon2id, and five failed attempts within ten minutes lock the account for fifteen minutes.

# Access tokens

A successful login returns a JSON Web Token that expires after 15 minutes. Services check its signature against the public keys published at `/.well-known/jwks.json` instead of calling the identity service on every request.

# Refresh tokens

Clients exchange a refresh token for a new access token at `POST /auth/refresh`. Each refresh token works once: the server issues a replacement and revokes the old one, and reuse of a revoked token ends every session of that user.

# Logout

Logging out deletes the refresh token and adds the access token's `jti` claim to a deny list until the token expires.
