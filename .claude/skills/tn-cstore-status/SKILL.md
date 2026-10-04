---
name: tn-cstore-status
description: Show the state of the content store: staged files, articles without summary or classification, failed links, and the health check result. Use when the user asks what is pending or whether the store is healthy.
---

Read `.claude/skills/tn-cstore/RULES.md` once. Then run from the repo root:

```
python3 tools/ingest.py status
python3 tools/check.py
```

Report in a few lines: what is waiting in `00_Staging`, what lacks a summary or classification, how many links failed to fetch, errors and warnings from the check. Suggest the next command (`/tn-cstore-ingest-daily`, `/tn-cstore-ingest-article`, `/tn-cstore-classify`, `/tn-cstore-retry`). Change nothing.
