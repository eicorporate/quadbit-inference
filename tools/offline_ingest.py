#!/usr/bin/env python3
import argparse
from collections import deque
import hashlib
import html
import json
import math
import re
import time
from collections import defaultdict
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urljoin, urlsplit, urlunsplit

import requests

HARMONICS = [432.0, 528.0, 963.0, 741.0, 639.0, 852.0, 174.0, 285.0, 439.83, 698.99, 1.0]
TRACKING_PARAMS = {
    "fbclid", "gclid", "ref", "source", "utm_source", "utm_medium", "utm_campaign",
    "utm_term", "utm_content", "utm_id", "utm_name", "mc_cid", "mc_eid"
}

ACCURACY_CAVEAT = (
    "This information was retrieved and absorbed from public internet sources. "
    "While Jeffrey and Ali strive for accuracy, all legal, medical, financial, "
    "and professional information should be independently verified with a "
    "licensed professional before acting on it. Laws, medical guidelines, and "
    "regulations change frequently. Jeffrey and Ali are not lawyers, doctors, "
    "or licensed financial advisors."
)


def canonicalize_url(url: str) -> str:
    s = urlsplit(url.strip())
    scheme = "https" if s.scheme in ("http", "https", "") else s.scheme
    netloc = s.netloc.lower()
    path = s.path or "/"
    if path != "/" and path.endswith("/"):
        path = path[:-1]

    q = []
    for k, v in parse_qsl(s.query, keep_blank_values=True):
        lk = k.lower()
        if lk in TRACKING_PARAMS or lk.startswith("utm_"):
            continue
        q.append((k, v))
    query = urlencode(sorted(q))
    return urlunsplit((scheme, netloc, path, query, ""))


def domain_scope(url: str) -> str:
    host = (urlsplit(url).netloc or "").lower()
    if host.startswith("www."):
        host = host[4:]
    return host


def in_domain(url: str, scope: str) -> bool:
    host = (urlsplit(url).netloc or "").lower()
    if host.startswith("www."):
        host = host[4:]
    return host == scope or host.endswith("." + scope)


def extract_text(raw: str) -> str:
    raw = re.sub(r"(?is)<script.*?>.*?</script>", " ", raw)
    raw = re.sub(r"(?is)<style.*?>.*?</style>", " ", raw)
    raw = re.sub(r"(?is)<noscript.*?>.*?</noscript>", " ", raw)
    raw = re.sub(r"(?is)<[^>]+>", " ", raw)
    raw = html.unescape(raw)
    raw = re.sub(r"\s+", " ", raw).strip()
    return raw


def extract_links(base_url: str, raw_html: str):
    links = set()
    for href in re.findall(r'(?is)href\s*=\s*["\']([^"\']+)["\']', raw_html or ""):
        href = href.strip()
        if not href or href.startswith("#"):
            continue
        if href.startswith(("mailto:", "tel:", "javascript:")):
            continue
        joined = urljoin(base_url, href)
        try:
            c = canonicalize_url(joined)
            if c.startswith("http://") or c.startswith("https://"):
                links.add(c)
        except Exception:
            continue
    return links


def text_to_11d(text: str):
    h = hashlib.sha256(text.encode("utf-8", errors="ignore")).digest()
    coords = []
    for i in range(11):
        chunk = h[i * 2:(i * 2) + 2]
        v = int.from_bytes(chunk, "big") / 65535.0
        angle = (2.0 * math.pi * v) * HARMONICS[i]
        coords.append(round(angle, 9))
    return coords


def keywords(text: str, limit=24):
    toks = re.findall(r"[a-zA-Z][a-zA-Z0-9_\-]{2,}", text.lower())
    freq = defaultdict(int)
    for t in toks:
        freq[t] += 1
    return [k for k, _ in sorted(freq.items(), key=lambda kv: kv[1], reverse=True)[:limit]]


def load_urls(path: Path):
    urls = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        urls.append(line)
    return urls


def chunked(seq, n):
    for i in range(0, len(seq), n):
        yield seq[i:i + n]


