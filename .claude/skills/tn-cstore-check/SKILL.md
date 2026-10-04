---
name: tn-cstore-check
description: Health check of the content store: all [[links]] resolve, full-text files have no backlinks, dates are not links, every article has summary and classification, stale hub candidates. Use before commits or when something looks off.
---

Run `python3 tools/check.py` from the repo root and report.

- `ERROR` lines are hard problems (unresolved link, backlink in full text, missing summary or classification, duplicated pointer line). Offer the fix, apply it only for mechanical issues (rerun `python3 tools/link.py`).
- `WARN` lines are advice (for example archive candidates). Do not act on them; suggest `/tn-cstore-archive`.

Exit code 1 means errors.
