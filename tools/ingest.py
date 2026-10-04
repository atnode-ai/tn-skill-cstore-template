#!/usr/bin/env python3
"""Intake from 00_Staging.
  ingest.py daily      extract links from staged daily notes -> urls.tsv (then run fetch.py --new)
  ingest.py article    copy staged markdown articles -> raw/<slug>.md (text unchanged except remote image links, see below); staged PDFs are converted to markdown first;
                       images the article embeds are copied to raw/attachments/ (looked up in attachments/, then next to the file in staging); remote images (![](https://...)) are downloaded there too and the link points at the file
  ingest.py finish     archive finished daily notes, delete finished staged articles and the source copies of their images
  ingest.py status     what is waiting, unclassified or unsummarised
  ingest.py vocab      known topics, people, entities, concepts with article counts
  ingest.py classify <stem> --topics a,b --people x --entities y --concepts z [--project P]
  ingest.py suggest [stem ...]   propose a project for classified articles that have none (hint or tag overlap)
  ingest.py attach <stem-part> <project|->   set or clear the project of one article
  ingest.py summary <stem>   write raw/<stem>.summary.md from stdin (front matter is built here)
Nothing is deleted or moved until `finish` (images are copied first, the source copy goes at `finish`), and `finish` only touches items that are fully processed."""
import re, sys, csv, json, hashlib, shutil, glob, datetime
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
ST_D, ST_A = ROOT / "00_Staging/daily-notes", ROOT / "00_Staging/articles"
ARCH = ROOT / "04_Archive/daily-notes"
ARCH_PDF = ROOT / "04_Archive/pdf"
STATE = ROOT / "tools/ingest-state.json"
if not (ROOT / "tools/classification.json").exists(): sys.exit("No content store here yet. Run: python3 tools/init.py")
ATT, RAW_ATT = ROOT / "attachments", ROOT / "raw/attachments"
IMG_EXT = (".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".avif", ".bmp")
EMBED = re.compile(r"(?<!\\)!\[\[([^\]|#]+)(?:[|#][^\]]*)?\]\]")
MDIMG = re.compile(r"!\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
URL = re.compile(r"https?://[^\s<>\")\]]+")
def staged(d): return sorted(p for p in d.rglob("*") if p.is_file() and p.suffix.lower() in (".md", ".pdf") and p.name != "README.md" and (p.suffix.lower() == ".md" or d == ST_A))
def image_refs(text):
    """Local image names an article body embeds: ![[x.png]], ![[x.png|300]] or ![](attachments/x.png). Other markdown image paths (fetched web pages) are ignored."""
    from urllib.parse import unquote
    refs = [m.group(1).strip() for m in EMBED.finditer(text)]
    refs += [unquote(m.group(1)) for m in MDIMG.finditer(text) if re.match(r"(\./)?attachments/", unquote(m.group(1)))]
    out = []
    for r in refs:
        if r.lower().endswith(IMG_EXT) and r not in out: out.append(r)
    return out

def take_images(text, src_dir, stem, s):
    """Copy the images an article embeds into raw/attachments/. Search order: attachments/, the staged file's folder (and subfolders), raw/attachments/ (already taken).
    The source copy is removed by `finish`. The article body is not changed: Obsidian finds `![[x.png]]` by file name, and `attachments/x.png` resolves from raw/."""
    for ref in image_refs(text):
        name = Path(ref).name
        dest = RAW_ATT / name
        src = next((c for c in [ATT / name, src_dir / ref, *src_dir.rglob(name)] if c.is_file()), None)
        if src is None:
            print(f"  image {name} already in raw/attachments/" if dest.exists() else f"  IMAGE MISSING {ref} (not in attachments/ or next to the file)"); continue
        RAW_ATT.mkdir(parents=True, exist_ok=True)
        if dest.exists() and dest.read_bytes() != src.read_bytes():
            print(f"  IMAGE CONFLICT {name}: raw/attachments/ has a different file with this name; not copied"); continue
        if not dest.exists(): shutil.copy2(src, dest)
        s.setdefault("images", {}).setdefault(stem, [])
        rel = str(src.relative_to(ROOT))
        if rel not in s["images"][stem]: s["images"][stem].append(rel)
        print(f"  image {name} -> raw/attachments/")
def remote_images(out, body, src, stem):
    """Download the remote images (![](https://...)) of a staged article into raw/attachments/ and point the links at them.
    Relative paths resolve against the article's source URL when it has one. Failed downloads keep their URL. Only the URL inside the link changes."""
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent)); from images import localize_images
    except ImportError as e:
        print(f"  remote images not downloaded ({e}); pip3 install --user requests"); return body
    if not re.search(r"!\[[^\]]*\]\(<?(https?:)?//", body) and not (src.startswith("http") and re.search(r"!\[[^\]]*\]\(<?[^)\s>]", body)): return body
    new, ok, bad = localize_images(body, src if src.startswith("http") else "", stem)
    if new != body:
        txt = out.read_text(); out.write_text(txt.replace(body, new, 1))
    if ok or bad: print(f"  remote images: {ok} downloaded to raw/attachments/" + (f", {bad} failed (kept their URL)" if bad else ""))
    return new
