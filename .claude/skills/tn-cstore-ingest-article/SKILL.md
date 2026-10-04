---
name: tn-cstore-ingest-article
description: Add markdown articles dropped in 00_Staging/articles/ to the store: copy to raw/, write summary, classify, update hub notes. Use when the user adds article files to staging or says ingest articles.
disable-model-invocation: true
---

Read `.claude/skills/tn-cstore/RULES.md` first. Run all commands from the repo root.

1. `git pull --no-rebase origin main`.
2. `python3 tools/ingest.py article` copies each staged `.md` to `raw/<slug>.md` (a staged `.pdf` is converted to markdown first; a scanned PDF with no text is skipped, tell the user it needs OCR) (text unchanged, front matter `source`, `title`, `daily_note` = intake date unless the file has its own). The original stays in staging until `finish`. Each image the article embeds (`![[x.png]]`, `![](attachments/x.png)`) is copied from `attachments/` (or from next to the file in staging) to `raw/attachments/`, and printed as `image ... -> raw/attachments/`. Remote images (`![](https://...)`) are downloaded to `raw/attachments/` as well and the link is pointed at the file (`remote images: N downloaded, M failed`); failed ones keep their URL. `IMAGE MISSING` or `IMAGE CONFLICT` lines need a word to the user (missing file, or a different file with that name already exists). A file in a subfolder `00_Staging/articles/<project name>/`, or with `project: <name>` in its front matter, carries a project hint (printed as `[project hint: ...]`).
3. For each new file, do steps 5 to 6 of `/tn-cstore-ingest-daily`: read it, choose tags from `python3 tools/ingest.py vocab` (ask if new or unclear), write the summary with `tools/ingest.py summary`, `tools/ingest.py classify`, add a line to `tools/descriptions.py` for any new hub. If there is a hint, add `--project "<name>"` to `classify` (a hint is explicit, no confirmation needed; an unknown project name stops with an error, then ask).
4. Projects without a hint: after classifying all new files, run `python3 tools/ingest.py suggest <stem> ...`. `SUGGEST` or `TIE` lines are proposals (3 or more shared hubs with a project). Ask once, in a single AskUserQuestion, for all proposed files together ("These N look like <project>. Attach?") and apply with `classify --project` or `ingest.py attach <stem> <project>`. One project per article, never attach without confirmation, no proposal means no project.
5. If the article has no source URL, the source is `local:<file name>`. Ask the user for the URL only if it is needed to tell two files apart.
6. `python3 tools/link.py`, `python3 tools/check.py` (zero errors), `python3 tools/ingest.py finish` (removes staged originals that are fully processed, and the source copies of their images; PDFs move to `04_Archive/pdf/`).
7. Commit and push. Report: files added, images moved, tags chosen, projects attached, new hubs, questions asked.

Never edit the article body in `raw/`, except to unwrap `[[backlinks]]` that came with the staged file (see RULES.md). Leave image embeds (`![[x.png]]`) alone. The only other body change is the image URL replaced by the downloaded file (`attachments/...`). Never put backlinks in it.
