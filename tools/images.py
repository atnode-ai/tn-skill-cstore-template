"""Download the images of a page into raw/attachments/ and point the markdown links at them. Used by fetch.py and ingest.py."""
import re, time, hashlib
from pathlib import Path
from urllib.parse import urljoin
import requests

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "raw"
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
ATT = RAW / "attachments"
IMG_TYPES = {"image/webp": "webp", "image/png": "png", "image/jpeg": "jpg", "image/jpg": "jpg", "image/gif": "gif", "image/svg+xml": "svg", "image/avif": "avif", "image/bmp": "bmp"}
MDIMG = re.compile(r"(!\[[^\]]*\]\(<?)([^)\s>]+)")

def localize_images(body, base, stem):
    """Download the images of a fetched page into raw/attachments/ and point the markdown links at them.
    Relative and protocol-relative URLs are resolved against `base`. Returns (new body, downloaded, failed).
    Skipped: data: URIs, YouTube links, non-images, files over 15 MB, tracking pixels. Failures keep the absolute URL."""
    cache, ok, bad = {}, 0, 0
    def one(u):
        nonlocal ok, bad
        if u in cache: return cache[u]
        cache[u] = None
        if re.match(r"(data|blob|javascript):", u, re.I) or "youtube.com" in u or "youtu.be" in u: return None
        h = hashlib.sha1(u.encode()).hexdigest()[:6]
        have = next(iter(ATT.glob(f"*-{h}.*")), None) if ATT.is_dir() else None
        if have: cache[u] = have.name; ok += 1; return have.name
        for attempt in range(2):
            try:
                r = requests.get(u, headers={"User-Agent": UA, "Accept": "image/*,*/*;q=0.8", "Referer": base}, timeout=25)
                if r.status_code == 429: time.sleep(3 * (attempt + 1)); continue
                ext = IMG_TYPES.get(r.headers.get("content-type", "").split(";")[0].strip().lower())
                if r.status_code != 200 or not ext or len(r.content) < 200 or len(r.content) > 15_000_000: break
                ATT.mkdir(parents=True, exist_ok=True)
                name = f"{stem[:40].rstrip('-')}-{h}.{ext}"
                (ATT / name).write_bytes(r.content); cache[u] = name; ok += 1; return name
            except Exception: time.sleep(1)
        bad += 1; return None
    def sub(m):
        u = m.group(2)
        if u.startswith("attachments/"): return m.group(0)
        full = urljoin(base, u)
        if not full.lower().startswith(("http://", "https://")): return m.group(0)
        name = one(full)
        return m.group(1) + (f"attachments/{name}" if name else full)
    return MDIMG.sub(sub, body), ok, bad
