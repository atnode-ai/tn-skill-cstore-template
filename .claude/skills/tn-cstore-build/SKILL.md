---
name: tn-cstore-build
description: Regenerate summaries' links and front matter, hub notes and notes/_index.md from tools/classification.json, descriptions.py and para.py, then run the health check. Use after any manual edit of those files or of summaries.
disable-model-invocation: true
---

From the repo root:

```
git pull --no-rebase origin main
python3 tools/link.py
python3 tools/check.py
```

`link.py` is re-runnable. It stops with `BLOCKED` when an article is unclassified, a summary is missing, or a hub lacks a description in `tools/descriptions.py`; fix that first (see `/tn-cstore-ingest-article`, `/tn-cstore-classify`). It never overwrites existing notes in `01_Projects/` or `02_Areas/`.

If the check passes, show `git status --short` summary and ask before committing. Commit and push per RULES.md.
