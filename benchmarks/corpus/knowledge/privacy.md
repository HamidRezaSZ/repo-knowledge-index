---
id: privacy
title: Privacy and Data Retention
summary: Where personal data lives, deletion requests and retention periods.
aliases: [gdpr, data-retention]
tags: [compliance, security]
related: [logging, backups]
---
# Personal data

Personal data is stored only in the `accounts` and `profiles` tables; other tables refer to users by ID.

# Deletion requests

When a user asks to delete their account, the `erase_user` job removes their personal data within 30 days and replaces it in historical records with anonymous placeholders.

# Retention periods

Invoices are kept for 10 years because of tax law. Inactive accounts are deleted after 3 years, with a warning email 30 days before.