def pdf_to_md(p):
    """PDF -> (markdown text, title from PDF metadata or ''). Text only, images are dropped."""
    try: import pymupdf4llm, pymupdf
    except ImportError: sys.exit("PDF support needs: pip3 install --user pymupdf4llm")
    with pymupdf.open(p) as d: meta = (d.metadata or {}).get("title") or ""
    return pymupdf4llm.to_markdown(str(p), show_progress=False).strip(), meta.strip()
def state(): return json.load(open(STATE)) if STATE.exists() else {"articles": {}, "daily": {}}
def save(s): STATE.write_text(json.dumps(s, indent=1, ensure_ascii=False))
def slugify(t): return (re.sub(r"[^a-zA-Z0-9]+", "-", t).strip("-").lower()[:70] or "page")
def clean(u):
    u = u.rstrip(".,;:!?)\\")
    u = re.sub(r"[?&](utm_[a-z]+|r|rcm|share_via|source|ref)=[^&#]*", "", u).replace("?&", "?").rstrip("?&")
    return u.replace("\\_", "_").replace("\\&", "&")
def known_urls():
    return {(r[0], r[1]) for r in csv.reader(open(ROOT / "tools/urls.tsv"), delimiter="\t") if r}

def daily():
    s, known, new, ask = state(), known_urls(), [], []
    for p in staged(ST_D):
        m = re.fullmatch(r"(\d{4}-\d{2}-\d{2})", p.stem)
        if not m: ask.append(p.name); continue
        text = p.read_text().replace("\\_", "_").replace("\\&", "&")
        urls = []
        for u in URL.findall(text):
            u = clean(u)
            if u not in urls: urls.append(u)
        added = [(p.stem, u) for u in urls if (p.stem, u) not in known]
        new += added; s["daily"][p.name] = {"urls": urls, "date": p.stem}
        print(f"{p.name}: {len(urls)} links, {len(added)} new")
    if new:
        with open(ROOT / "tools/urls.tsv", "a") as f:
            for d, u in new: f.write(f"{d}\t{u}\n")
    save(s)
    for a in ask: print(f"ASK: {a} is not named YYYY-MM-DD. Which date is it?")
    print(f"{len(new)} links added to urls.tsv. Next: python3 tools/fetch.py --new")

def article():
    s = state(); ask = []
    for p in staged(ST_A):
        fm, pdf = {}, p.suffix.lower() == ".pdf"
        if pdf:
            t, ptitle = pdf_to_md(p)
            if len(re.sub(r"\s+|-----", "", t)) < 200: print(f"SKIP {p.name}: no extractable text (scanned PDF? needs OCR)"); continue
            if ptitle: fm["title"] = ptitle
        else: t = p.read_text()
        if not pdf and t.startswith("---\n"):
            _, f, t = t.split("---\n", 2)
            fm = dict(re.findall(r"^(\w+):\s*(.*)$", f, re.M))
        rel = p.relative_to(ST_A).parts
        hint = fm.get("project", "").strip('"') or (rel[0] if len(rel) > 1 else "")
        title = fm.get("title", "").strip('"') or (re.search(r"^#\s+(.+)$", t, re.M) or [None, ""])[1] or p.stem.replace("-", " ")
        src = fm.get("source", "").strip('"') or fm.get("url", "").strip('"') or f"local:{p.name}"
        stem = f"{slugify(title)}-{hashlib.md5(src.encode()).hexdigest()[:6]}"
        out = ROOT / "raw" / f"{stem}.md"
        if out.exists():
            print(f"SKIP {p.name}: already in raw/ as {stem}"); s["articles"][p.name] = stem
            if hint: s.setdefault("hints", {})[stem] = hint
            continue
        today = datetime.date.today().isoformat(); conv = "pdf" if pdf else "staged"
        head = f'---\nsource: "{src}"\ntitle: "{title.replace(chr(34), chr(39))}"\ndaily_note: {fm.get("daily_note", today)}\nconverter: {conv}\n---\n\n'
        body = t.lstrip("\n")
        if not re.match(r"#\s", body): body = f"# {title}\n\n" + body
        out.write_text(head + body)
        s["articles"][p.name] = stem
        if not pdf:
            take_images(body, p.parent, stem, s)
            body = remote_images(out, body, src, stem)
        if hint: s.setdefault("hints", {})[stem] = hint
        print(f"{p.name} -> raw/{stem}.md  (needs summary + classification)" + (f"  [project hint: {hint}]" if hint else ""))
    save(s)
    if not staged(ST_A): print("no staged articles")

