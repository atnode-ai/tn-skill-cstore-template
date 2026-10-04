#!/usr/bin/env python3
"""Health check of the content store. Exit code 1 if any hard problem is found."""
import re, glob, os, json, datetime, sys, collections
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
if not (ROOT / "tools/classification.json").exists(): sys.exit("No content store here yet. Run: python3 tools/init.py")
md = [Path(f) for f in glob.glob(str(ROOT / "**/*.md"), recursive=True) if "/.obsidian/" not in f and "/00_Staging/" not in f and not re.search(r"/01_Projects/[^/]+/", f)]  # project working folders are the user's files, not checked
names = {f.stem for f in md}
errors, warns = [], []
LINK = re.compile(r"(?<![\\!])\[\[([^\]|#]+)(?:[|#][^\]]*)?\]\]")
EMBED = re.compile(r"(?<!\\)!\[\[([^\]|#]+)(?:[|#][^\]]*)?\]\]")
MDIMG = re.compile(r"!\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
IMG_EXT = (".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".avif", ".bmp")
RAW_ATT = ROOT / "raw/attachments"
referenced = set()
for f in md:
    t = f.read_text(); rel = f.relative_to(ROOT)
    full = rel.parts[0] == "raw" and not f.name.endswith(".summary.md")
    for m in LINK.finditer(t):
        if full: errors.append(f"{rel}: full text must have no backlinks ([[{m.group(1)}]])"); break
        if m.group(1) not in names and not str(rel).startswith("00_Staging"): errors.append(f"{rel}: unresolved [[{m.group(1)}]]")
    if full:
        for m in EMBED.finditer(t):
            n = m.group(1).strip()
            if not n.lower().endswith(IMG_EXT): errors.append(f"{rel}: full text must have no backlinks (![[{n}]])"); break
        from urllib.parse import unquote
        for r in [m.group(1).strip() for m in EMBED.finditer(t)] + [unquote(m.group(1)) for m in MDIMG.finditer(t) if re.match(r"(\./)?attachments/", unquote(m.group(1)))]:
            if not r.lower().endswith(IMG_EXT): continue
            referenced.add(Path(r).name)
            if not (RAW_ATT / Path(r).name).is_file(): errors.append(f"{rel}: image {Path(r).name} is not in raw/attachments/")
    if re.search(r"^daily_note:.*\[\[", t, re.M): errors.append(f"{rel}: date must not be a backlink")
    if len(re.findall(r"^(?:Summary|Full text):", t, re.M)) > 1: errors.append(f"{rel}: duplicated pointer line")
C = json.load(open(ROOT / "tools/classification.json"))
stems = [f.stem for f in md if f.parent.name == "raw" and not f.name.endswith(".summary.md")]
for s in stems:
    if not (ROOT / f"raw/{s}.summary.md").exists(): errors.append(f"raw/{s}: no summary")
    if s not in C: errors.append(f"raw/{s}: not classified")
    else:
        if not C[s]["topics"]: warns.append(f"raw/{s}: no topic")
for s in C:
    if s not in stems: errors.append(f"classification.json: {s} has no file")
# projects
sys.path.insert(0, str(ROOT / "tools"))
from para import PROJECTS
START, END = "<!-- cstore:articles -->", "<!-- /cstore:articles -->"
for s_, v in C.items():
    pr = v.get("project")
    if pr and pr not in PROJECTS: errors.append(f"raw/{s_}: project {pr!r} not in tools/para.py")
    sf = ROOT / f"raw/{s_}.summary.md"
    if sf.exists():
        m = re.search(r'^project: "\[\[(.*)\]\]"', sf.read_text(), re.M)
        if (m.group(1) if m else "") != (pr or ""): errors.append(f"raw/{s_}: summary project differs from classification (run link.py)")
for n in PROJECTS:
    f = ROOT / "01_Projects" / f"{n}.md"
    if not f.exists(): errors.append(f"01_Projects/{n}.md missing")
    elif START not in f.read_text() or END not in f.read_text(): errors.append(f"01_Projects/{n}.md has no article block markers (run link.py)")
# hubs
today = datetime.date.today()
for f in (ROOT / "notes").glob("*.md"):
    if f.name == "_index.md": continue
    fm = re.search(r"^---\n(.*?)\n---", f.read_text(), re.S).group(1)
    last = re.search(r"last_article: (\S+)", fm); para = re.search(r"para: (\S+)", fm); typ = re.search(r"type: (\S+)", fm)
    # people and topics are evergreen; entities and concepts can go stale (age = days since the note was saved)
    if last and para and para.group(1) == "resource" and typ and typ.group(1) in ("entity", "concept"):
        age = (today - datetime.date.fromisoformat(last.group(1))).days
        if age > 365: warns.append(f"hub {f.stem}: newest article {age} days old, archive candidate (tn-cstore-archive)")
# one-article terms (informational)
cnt = [collections.Counter(), collections.Counter()]
for v in C.values(): cnt[0].update(set(v["entities"])); cnt[1].update(set(v["concepts"]))
res = json.load(open(ROOT / "tools/results.json"))
for a in sorted(RAW_ATT.glob("*")) if RAW_ATT.is_dir() else []:
    if a.is_file() and not a.name.startswith(".") and a.name not in referenced: warns.append(f"raw/attachments/{a.name}: not referenced by any article")
print(f"{len(stems)} articles, {len([f for f in (ROOT/'notes').glob('*.md') if f.name != '_index.md'])} hubs, {sum(1 for x in res if not x['ok'])} links not fetched")
for e in errors: print("ERROR", e)
for w in warns: print("WARN ", w)
print("OK" if not errors else f"{len(errors)} errors")
raise SystemExit(1 if errors else 0)
