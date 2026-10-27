---
id: local-development
title: Local Development
summary: Setting up and running the service on a laptop.
aliases: [setup, dev-environment]
tags: [onboarding]
related: [configuration, testing]
---
# Requirements

Install Docker, Python 3.12 and `uv`, then run `make bootstrap` once to install dependencies and Git hooks.

# Running the service

`make dev` starts PostgreSQL, Redis and the API with auto-reload on port 8000. `make seed` loads sample data.

# Troubleshooting

If the API cannot reach the database, run `docker compose ps` to check that the containers are healthy, then `make reset-db` to recreate the local database.
