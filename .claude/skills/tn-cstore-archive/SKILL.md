---
name: tn-cstore-archive
description: Archive stale hub notes (outdated tools, finished events) and finished daily notes. Use when check.py shows archive candidates, a tool was replaced, a project ended, or processed daily notes are still in staging.
disable-model-invocation: true
---

Read `.claude/skills/tn-cstore/RULES.md` first. From the repo root:

1. Daily notes: `python3 tools/ingest.py finish` moves fully processed daily notes to `04_Archive/daily-notes/`. Notes with unfinished links stay.
2. Hubs: `python3 tools/check.py` lists archive candidates (entities and concepts whose newest article is over 365 days old; people and topics are evergreen). Age counts from the date a note was saved, so confirm with the user before archiving. Never archive on age alone.
3. To archive a hub: add `"<Hub>": "<reason>"` to `ARCHIVE` in `tools/para.py` (sets `para: archive`, `status: stale`, shows it under Archive in the index). To restore, remove the entry.
4. Finished project: ask the user, then add the project name to a note in `04_Archive/` by moving its file with `git mv` and update `tools/para.py` to drop it from `PROJECTS` so it is not recreated.
5. `python3 tools/link.py`, `python3 tools/check.py`, commit and push.

Ask before every archive decision; archiving only changes properties and file location, nothing is deleted.
