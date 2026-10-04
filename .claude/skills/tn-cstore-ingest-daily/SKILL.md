---
name: tn-cstore-ingest-daily
description: Process daily notes dropped in 00_Staging/daily-notes/: extract links, fetch and convert pages to markdown, write summaries, classify, update hub notes, archive the daily note. Use when the user adds daily notes to staging or says ingest daily notes.
disable-model-invocation: true
---

Read `.claude/skills/tn-cstore/RULES.md` first. Run all commands from the repo root.

1. `git pull --no-rebase origin main`.
2. `python3 tools/ingest.py daily`. If it prints `ASK:` lines, ask for the date of those notes (AskUserQuestion), rename the file to `YYYY-MM-DD.md`, rerun.
3. `python3 tools/fetch.py --new`. It fetches only new links, reuses pages already stored (adding the new date), and records failures in `tools/results.json`. It also downloads each page's images into `raw/attachments/` and links them there (`attachments/<article>-<hash>.<ext>`); images that fail keep their remote URL.
4. `python3 tools/ingest.py status` lists new `raw/` files without summary or classification.
5. For each new page: read `raw/<stem>.md` (all of it if short, the opening, headings and ending if long), then
   - `python3 tools/ingest.py vocab` and pick tags from existing vocabulary.
   - If a new topic, person, entity or concept is needed, or the right tag is unclear: stop and ask (RULES.md, "Ask, do not guess").
   - `echo "<summary>" | python3 tools/ingest.py summary <stem>` (style rules in RULES.md).
   - `python3 tools/ingest.py classify <stem> --topics a,b --people x --entities y --concepts z`.
   - If a new hub appears (topic, person, or entity or concept now in 2+ articles), add one line for it to `tools/descriptions.py` (`"Name": ("type", "description")`).
6. Projects: run `python3 tools/ingest.py suggest <new stems>`. For `SUGGEST` or `TIE` lines ask once for all of them together and apply with `ingest.py attach <stem> <project>`. One project per article, never attach without confirmation.
7. `python3 tools/link.py` then `python3 tools/check.py`. Fix every error. `link.py` prints `BLOCKED` with the missing items if something is unfinished.
8. `python3 tools/ingest.py finish` archives daily notes whose links are all done to `04_Archive/daily-notes/`. Notes with unfinished or failed links stay.
9. Commit and push (see RULES.md, Safety). Report: links found, fetched, failed (list them), new hubs, questions you asked.

Failed links are not an error: they stay listed in `tools/results.json`. Offer `/tn-cstore-retry`.
