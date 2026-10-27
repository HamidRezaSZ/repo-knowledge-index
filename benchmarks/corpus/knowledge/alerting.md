---
id: alerting
title: Alerting and On-call
summary: When alerts page someone, the on-call rotation, incidents and postmortems.
aliases: [on-call, incidents, pager]
tags: [operations, observability]
related: [tracing, deployment]
---
# Paging rules

An alert pages the on-call engineer only when users are affected: an error rate above 2% for 5 minutes, or p95 latency above 1 second for 10 minutes. Other alerts go to the team channel.

# Rotation

On-call shifts last one week and hand over on Monday at 10:00. The secondary engineer takes any page the primary does not acknowledge within 15 minutes.

# Incident response

Declare an incident in the #incidents channel, name an incident lead and post updates every 30 minutes. Fix the user impact first and investigate the cause afterwards.

# Postmortems

Every incident that paged someone gets a blameless postmortem within five working days, with action items tracked as tickets.