def finish():
    s, C = state(), json.load(open(ROOT / "tools/classification.json"))
    done = lambda stem: (ROOT / f"raw/{stem}.summary.md").exists() and stem in C
    for name, stem in list(s["articles"].items()):
        found = [q for q in ST_A.rglob(name) if q.is_file()]
        if done(stem) and found:
            f = found[0]
            if f.suffix.lower() == ".pdf":
                ARCH_PDF.mkdir(parents=True, exist_ok=True); dest = ARCH_PDF / name
                if dest.exists(): dest = ARCH_PDF / f"{f.stem}-{datetime.date.today().isoformat()}.pdf"
                shutil.move(str(f), str(dest)); print(f"archived staged PDF {name} -> 04_Archive/pdf/")
            else: f.unlink(); print(f"removed staged article {name}")
            if f.parent != ST_A and f.parent.exists() and not any(f.parent.iterdir()): f.parent.rmdir()
            del s["articles"][name]
            for rel in s.get("images", {}).pop(stem, []):
                q, d = ROOT / rel, RAW_ATT / Path(rel).name
                if q.is_file() and d.is_file() and q.read_bytes() == d.read_bytes():
                    q.unlink(); print(f"moved image {Path(rel).name} -> raw/attachments/")
                    d_ = q.parent
                    while d_ != ST_A and d_.is_relative_to(ST_A) and d_.exists() and not any(d_.iterdir()): d_.rmdir(); d_ = d_.parent
    res = {(x["date"], x["url"]): x for x in json.load(open(ROOT / "tools/results.json"))}
    for name, info in list(s["daily"].items()):
        src = ST_D / name
        if not src.exists(): continue
        pending = []
        for u in info["urls"]:
            x = res.get((info["date"], u))
            if not x: pending.append(u)
            elif x["ok"] and not done(Path(x["file"]).stem): pending.append(u)
        if pending: print(f"KEEP {name}: {len(pending)} links not summarised/classified yet"); continue
        ARCH.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(ARCH / name)); print(f"archived {name} -> 04_Archive/daily-notes/"); del s["daily"][name]
    save(s)

def status():
    C = json.load(open(ROOT / "tools/classification.json"))
    stems = [Path(f).stem for f in glob.glob(str(ROOT / "raw/*.md")) if not f.endswith(".summary.md")]
    print("staged daily notes:", [p.name for p in staged(ST_D)])
    print("staged articles:   ", [p.name for p in staged(ST_A)])
    print("raw without summary:", [x for x in stems if not (ROOT / f"raw/{x}.summary.md").exists()])
    print("raw unclassified:   ", [x for x in stems if x not in C])
    res = json.load(open(ROOT / "tools/results.json")); have = {(x["date"], x["url"]) for x in res}
    rows = {tuple(r[:2]) for r in csv.reader(open(ROOT / "tools/urls.tsv"), delimiter="\t") if r}
    print("urls not yet fetched:", len(rows - have), "| failed:", sum(1 for x in res if not x["ok"]))

def vocab():
    import collections
    C = json.load(open(ROOT / "tools/classification.json"))
    sys.path.insert(0, str(ROOT / "tools")); from descriptions import D
    seed = {"topics": "topic", "people": "person", "entities": "entity", "concepts": "concept"}
    for k in ("topics", "people", "entities", "concepts"):
        c = collections.Counter(t for v in C.values() for t in v[k])
        for t, (typ, _) in D.items():
            if typ == seed[k] and t not in c: c[t] = 0   # seeded in descriptions.py, no article yet
        print(f"\n{k} ({len(c)}): " + ", ".join(f"{t} {n}" for t, n in c.most_common()))

