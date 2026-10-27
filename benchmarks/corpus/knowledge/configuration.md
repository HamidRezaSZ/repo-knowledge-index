---
id: configuration
title: Configuration
summary: Where settings come from, how they override each other, and how to change them.
aliases: [settings]
tags: [operations]
related: [secrets, local-development]
---
# Sources

Settings are read from `config/defaults.toml`, then from the environment's file such as `config/staging.toml`, then from environment variables. Later sources override earlier ones.

# Naming

Environment variables use upper case and the `APP_` prefix, so `email.sender_address` becomes `APP_EMAIL_SENDER_ADDRESS`.

# Validation

The service refuses to start when a required setting is missing or has the wrong type, and it prints the setting's name.

# Changing settings in production

Edit the values in the deployment repository and open a pull request; merging it restarts the pods. Never change values by hand on a running server.
