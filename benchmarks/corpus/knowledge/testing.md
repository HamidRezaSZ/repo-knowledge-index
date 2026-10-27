---
id: testing
title: Testing
summary: Test layers, test data and flaky tests.
aliases: [tests]
tags: [quality, ci]
related: [local-development]
---
# Test layers

Unit tests cover pure functions and finish in under a minute. Integration tests use real PostgreSQL and Redis containers started by `docker compose -f compose.test.yml up`.

# Test data

Build test data with the factories in `tests/factories.py` instead of shared JSON fixtures, so each test states only the fields it needs.

# Flaky tests

A test that fails and then passes without a code change is quarantined with `@pytest.mark.flaky` and gets a ticket. Quarantined tests must be fixed or deleted within two weeks.

# Coverage

A pull request must not lower the line coverage of the files it changes below 80%.
