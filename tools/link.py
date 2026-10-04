#!/usr/bin/env python3
"""Add Obsidian [[backlinks]]: front matter tags, inline links in summaries,
hub notes in notes/. Re-runnable: rebuilds notes/,
strips and re-applies links in raw/*.summary.md."""
import re, sys, glob, json, collections, os
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import descriptions
D = descriptions.D
ALIASES = getattr(descriptions, "ALIASES", {})  # term -> regex patterns that count as a mention
from para import AREAS, PROJECTS, ARCHIVE, RESOURCE_GROUPS
if not (ROOT / "tools/classification.json").exists(): sys.exit("No content store here yet. Run: python3 tools/init.py")
C = json.load(open(ROOT / "tools/classification.json"))

MIN_LINKS = 2
files = sorted(f for f in glob.glob(str(ROOT / "raw/*.md")) if not f.endswith(".summary.md"))
stems = [Path(f).stem for f in files]
unclassified = [x for x in stems if x not in C]
nosummary = [x for x in stems if not (ROOT / "raw" / f"{x}.summary.md").exists()]
if unclassified or nosummary:
    sys.exit("BLOCKED. Unclassified: %s | Missing summary: %s" % (unclassified, nosummary))
stale = [x for x in C if x not in stems]
if stale: sys.exit("classification.json has entries without a file: %s" % stale)

# normalise: Ray Dalio is a person, not a topic; entity == topic duplicates dropped
art = {}
for f in files:
    i = Path(f).stem
    topics, people, ents, concs = (list(C[i][k]) for k in ("topics", "people", "entities", "concepts"))
    for t in list(topics):
        if t in D and D[t][0] == "person":
            topics.remove(t); people.append(t) if t not in people else None
    ents = [e for e in ents if e not in topics]
    proj = C[i].get("project") or ""
    if proj and proj not in PROJECTS: sys.exit("BLOCKED. %s: project %r is not in tools/para.py PROJECTS" % (i, proj))
    art[i] = dict(file=Path(f), topics=topics, people=people, ents=ents, concs=concs, project=proj)

cnt = [collections.Counter(), collections.Counter()]
for a in art.values():
    cnt[0].update(set(a["ents"])); cnt[1].update(set(a["concs"]))
LINKED = {t for c in cnt for t, n in c.items() if n >= MIN_LINKS}
LINKED |= {t for a in art.values() for t in a["topics"] + a["people"]}

def fm_split(text):
    _, fm, body = text.split("---\n", 2)
    return fm, body
def fm_get(fm, key):
    m = re.search(rf"^{key}: (.*)$", fm, re.M); return m.group(1).strip() if m else ""
def q(s): return '"' + s.replace('"', "'") + '"'
def link(t): return f"[[{t}]]" if t in LINKED else t
def yl(items): return "[" + ", ".join(q(link(t)) for t in items) + "]"

def patterns(term):
    if term in ALIASES: return ALIASES[term]
    pats = [re.escape(term)]
    if D.get(term, ("",))[0] == "person":
        pats.append(re.escape(term.split()[-1]))      # surname alias
    return pats

def inject(text, terms):
    """link first mention of each term (longest pattern first), skipping existing [[..]]"""
    for term in terms:
        if term not in LINKED: continue
        done = False
        for pat in patterns(term):
            for m in re.finditer(rf"(?<![\w\[|/])({pat})(?![\w\]|])", text):
                # skip if inside an existing wikilink
                pre = text[:m.start()]
                if pre.count("[[") > pre.count("]]"): continue
                shown = m.group(1)
                rep = f"[[{term}]]" if shown == term else f"[[{term}|{shown}]]"
                text = text[:m.start()] + rep + text[m.end():]; done = True; break
            if done: break
    return text

summ_name = lambda a: a["file"].stem + ".summary"
def clean_title(t):
    t = re.sub(r"\s+", " ", re.sub(r"[\[\]|#^]", "", t)).strip()
    return t if len(t) <= 90 else t[:90].rsplit(" ", 1)[0] + "…"

