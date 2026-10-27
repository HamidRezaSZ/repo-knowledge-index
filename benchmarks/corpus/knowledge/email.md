---
id: email
title: Email and Notifications
summary: Sending transactional email and notification preferences.
aliases: [notifications, mail]
tags: [messaging]
related: [background-jobs]
---
# Sending email

Transactional email is sent through Postmark from a background job, never inside the web request. Templates live in `templates/email/` and are written in MJML.

# Preferences

Users choose which notifications they receive in their profile. Security messages, such as password resets, ignore these choices.

# Bounces

Addresses that hard-bounce twice are marked undeliverable and skipped until the user confirms a new address.
