# 00_Staging

Inbox. Drop files here; they get processed and moved out. Nothing stays here.

Run `/tn-cstore-ingest-daily` for `daily-notes/` and `/tn-cstore-ingest-article` for `articles/` (Claude Code, repo root).

## daily-notes/

Daily notes (`YYYY-MM-DD.md`) that contain links.

1. Extract every link.
2. Fetch each page, convert it to markdown, write it to `raw/<slug>.md`.
3. Write `raw/<slug>.summary.md` with front matter tags and inline backlinks.
4. Update the hub notes in `notes/`.
5. Move the processed daily note to `04_Archive/daily-notes/`. It gets no backlinks.

## articles/

Articles as markdown files (`.md`) or PDFs (`.pdf`).

Optional project hint: put the file in `articles/<project name>/` or add `project: <name>` to its front matter. Without a hint, I propose a project when the article shares 3 or more hubs with it and ask once before attaching. One project per article.

1. Markdown is copied into `raw/<slug>.md` (text unchanged, no backlinks). A PDF is converted to markdown first (text only, images dropped; needs `pip3 install --user pymupdf4llm`). A scanned PDF without text is skipped and reported.
2. Write `raw/<slug>.summary.md` with tags and backlinks, update the hub notes.
3. Images the article embeds (`![[x.png]]`, `![](attachments/x.png)`) are copied from `attachments/` or from next to the file into `raw/attachments/`; the source copy is removed with the original in step 4.
4. Remove the original from staging. A processed PDF moves to `04_Archive/pdf/` instead, so the source file is kept.

## Classification rule

Each file gets topics, people, entities and concepts from the existing vocabulary (`python3 tools/ingest.py vocab`, `notes/_index.md`).
If the right tag, area, project or destination is unclear, or a term would be new, ask before moving. Never guess.
