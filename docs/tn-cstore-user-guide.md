# tn-cstore user guide

How to grow the content store with the `/tn-cstore-*` commands.

## What this is

A markdown store of saved articles. Each article has the full text, a short summary, tags, and Obsidian links to hub notes (topics, people, tools, concepts). You drop material into `00_Staging/`, run a command, and Claude does the fetching, summarising, tagging and linking.

## Setup

1. Open Claude Code in the repo root. The commands load from `.claude/skills/`.
   New, empty repo (for example one created from the template): run `/tn-cstore-init` first. It creates the folders and data files and asks for your first areas, projects and topics.
2. Open the same folder as an Obsidian vault to browse and use the graph.
3. Python 3 with `requests`, `trafilatura`, `markdownify` and `beautifulsoup4` is needed for fetching (`pip3 install --user -r tools/requirements.txt`). The same file adds `pymupdf4llm`, needed to convert PDF articles.

## Typical session

1. Drop files into `00_Staging/daily-notes/` or `00_Staging/articles/`.
2. Run `/tn-cstore-ingest-daily` or `/tn-cstore-ingest-article`.
3. Answer any question Claude asks (new tag, unclear date, unclear area).
4. Claude commits and pushes to `main`. Pull in Obsidian.

Run `/tn-cstore-status` any time to see what is pending.

## What goes where

| Folder | Content |
|---|---|
| `00_Staging/daily-notes/` | Daily notes with links. Name each `YYYY-MM-DD.md`. |
| `00_Staging/articles/` | Articles as markdown files or PDFs. A PDF is converted to text; after processing the PDF moves to `04_Archive/pdf/`. |
| `raw/` | `<slug>.md` full text (no links) and `<slug>.summary.md` (summary with links). |
| `raw/attachments/` | Images the articles embed. Obsidian saves pasted images in `attachments/`; ingest copies the ones an article uses here. |
| `notes/` | Hub notes and `_index.md`. Generated. |
| `01_Projects/`, `02_Areas/` | Your own project and area notes. Never overwritten. |
| `03_Resources/` | Empty, for files you move in. |
| `04_Archive/daily-notes/` | Daily notes after processing. |

## Commands

### /tn-cstore-init
**Use when:** you start a new store in an empty repo, or another command says the store is not set up.
**Does:** creates the folder layout, empty data files, `tools/para.py` and `tools/descriptions.py` skeletons, a README and the Obsidian attachment setting. Then asks for 1 to 4 areas, up to 4 projects and 5 to 15 starting topics, writes them, builds, checks, commits and pushes. `/tn-cstore-init --minimal` skips the questions.
**Good to know:** it never overwrites a file, so it is safe on an existing store. The first articles still bring vocabulary questions; that settles after 10 to 20 articles.

### /tn-cstore-status
**Use when:** you want to know what is pending or whether the store is healthy.
**Does:** lists staged files, articles without summary or tags, failed links, and runs the health check. Changes nothing.
**Output:** a few lines and the suggested next command.

### /tn-cstore-ingest-daily
**Use when:** you added daily notes to `00_Staging/daily-notes/`.
**You provide:** files named `YYYY-MM-DD.md` containing links (plain URLs, markdown links, or pasted "title + share link" lines).
**Does:**
1. Pulls the latest `main`.
2. Extracts every link and adds new ones to `tools/urls.tsv`.
3. Fetches new pages and converts the HTML to markdown in `raw/`. Images on the page are downloaded to `raw/attachments/` and linked from there; an image that cannot be downloaded keeps its web address. A page already stored gets the new date added instead of a second copy.
4. Reads each new page, writes a summary, picks tags from the existing vocabulary.
5. Adds hub descriptions for any new hub, rebuilds links and hub notes, runs the check.
6. Moves fully processed daily notes to `04_Archive/daily-notes/`.
7. Commits and pushes.
**Asks you:** the date of a file not named `YYYY-MM-DD`; any new topic, person, tool or concept; anything unclear.
**Result:** a report with links found, fetched, failed (listed), new hubs and the questions asked.
**Good to know:** failed links are not an error. They stay in the README "Not fetched" table. A daily note with unfinished links stays in staging until they are done.

### /tn-cstore-ingest-article
**Use when:** you added markdown or PDF article files to `00_Staging/articles/`.
**You provide:** `.md` or `.pdf` files. A front matter `source:` URL and `title:` help. Without them the title comes from the first `# heading` or the file name and the source is `local:<file name>`.
**Does:** copies each file to `raw/<slug>.md` with the text unchanged (a PDF is converted to text first), then does summary, tags, hubs, rebuild, check, commit and push like the daily command. Images the article embeds are copied to `raw/attachments/`, and remote images (web addresses) are downloaded there too (a failed download keeps its web address) and the source copy is removed once the article is fully processed. Removes the staged original once fully processed. A PDF is moved to `04_Archive/pdf/` instead.
**Project hint (optional):** put the file in `00_Staging/articles/<project name>/` (for example `00_Staging/articles/Blog launch/`) or add `project: Blog launch` to its front matter. The article is then attached to that project without a question.
**Without a hint:** after tagging, Claude checks whether the new articles share 3 or more hubs with a project and asks once, for all of them together, whether to attach. No match means no project. One project per article.
**Result:** the summary gets a `project:` link to the project note, and the project note's article list refreshes.
**Asks you:** new vocabulary, unclear classification, and project proposals.