def classify():
    a = sys.argv[2:]
    if not a: sys.exit(__doc__)
    stem, opts = a[0], dict(zip(a[1::2], a[2::2]))
    if not (ROOT / f"raw/{stem}.md").exists(): sys.exit(f"no raw/{stem}.md")
    C = json.load(open(ROOT / "tools/classification.json"))
    prev = C.get(stem, {}).get("project", "")
    C[stem] = {k: [x.strip() for x in opts.get("--" + k, "").split(",") if x.strip()] for k in ("topics", "people", "entities", "concepts")}
    proj = opts.get("--project", prev)
    if proj:
        from importlib import import_module
        sys.path.insert(0, str(ROOT / "tools")); P = import_module("para").PROJECTS
        if proj not in P: sys.exit(f"unknown project {proj!r}; known: {list(P)}")
        C[stem]["project"] = proj
    json.dump(dict(sorted(C.items())), open(ROOT / "tools/classification.json", "w"), indent=1, ensure_ascii=False)
    print("classified", stem, C[stem])

def _projects():
    sys.path.insert(0, str(ROOT / "tools")); from importlib import import_module
    return import_module("para").PROJECTS

def _stem(q, C):
    hits = [k for k in C if q == k or q in k]
    if len(hits) != 1: sys.exit(f"{q!r} matches {len(hits)} articles: {hits[:5]}")
    return hits[0]

def attach():
    """attach <stem-or-part> <project|->  (one project per article; - removes)"""
    if len(sys.argv) < 4: sys.exit(attach.__doc__)
    C = json.load(open(ROOT / "tools/classification.json")); stem = _stem(sys.argv[2], C); proj = sys.argv[3]
    if proj == "-": C[stem].pop("project", None)
    else:
        if proj not in _projects(): sys.exit(f"unknown project {proj!r}; known: {list(_projects())}")
        C[stem]["project"] = proj
    json.dump(dict(sorted(C.items())), open(ROOT / "tools/classification.json", "w"), indent=1, ensure_ascii=False)
    print("attached", stem, "->", proj)

def suggest():
    """suggest [stem-or-part ...]: project proposals for classified articles with no project.
    Score = shared tags with the project's hubs. 3 or more proposes it (2 is too noisy). Hints from staging folder or front matter win."""
    C = json.load(open(ROOT / "tools/classification.json")); P = _projects(); st = state()
    stems = [_stem(q, C) for q in sys.argv[2:]] or [k for k, v in C.items() if not v.get("project")]
    for stem in stems:
        v = C[stem]; tags = set(v["topics"] + v["people"] + v["entities"] + v["concepts"])
        if st.get("hints", {}).get(stem): print(f"HINT  {stem} -> {st['hints'][stem]}"); continue
        if not P: continue
        sc = sorted(((len(tags & set(pr["hubs"])), n) for n, pr in P.items()), reverse=True)
        if sc[0][0] >= 3 and (len(sc) < 2 or sc[0][0] > sc[1][0]): print(f"SUGGEST {stem} -> {sc[0][1]} (score {sc[0][0]})")
        elif sc[0][0] >= 3: print(f"TIE   {stem}: " + ", ".join(f"{n} ({s})" for s, n in sc if s == sc[0][0]))

def summary():
    stem = sys.argv[2] if len(sys.argv) > 2 else sys.exit(__doc__)
    src = ROOT / f"raw/{stem}.md"
    if not src.exists(): sys.exit(f"no raw/{stem}.md")
    fm = dict(re.findall(r"^(\w+):\s*(.*)$", src.read_text().split("---\n", 2)[1], re.M))
    body = sys.stdin.read().strip()
    if not body: sys.exit("empty summary on stdin")
    title = fm["title"].strip('"')
    out = ROOT / f"raw/{stem}.summary.md"
    out.write_text(f'---\nsource: {fm["source"]}\ntitle: "{title}"\nfull_text: {stem}.md\ndaily_note: {fm["daily_note"]}\n---\n\n# Summary: {title}\n\n{body}\n')
    print("wrote", out.relative_to(ROOT))

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    {"daily": daily, "article": article, "finish": finish, "status": status, "vocab": vocab, "classify": classify, "summary": summary, "attach": attach, "suggest": suggest}.get(cmd, lambda: sys.exit(__doc__))()
