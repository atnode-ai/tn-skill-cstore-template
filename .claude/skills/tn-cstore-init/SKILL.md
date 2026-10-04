---
name: tn-cstore-init
description: Set up a new content store in an empty or fresh repo: folder layout, empty data files, first areas, projects and starting vocabulary, then a first build and check. Use when the user wants to start a store, bootstrap the template, or when the other tn-cstore commands say the store is not set up.
argument-hint: "[--minimal]  (skip the questions, set up folders and files only)"
disable-model-invocation: true
---

Read `.claude/skills/tn-cstore/RULES.md` first. Run everything from the repo root.

1. `python3 tools/init.py --check`. If it prints `complete` and `tools/classification.json` already has articles, this is an existing store: say so and stop (offer `/tn-cstore-status`).
2. `python3 tools/init.py` creates the missing folders (with `.gitkeep`), empty data files, skeleton `tools/para.py` and `tools/descriptions.py`, `README.md`, `.gitignore` and `.obsidian/app.json` (attachments folder). It never overwrites a file.
3. `pip3 install --user -r tools/requirements.txt` if `python3 -c "import requests, trafilatura, markdownify, bs4"` fails. PDF support (`pymupdf4llm`) is optional; say so if it fails.
4. Unless the argument is `--minimal`, set up the PARA layer and vocabulary. Ask in at most 2 AskUserQuestion rounds, with suggestions the user can accept or replace:
   - **Areas** (1 to 4): ongoing responsibilities with no end date. One sentence each.
   - **Projects** (0 to 4): outcomes that can be crossed off. One sentence each.
   - **Starting topics** (5 to 15): the subjects the user expects to save articles about, plus any people they follow. Topics are broad (`Macro`, `Local-LLMs`), not single articles.
   Then write them:
   - `tools/descriptions.py`: one line per term in `D`, `"Name": ("topic"|"person", "one-line description")`. English, canonical names (RULES.md, Linking rules). Do not seed entities or concepts: they earn a hub from 2 articles.
   - `tools/para.py`: each area and project with `text` (`Ongoing responsibility: ...` / `Outcome: ...`) and the `hubs` it covers. A hub has at most one area. Topics in no area can go into a `RESOURCE_GROUPS` group.
   Show the result in a few lines before writing. Never invent areas or projects the user did not confirm.
5. `python3 tools/link.py` (creates the notes in `01_Projects/` and `02_Areas/` and `notes/_index.md`), then `python3 tools/check.py`. Zero errors required.
6. Commit (`Set up content store`) and push to the default branch (RULES.md, Safety). If the repo has no remote yet, say so and leave it committed locally.
7. Report what was created, then the next step: open the repo root as an Obsidian vault, drop daily notes (`YYYY-MM-DD.md` with links) into `00_Staging/daily-notes/` or articles (`.md`, `.pdf`) into `00_Staging/articles/`, and run `/tn-cstore-ingest-daily` or `/tn-cstore-ingest-article`. Mention that the first articles will bring more vocabulary questions, and that this settles after 10 to 20 articles.

`init.py` is safe to run again on an existing store: it only adds what is missing.