### /tn-cstore-classify
**Use when:** a tag looks wrong, you want to rename, merge or drop a term, or you want specific articles re-tagged.
**You provide:** an article name or a topic (optional): `/tn-cstore-classify Local-LLMs`.
**Does:** shows the vocabulary with counts, proposes the change with old and new tags, applies it after you agree, rebuilds, checks, commits and pushes.
**Asks you:** before any new term and before any rename or merge.

### /tn-cstore-build
**Use when:** you edited `tools/classification.json`, `tools/descriptions.py`, `tools/para.py` or a summary by hand.
**Does:** rebuilds summary links, hub notes and `_index.md`, updates the README fetch table, runs the check, then asks before committing.
**If it says BLOCKED:** an article has no tags, no summary, or a hub has no description. The message names the item. Use `/tn-cstore-classify` or `/tn-cstore-ingest-article` to fix it.

### /tn-cstore-check
**Use when:** before a commit, or when something looks off.
**Checks:** every double-bracket link resolves, full-text files have no backlinks, dates are not links, no duplicated pointer lines, every article has summary and tags, stale hub candidates.
**Output:** `ERROR` lines (must fix) and `WARN` lines (advice). Mechanical errors are fixed by rebuilding.

### /tn-cstore-retry
**Use when:** you want another try at links that failed (403, 429, empty page).
**Does:** retries slowly (4 seconds apart), reports what still fails and why, summarises and tags what came through, regenerates the README "Not fetched" table, commits and pushes.
**Does not:** use archive sites or proxies unless you ask.

### /tn-cstore-assign
**Use when:** a hub belongs to an area or project, or you want a new area or project.
**You provide:** `/tn-cstore-assign Obsidian to Knowledge system`, `/tn-cstore-assign article <name> to <project>` (attach one article to one project, `-` removes it), or `/tn-cstore-assign new project <name>`.
**Does:** edits `tools/para.py`, rebuilds, checks, commits and pushes. For a new project or area it asks for the outcome (project, has an end) or the ongoing responsibility (area, no end) in one sentence, then creates the note once in `01_Projects/` or `02_Areas/`.
**Rule of thumb:** can it be crossed off, then Project. A standard to keep up with no end, then Area. Otherwise Resource.

### /tn-cstore-archive
**Use when:** a tool was replaced, an event is over, a project finished, or processed daily notes are still in staging.
**Does:** moves finished daily notes to `04_Archive/daily-notes/`; lists archive candidates among hubs; archives a hub (sets `para: archive`, `status: stale`) only after you confirm. Nothing is deleted.
**Note:** a hub's age counts from the day the note was saved, so Claude confirms with you every time.

## Cheat sheet

| I want to | Run |
|---|---|
| Start a new store | `/tn-cstore-init` |
| See what is pending | `/tn-cstore-status` |
| Add daily notes | drop in `00_Staging/daily-notes/`, `/tn-cstore-ingest-daily` |
| Add markdown or PDF articles | drop in `00_Staging/articles/`, `/tn-cstore-ingest-article` |
| Fix or change tags | `/tn-cstore-classify` |
| Retry failed links | `/tn-cstore-retry` |
| Put a hub in an area or project | `/tn-cstore-assign` |
| Retire an outdated hub | `/tn-cstore-archive` |
| Regenerate after hand edits | `/tn-cstore-build` |
| Verify everything | `/tn-cstore-check` |

## Rules Claude follows

- Full text in `raw/` is never edited and has no backlinks. Only the summaries carry links. One exception: Obsidian backlinks (double-bracket links) that arrive inside a staged article are unwrapped to plain text. Image embeds stay as they are, and the image files live in `raw/attachments/`.
- Dates are plain text, not links.
- A hub exists for every topic and person, and for tools and concepts in 2 or more articles. A person is linked only if the article is about them.
- Names are English. Existing vocabulary is reused first.
- New vocabulary, an unclear area or project, or an unclear date: Claude asks, it does not guess.
- An article has at most one project. Project proposals are always confirmed, a staging subfolder or `project:` field counts as your confirmation.
- The article list in each project note sits between `cstore:articles` markers and is refreshed by the scripts. Do not edit that block.
- Summaries state when a page was only a teaser, paywalled or empty.
- Before every commit the check must show zero errors. Claude pulls first, never force-pushes.

## Troubleshooting

| Symptom | Cause and fix |
|---|---|
| `BLOCKED. Unclassified: [...]` | An article lacks tags. Run `/tn-cstore-classify` on it. |
| `BLOCKED. Missing hub descriptions` | A new hub needs a line in `tools/descriptions.py`. `/tn-cstore-build` adds it after asking. |
| A daily note stays in staging | Some of its links are not summarised yet. Run `/tn-cstore-status`. |
| Many links fail with 403 or 429 | The site blocks scripts. `/tn-cstore-retry` later, or leave them listed. |
| Push rejected | You pushed from Obsidian in the meantime. Claude merges (no force) and pushes again. |
| `fetch.py` prints a usage line | It needs `--new`, `--retry` or `--all`. `--all` refetches everything, use with care. |
| Unresolved link error | A summary points to a note that is gone. `/tn-cstore-build` regenerates the hubs. |

## Under the hood

The commands call scripts in `tools/`: `init.py` (set up), `ingest.py` (staging intake, `vocab`, `classify`, `summary`, `finish`, `status`), `fetch.py`, `link.py`, `check.py`. You can run them yourself from the repo root. The full rules for Claude are in `.claude/skills/tn-cstore/RULES.md`. Decisions specific to one vault go in `LOCAL.md` next to it.
