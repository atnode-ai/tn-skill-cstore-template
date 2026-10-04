# Changelog

Releases of the tn-cstore template. To update a store made from an earlier version, copy from the new version the scripts `tools/*.py` except `para.py` and `descriptions.py`, plus `tools/requirements.txt`, `.claude/skills/tn-cstore*/` (keep your own `LOCAL.md`) and `docs/`. Never copy the data files (`tools/para.py`, `tools/descriptions.py`, `tools/*.json`, `tools/urls.tsv`): they hold your store. Then run `python3 tools/init.py` and `python3 tools/check.py`.

## v1.0.1 (2026-10-04)

- New stores ignore the whole .obsidian/ folder in .gitignore (was only workspace.json)

## v1.0.0 (2026-10-04)

- First tagged release of the tn-cstore content store template: start with /tn-cstore-init
- Commands: init, status, ingest-daily, ingest-article, classify, build, check, retry, assign, archive
- User guide example for /tn-cstore-assign is now generic
