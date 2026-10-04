---
name: tn-cstore-retry
description: Retry links that failed to fetch (403, 429, empty), then summarise and classify whatever came through. Use when the user asks to retry failed links or after a site changes its blocking.
disable-model-invocation: true
---

Read `.claude/skills/tn-cstore/RULES.md` first. From the repo root:

1. `git pull --no-rebase origin main`, then `python3 tools/fetch.py --retry` (4 s between requests; slow on purpose). Retried pages get their images downloaded into `raw/attachments/` like any new fetch.
2. Compare the failure count before and after. List what still fails and the reason (`tools/results.json`, `note` or `status`). Do not use other routes (archives, proxies) unless the user asks.
3. For each newly fetched page, run steps 5 to 6 of `/tn-cstore-ingest-daily` (summary, classify, hubs, `link.py`, `check.py`).
4. Commit and push. The README's "Not fetched" table is stale after a retry: regenerate it from `tools/results.json` (date, reason, URL for every `ok: false`).