# ---------- article files ----------
for i, a in art.items():
    for suffix in (".md", ".summary.md"):
        p = a["file"] if suffix == ".md" else a["file"].with_name(a["file"].stem + ".summary.md")
        text = p.read_text()
        fm, body = fm_split(text)
        dates = [d.strip() for d in fm_get(fm, "daily_note").strip("[]").replace('"', "").replace("[[", "").replace("]]", "").split(",")]
        title = fm_get(fm, "title").strip('"')
        is_summary = suffix == ".summary.md"
        keep = [l for l in fm.splitlines() if not re.match(r"(daily_note|project|topics|people|entities|concepts):", l)]
        a.setdefault("dates", dates); a.setdefault("title", title)
        # drop any earlier Summary/Full text/Related lines (idempotent)
        body = re.sub(r"\A(?:\n*(?:Summary|Full text|Related):[^\n]*\n)+\n*", "\n", body)
        if is_summary:
            keep += ["daily_note: " + ", ".join(dates)]
            if a["project"]: keep += [f'project: "[[{a["project"]}]]"']
            keep += ["topics: " + yl(a["topics"]), "people: " + yl(a["people"]),
                     "entities: " + yl(a["ents"]), "concepts: " + yl(a["concs"])]
            body = re.sub(r"\[\[([^\]|]+)(?:\|([^\]]+))?\]\]", lambda m: m.group(2) or m.group(1), body)  # strip old links
            head, _, rest = body.lstrip("\n").partition("\n\n")
            body = "\n" + head + "\n\n" + inject(rest, a["people"] + a["ents"] + a["concs"]) if rest else "\n" + inject(head, a["people"] + a["ents"] + a["concs"])
            rel = f"Full text: [[{a['file'].stem}]] · Related: " + " · ".join(([f"[[{a['project']}]]"] if a["project"] else []) + [link(t) for t in a["topics"] + a["people"]])
            body = "\n" + rel + "\n" + body
        else:
            # full text keeps no backlinks: plain dates, no tags, no Summary/Related line
            keep += ["daily_note: " + ", ".join(dates)]
            body = "\n" + body.lstrip("\n")
        p.write_text("---\n" + "\n".join(keep) + "\n---\n" + body)

# ---------- hub notes ----------
import shutil
for d in ("notes",):
    shutil.rmtree(ROOT / d, ignore_errors=True); (ROOT / d).mkdir()
members = collections.defaultdict(list)
for i, a in art.items():
    for kind, terms in (("topics", a["topics"]), ("people", a["people"]), ("ents", a["ents"]), ("concs", a["concs"])):
        for t in terms:
            if t in LINKED: members[t].append(i)
def art_line(i):
    a = art[i]; return f"- [[{summ_name(a)}|{clean_title(a['title'])}]] ({a['dates'][0]})"
up_area = {h: a for a, v in AREAS.items() for h in v["hubs"]}
up_proj = collections.defaultdict(list)
for pr, v in PROJECTS.items():
    for h in v["hubs"]: up_proj[h].append(pr)
missing_desc = sorted(t for t in LINKED if t not in D)
if missing_desc: sys.exit("BLOCKED. Missing hub descriptions in tools/descriptions.py: %s" % missing_desc)
for t in sorted(LINKED):
    typ, desc = D[t]
    ids = sorted(set(members[t]), key=lambda i: (art[i]["dates"][0], i), reverse=True)  # stem breaks date ties: same output every run
    others = collections.Counter(x for i in ids for x in art[i]["topics"] + art[i]["people"] + art[i]["ents"] + art[i]["concs"] if x in LINKED and x != t)
    rel = ", ".join(f"[[{x}]]" for x, _ in others.most_common(8))
    para = "archive" if t in ARCHIVE else "resource"
    status = "stale" if t in ARCHIVE else "active"
    last = max(art[i]["dates"][0] for i in ids)
    fm = f"---\ntype: {typ}\npara: {para}\nstatus: {status}\narticles: {len(ids)}\nlast_article: {last}\n"
    if t in up_area: fm += f'area: "[[{up_area[t]}]]"\n'
    if up_proj[t]: fm += "projects: [" + ", ".join(q(f"[[{x}]]") for x in up_proj[t]) + "]\n"
    txt = fm + f"---\n\n# {t}\n\n{desc}\n\n"
    if t in ARCHIVE: txt += f"**Archived:** {ARCHIVE[t]}\n\n"
    part = [f"[[{up_area[t]}]]"] if t in up_area else []
    part += [f"[[{x}]]" for x in up_proj[t]]
    if part: txt += f"**Part of:** {', '.join(part)}\n\n"
    if rel: txt += f"**Often together with:** {rel}\n\n"
    txt += f"## Articles ({len(ids)})\n\n" + "\n".join(art_line(i) for i in ids) + "\n"
    (ROOT / "notes" / f"{t}.md").write_text(txt)

# hand-written layer: created once, never overwritten
for folder, items, kind in (("01_Projects", PROJECTS, "project"), ("02_Areas", AREAS, "area")):
    (ROOT / folder).mkdir(exist_ok=True)
    for name, v in items.items():
        f = ROOT / folder / f"{name}.md"
        if f.exists(): continue
        hubs = "\n".join(f"- [[{h}]]: {D[h][1]}" for h in v["hubs"] if h in LINKED)
        f.write_text(f"---\ntype: {kind}\nstatus: active\n---\n\n# {name}\n\n{v['text']}\n\n## Notes\n\n{hubs}\n\n## Current state\n\n(add)\n")