def main():
    ap = argparse.ArgumentParser(description="Offline ingestion builder (off-server)")
    ap.add_argument("--input", required=True, help="Input URL list file")
    ap.add_argument("--out", required=True, help="Output directory")
    ap.add_argument("--timeout", type=int, default=15)
    ap.add_argument("--shard-size", type=int, default=200)
    ap.add_argument("--max-urls", type=int, default=0, help="0 = all")
    ap.add_argument("--crawl-subpages", action="store_true", default=True)
    ap.add_argument("--max-depth", type=int, default=2)
    ap.add_argument("--max-pages-per-domain", type=int, default=100)
    ap.add_argument("--max-total-pages", type=int, default=5000)
    ap.add_argument("--min-words", type=int, default=100)
    args = ap.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    urls = load_urls(Path(args.input))
    if args.max_urls and args.max_urls > 0:
        urls = urls[:args.max_urls]

    t0 = time.time()
    seen_url = set()
    seen_content = set()

    raw_records = []
    skipped_url_dup = 0
    skipped_content_dup = 0
    fetch_errors = 0

    pages_per_domain = defaultdict(int)
    total_pages = 0

    for seed in urls:
        seed_url = canonicalize_url(seed)
        scope = domain_scope(seed_url)
        q = deque([(seed_url, 0)])
        local_seen = set()

        while q:
            url, depth = q.popleft()
            if total_pages >= args.max_total_pages:
                break
            if pages_per_domain[scope] >= args.max_pages_per_domain:
                break

            uh = hashlib.sha256(url.encode("utf-8")).hexdigest()
            if uh in seen_url:
                skipped_url_dup += 1
                continue
            seen_url.add(uh)

            try:
                r = requests.get(url, timeout=args.timeout, headers={"User-Agent": "QuadbitOfflineIngest/1.0"})
                ctype = (r.headers.get("Content-Type") or "").lower()
                if not ("text/html" in ctype or "text/plain" in ctype or not ctype):
                    continue

                body = r.text if r.text else ""
                text = extract_text(body)
                if not text:
                    continue

                if len(text.split()) < args.min_words:
                    continue

                ch = hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()
                if ch in seen_content:
                    skipped_content_dup += 1
                else:
                    seen_content.add(ch)
                    rec = {
                        "source_url": url,
                        "source_domain": scope,
                        "url_hash": uh,
                        "content_hash": ch,
                        "coords_11d": text_to_11d(text),
                        "keywords": keywords(text),
                        "trust_weight": 0.55,
                        "fetched_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                        "accuracy_caveat": ACCURACY_CAVEAT,
                        "content": text[:20000],
                    }
                    raw_records.append(rec)

                pages_per_domain[scope] += 1
                total_pages += 1

                if args.crawl_subpages and depth < args.max_depth:
                    for nxt in extract_links(url, body):
                        if not in_domain(nxt, scope):
                            continue
                        if nxt in local_seen:
                            continue
                        local_seen.add(nxt)
                        q.append((nxt, depth + 1))

            except Exception:
                fetch_errors += 1

        if total_pages >= args.max_total_pages:
            break

    # write shards
    shards = []
    for i, block in enumerate(chunked(raw_records, args.shard_size), start=1):
        sp = out / f"ingest_shard_{i:05d}.jsonl"
        with sp.open("w", encoding="utf-8") as f:
            for r in block:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        shards.append(sp.name)

    manifest = {
        "created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "input_count": len(urls),
        "unique_url_count": len(seen_url),
        "records_written": len(raw_records),
        "total_pages_fetched": total_pages,
        "max_pages_per_domain": args.max_pages_per_domain,
        "max_total_pages": args.max_total_pages,
        "max_depth": args.max_depth,
        "min_words": args.min_words,
        "skipped_url_duplicates": skipped_url_dup,
        "skipped_content_duplicates": skipped_content_dup,
        "fetch_errors": fetch_errors,
        "shard_size": args.shard_size,
        "shards": shards,
        "duration_seconds": round(time.time() - t0, 2),
    }
    (out / "ingest_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
