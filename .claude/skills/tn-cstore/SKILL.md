---
name: tn-cstore
description: Content store for saved links and articles in this repo. Overview and rules for the tn-cstore-* commands that grow it. Load when the user mentions the content store, staging, hub notes, backlinks, or any tn-cstore command.
---

# tn-cstore: content store

A markdown store of saved articles, summarised, tagged and linked for Obsidian. Read `RULES.md` in this folder before changing anything (and `LOCAL.md` if it exists). The human-facing guide is `docs/tn-cstore-user-guide.md`.

## Commands

| Command | What it does |
|---|---|
| `/tn-cstore-init` | Set up a new store in an empty repo: folders, data files, first areas, projects and vocabulary. |
| `/tn-cstore-status` | What is waiting in staging, unsummarised, unclassified, failed. Runs the health check. |
| `/tn-cstore-ingest-daily` | Process daily notes in `00_Staging/daily-notes/`: links, fetch, summary, tags, hubs, archive. |
| `/tn-cstore-ingest-article` | Process markdown articles in `00_Staging/articles/`: add to `raw/`, summary, tags, hubs. |
| `/tn-cstore-classify` | Tag or re-tag articles, manage vocabulary (asks before adding new terms). |
| `/tn-cstore-build` | Rebuild summaries' links, hub notes, `_index.md`, then check. |
| `/tn-cstore-check` | Health check: links resolve, no backlinks in full text, nothing unclassified. |
| `/tn-cstore-retry` | Retry links that failed to fetch, then summarise what came through. |
| `/tn-cstore-assign` | Put a hub into an area or project, or create a new area or project. |
| `/tn-cstore-archive` | Archive stale hubs and finished daily notes. |

All commands run from the repo root. Scripts live in `tools/` (`init.py`, `ingest.py`, `fetch.py`, `link.py`, `check.py`). If `tools/classification.json` is missing, the store is not set up yet: run `/tn-cstore-init`.
