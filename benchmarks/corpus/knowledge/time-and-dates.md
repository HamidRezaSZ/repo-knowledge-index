---
id: time-and-dates
title: Time Zones and Timestamps
summary: How dates and times are stored and shown.
aliases: [timezones, timestamps]
tags: [conventions]
related: []
---
# Storage

All timestamps are stored in UTC as `timestamptz`. Never store a local time without its offset.

# Display

Convert to the user's time zone only in the client, using the zone saved in their profile.

# Business days

Payout schedules skip weekends and the bank holidays listed in `calendars/holidays.yaml`.