# refreshed article list inside each project note (only between the markers)
START, END = "<!-- cstore:articles -->", "<!-- /cstore:articles -->"
for name in PROJECTS:
    f = ROOT / "01_Projects" / f"{name}.md"
    ids = sorted((i for i, a in art.items() if a["project"] == name), key=lambda i: art[i]["dates"][0], reverse=True)
    lines = "\n".join(art_line(i) for i in ids) or "(none yet)"
    block = f"{START}\n{lines}\n{END}"
    t = f.read_text()
    if START in t and END in t:
        t = re.sub(re.escape(START) + r".*?" + re.escape(END), lambda m: block, t, flags=re.S)
    else:
        sec = f"## Articles\n\n{block}\n\n"
        t = t.replace("## Current state", sec + "## Current state", 1) if "## Current state" in t else t.rstrip() + "\n\n" + sec
    f.write_text(t)

# index
def n_of(t): return len(set(members[t]))
def li(t): return f"- [[{t}]] ({n_of(t)}): {D[t][1]}"
idx = ["# Index", "", f"{len(art)} articles, {len(LINKED)} hub notes. Source text and summaries live in `raw/`. Hubs stay flat in `notes/`; PARA position is the `para:` property.", "", "## Areas", ""]
for a, v in AREAS.items():
    idx += [f"### [[{a}]]", "", v["text"], ""] + [li(h) for h in v["hubs"] if h in LINKED] + [""]
idx += ["## Projects", ""]
for pr, v in PROJECTS.items():
    idx += [f"### [[{pr}]]", "", v["text"], "", "Hubs: " + ", ".join(f"[[{h}]]" for h in v["hubs"] if h in LINKED), ""]
idx += ["## Resources", ""]
used = {h for v in AREAS.values() for h in v["hubs"]} | set(ARCHIVE)
for grp, names in RESOURCE_GROUPS.items():
    idx += [f"### {grp}", ""] + [li(t) for t in names if t in LINKED and t not in used] + [""]
grouped = used | {h for v in PROJECTS.values() for h in v["hubs"]} | {t for v in RESOURCE_GROUPS.values() for t in v}
other = sorted((t for t in LINKED if D[t][0] == "topic" and t not in grouped), key=lambda t: (-n_of(t), t))
if other: idx += ["### Ungrouped topics", ""] + [li(t) for t in other] + [""]   # add them to an area or RESOURCE_GROUPS in tools/para.py
for typ, title in (("person", "People"), ("entity", "Orgs and tools"), ("concept", "Concepts")):
    names = sorted((t for t in LINKED if D[t][0] == typ and t not in used), key=lambda t: (-n_of(t), t))
    idx += [f"### {title}", ""] + [li(t) for t in names] + [""]
idx += ["## Archive", ""] + ([li(t) + f" Archived: {r}" for t, r in ARCHIVE.items()] or ["(empty)"]) + [""]
(ROOT / "notes" / "_index.md").write_text("\n".join(idx))

# ---------- escape stray wikilinks that come from the scraped article text ----------
known = {os.path.splitext(os.path.basename(x))[0] for x in glob.glob(str(ROOT / "**/*.md"), recursive=True)}
IMG_EXT = (".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".avif", ".bmp")
def esc(m):
    if m.group(1) and m.group(2).strip().lower().endswith(IMG_EXT): return m.group(0)   # image embed (![[x.png]]): keep, the file is in raw/attachments/
    return m.group(1) + "\\[\\[" + m.group(2) + (m.group(3) or "") + "\\]\\]"
for a in art.values():
    t = a["file"].read_text(); fm, body = fm_split(t)
    head, sep, rest = body.lstrip("\n").partition("\n")
    rest = re.sub(r"(?<!\\)(!?)\[\[([^\]|#]+)([|#][^\]]*)?\]\]", esc, rest)
    a["file"].write_text("---\n" + fm + "---\n\n" + head + sep + rest)
# ---------- README: fetch counts and the Not fetched table ----------
res = json.load(open(ROOT / "tools/results.json"))
bad = sorted((x for x in res if not x["ok"]), key=lambda x: x["date"])
def why(x): return x.get("note") or (f"HTTP {x['status']}" if x.get("status") else "connection error")
readme = ROOT / "README.md"
rd = readme.read_text() if readme.exists() else "# Content store\n\n**0 of 0 links fetched.**\n\n"
rd = re.sub(r"\*\*\d+ of \d+ links fetched\.\*\*", f"**{len(res) - len(bad)} of {len(res)} links fetched.**", rd)
rd = rd.split("## Not fetched")[0] + "## Not fetched\n\n| Date | Reason | URL |\n|---|---|---|\n" + "\n".join(f"| {x['date']} | {why(x)} | {x['url']} |" for x in bad) + "\n"
readme.write_text(rd)
print("articles", len(art), "linked notes", len(LINKED))
