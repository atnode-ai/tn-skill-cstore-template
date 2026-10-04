#!/usr/bin/env python3
"""Fetch each URL in urls.tsv, convert the HTML to markdown, save as raw/<slug>.md.
Images in the page are downloaded to raw/attachments/ and the links point at them (attachments/<slug>-<hash>.<ext>); an image that cannot be downloaded keeps its absolute URL."""
import csv, re, sys, time, json, hashlib, concurrent.futures as cf
from pathlib import Path
from urllib.parse import urlparse
import html as htmllib
from bs4 import UnicodeDammit
import requests, trafilatura
from bs4 import BeautifulSoup
from markdownify import markdownify as md
sys.path.insert(0, str(Path(__file__).resolve().parent))
from images import localize_images

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "raw"
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"

def slugify(s):
    s = re.sub(r"[^a-zA-Z0-9]+", "-", s).strip("-").lower()
    return s[:70] or "page"

def to_markdown(html, url):
    out = trafilatura.extract(html, url=url, output_format="markdown", include_links=True,
                              include_images=True, include_tables=True, favor_recall=True)
    if out and len(out) > 400:
        return out, "trafilatura"
    soup = BeautifulSoup(html, "html.parser")
    for t in soup(["script", "style", "nav", "footer", "header", "form", "noscript", "svg"]):
        t.decompose()
    node = soup.find("article") or soup.find("main") or soup.body or soup
    return md(str(node), heading_style="ATX").strip(), "markdownify"

def title_of(html):
    m = re.search(r"<title[^>]*>(.*?)</title>", html, re.S | re.I)
    return htmllib.unescape(re.sub(r"\s+", " ", m.group(1))).strip() if m else ""

def gh_raw(url):
    """github.com repo / blob URLs are blocked for scraping; use raw README/file instead"""
    m = re.match(r"https://github\.com/([^/]+)/([^/#?]+)/blob/([^/]+)/(.+)", url)
    if m: return f"https://raw.githubusercontent.com/{m[1]}/{m[2]}/{m[3]}/{m[4]}"
    m = re.match(r"https://github\.com/([^/]+)/([^/#?]+)/?$", url)
    if m: return f"https://raw.githubusercontent.com/{m[1]}/{m[2]}/HEAD/README.md"
    return None

def fetch(row):
    date, url = row
    last = None
    raw = gh_raw(url)
    if raw:
        r = requests.get(raw, headers={"User-Agent": UA}, timeout=30)
        if r.status_code < 400 and len(r.text) > 100:
            d = RAW; d.mkdir(parents=True, exist_ok=True)
            title = url.split("github.com/")[1]
            path = d / f"{slugify(title)}-{hashlib.md5(url.encode()).hexdigest()[:6]}.md"
            text, n_img, n_bad = localize_images(r.text, raw, path.stem)
            path.write_text(f'---\nsource: "{url}"\nfinal_url: "{raw}"\ntitle: "{title}"\ndaily_note: {date}\nconverter: raw\n---\n\n# {title}\n\n{text}\n', encoding="utf-8")
            return dict(date=date, url=url, final=raw, status=200, ok=True, title=title, file=str(path.relative_to(ROOT)), chars=len(r.text), images=n_img, images_failed=n_bad)
    for attempt in range(4):
        try:
            r = requests.get(url, headers={"User-Agent": UA, "Accept-Language": "en,de;q=0.8"},
                             timeout=30, allow_redirects=True)
            if r.status_code == 429:
                time.sleep(5 * (attempt + 1)); last = "429"; continue
            if r.status_code >= 400:
                return dict(date=date, url=url, final=r.url, status=r.status_code, ok=False)
            ctype = r.headers.get("content-type", "").lower()
            host = urlparse(r.url).netloc
            if "html" not in ctype and "xml" not in ctype:
                return dict(date=date, url=url, final=r.url, status=r.status_code, ok=False, note=f"skipped: {ctype.split(';')[0] or 'unknown type'}")
            if any(h in host for h in ("amazon.", "nettoshop.")):
                return dict(date=date, url=url, final=r.url, status=r.status_code, ok=False, note="skipped: shop/product page")
            html = UnicodeDammit(r.content, is_html=True).unicode_markup
            body, how = to_markdown(html, r.url)
            title = title_of(html)
            if len(body) < 200:
                return dict(date=date, url=url, final=r.url, status=r.status_code, ok=False, title=title, note="empty extract")
            slug = slugify(title or urlparse(r.url).path)
            d = RAW; d.mkdir(parents=True, exist_ok=True)
            path = d / f"{slug}-{hashlib.md5(url.encode()).hexdigest()[:6]}.md"
            fm = f'---\nsource: "{url}"\nfinal_url: "{r.url}"\ntitle: "{title.replace(chr(34), chr(39))}"\ndaily_note: {date}\nconverter: {how}\n---\n\n'
            body, n_img, n_bad = localize_images(body, r.url, path.stem)
            path.write_text(fm + f"# {title}\n\n" + body + "\n", encoding="utf-8")
            return dict(date=date, url=url, final=r.url, status=r.status_code, ok=True, title=title, file=str(path.relative_to(ROOT)), chars=len(body), images=n_img, images_failed=n_bad)
        except Exception as e:
            last = str(e)[:120]; time.sleep(2)
    return dict(date=date, url=url, ok=False, error=last)

def add_date(file_rel, date):
    """a URL already stored was saved again on another day: record the extra date"""
    for suffix in (".md", ".summary.md"):
        f = ROOT / (file_rel if suffix == ".md" else file_rel[:-3] + suffix)
        if not f.exists(): continue
        t = f.read_text()
        m = re.search(r"^daily_note: (.*)$", t, re.M)
        if m and date not in m.group(1):
            f.write_text(t.replace(m.group(0), m.group(0) + ", " + date, 1))

if __name__ == "__main__":
    usage = "usage: fetch.py --new | --retry | --all   (--all refetches everything and overwrites results.json)"
    mode = next((a for a in sys.argv[1:] if a in ("--new", "--retry", "--all")), None)
    if not mode: sys.exit(usage)
    if not (ROOT / "tools/urls.tsv").exists(): sys.exit("No content store here yet. Run: python3 tools/init.py")
    rows = [tuple(r) for r in csv.reader(open(ROOT / "tools/urls.tsv"), delimiter="\t") if r]
    seen, uniq = set(), []
    for r in rows:
        if r not in seen: seen.add(r); uniq.append(r)
    rp = ROOT / "tools/results.json"
    old = json.load(open(rp)) if rp.exists() else []
    if mode == "--retry":
        todo = [(x["date"], x["url"]) for x in old if not x["ok"]]
        res = [x for x in old if x["ok"]]
        for row in todo:
            res.append(fetch(row)); time.sleep(4)
    elif mode == "--new":
        have = {(x["date"], x["url"]) for x in old}
        by_url = {x["url"]: x for x in old if x["ok"]}
        res = list(old)
        for d, u in [r for r in uniq if r not in have]:
            if u in by_url:      # same page, new day
                x = dict(by_url[u], date=d); res.append(x); add_date(x["file"], d)
            else:
                res.append(fetch((d, u))); time.sleep(2)
    else:
        with cf.ThreadPoolExecutor(max_workers=4) as ex:
            res = list(ex.map(fetch, uniq))
    rp.write_text(json.dumps(res, indent=1, ensure_ascii=False))
    ok = sum(r["ok"] for r in res); print(f"{ok}/{len(res)} ok")
