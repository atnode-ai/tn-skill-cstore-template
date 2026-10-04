---
name: tn-cstore-assign
description: Assign a hub note or a single article to a PARA area or project, or create a new area or project. Use when the user says a topic belongs to an area or project, or wants a new project or area note.
argument-hint: "<hub> to <area or project>  |  article <name> to <project>  |  new project|area <name>"
disable-model-invocation: true
---

Read `.claude/skills/tn-cstore/RULES.md` first. From the repo root:

1. Existing hub to existing area or project: add the hub name to the `hubs` list of that entry in `tools/para.py` (`AREAS` or `PROJECTS`). A hub has at most one area, any number of projects.
2. New project or area: ask for the outcome (project, must have an end) or the ongoing responsibility (area, no end date) in one sentence, plus the hubs. Add an entry in `tools/para.py`. The note file in `01_Projects/` or `02_Areas/` is created once by `link.py`; existing files are never touched, so also edit the existing note by hand if you only changed `para.py`.
3. One article to a project: `python3 tools/ingest.py attach <stem or unique part of it> "<project>"` (one project per article; `-` instead of a project removes it). The article list inside the project note refreshes on `link.py` between the `cstore:articles` markers. Never edit that block by hand.
4. If the right place is unclear, ask (AskUserQuestion) with the options and what each means. PARA test: can it be crossed off, then Project; is there a standard to keep up with no end, then Area; otherwise Resource.
5. `python3 tools/link.py`, `python3 tools/check.py`, commit and push.
