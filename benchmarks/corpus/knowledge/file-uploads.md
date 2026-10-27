---
id: file-uploads
title: File Uploads
summary: Uploading files to object storage with presigned URLs, size limits and virus scanning.
aliases: [uploads, s3]
tags: [storage]
related: [privacy]
---
# Presigned uploads

Clients ask `POST /v2/uploads` for a presigned S3 URL and upload the file straight to the bucket, so large files never pass through the API servers.

# Limits

Files may be at most 25 MB. Only PDF, PNG and JPEG are accepted, checked by content type and by the file's first bytes.

# Virus scanning

A background job scans each upload, and the file stays under the `quarantine/` prefix until the scan passes.
