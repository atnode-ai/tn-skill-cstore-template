---
name: tn-cstore-classify
description: Tag or re-tag articles in the content store and manage the vocabulary (topics, people, entities, concepts). Asks before adding new terms. Use when tags look wrong, a term should be renamed, merged or dropped, or the user asks to classify specific articles.
argument-hint: "[article stem or topic to review]"
disable-model-invocation: true
---

Read `.claude/skills/tn-cstore/RULES.md` first. From the repo root:

1. `python3 tools/ingest.py vocab` shows the vocabulary with counts. If an argument names an article or a topic, open the matching `raw/*.summary.md` and `notes/<topic>.md`.
2. Propose the change before making it: article tags, a rename, a merge, a drop. Show old and new tags and the reason. For anything new, ask (AskUserQuestion).
3. Apply after approval:
   - tags per article: `python3 tools/ingest.py classify <stem> --topics ... --people ... --entities ... --concepts ...` (this replaces all tags of that article, but keeps its project unless you pass `--project "<name>"`)
   - rename or merge a term: edit `tools/classification.json`, `tools/descriptions.py` and `tools/para.py` consistently (search the term in all three)
   - new or changed hub text: `tools/descriptions.py`
4. `python3 tools/link.py`, `python3 tools/check.py`, commit and push.

Rules to keep: people are linked only if the article is about them; entities and concepts get a hub only from 2 articles; English names; a person is never also a topic.
