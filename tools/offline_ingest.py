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


def discover_sitemaps(scope: str, timeout: int = 10, max_urls: int = 2000):
    """
    Try to find sitemap URLs for a given domain (scope) via common locations and robots.txt.
    Returns a set of canonicalized URLs limited by max_urls.
    """
    candidates = [
        f"https://{scope}/sitemap.xml",
        f"https://{scope}/sitemap_index.xml",
        f"http://{scope}/sitemap.xml",
        f"http://{scope}/sitemap_index.xml",
        f"https://{scope}/robots.txt",
        f"http://{scope}/robots.txt",
    ]

    sitemap_urls = set()

    for c in candidates:
        try:
            r = requests.get(c, timeout=timeout, headers={"User-Agent": "QuadbitOfflineIngest/1.0"})
            if r.status_code >= 400:
                continue
            url_lower = c.lower()
            if url_lower.endswith("robots.txt"):
                for line in r.text.splitlines():
                    if line.lower().startswith("sitemap:"):
                        sm = line.split(":", 1)[1].strip()
                        try:
                            sm_c = canonicalize_url(sm)
                            if in_domain(sm_c, scope):
                                sitemap_urls.add(sm_c)
                        except Exception:
                            continue
            else:
                # Basic XML <loc> extraction
                for loc in re.findall(r"(?is)<loc>\s*([^<]+?)\s*</loc>", r.text or ""):
                    try:
                        sm_c = canonicalize_url(loc)
                        if in_domain(sm_c, scope):
                            sitemap_urls.add(sm_c)
                    except Exception:
                        continue
        except Exception:
            continue

        if len(sitemap_urls) >= max_urls:
            break

    # Trim to max_urls
    if len(sitemap_urls) > max_urls:
        sitemap_urls = set(list(sitemap_urls)[:max_urls])

    return sitemap_urls


def main():
    ap = argparse.ArgumentParser(description="Offline ingestion builder (off-server)")
    ap.add_argument("--input", required=True, help="Input URL list file")
    ap.add_argument("--out", required=True, help="Output directory")
    ap.add_argument("--timeout", type=int, default=15)
    ap.add_argument("--shard-size", type=int, default=1000)
    ap.add_argument("--max-urls", type=int, default=0, help="0 = all")
    ap.add_argument("--crawl-subpages", action="store_true", default=True)
    ap.add_argument("--max-depth", type=int, default=3)
    ap.add_argument("--max-pages-per-domain", type=int, default=400)
    ap.add_argument("--max-total-pages", type=int, default=120000)
    ap.add_argument("--min-words", type=int, default=100)
    ap.add_argument("--trust-weight", type=float, default=0.01)
    ap.add_argument("--push-endpoint", default="", help="Optional memory/store endpoint for live push")
    ap.add_argument("--push-timeout", type=int, default=20)
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
    push_ok = 0
    push_err = 0

    pages_per_domain = defaultdict(int)
    total_pages = 0
    depth_counts = defaultdict(int)
    max_depth_observed = 0
    deepest_urls = []  # list of (depth, url)
    sitemap_total = 0
    sitemap_used = []

    for seed in urls:
        seed_url = canonicalize_url(seed)
        scope = domain_scope(seed_url)
        q = deque([(seed_url, 0)])
        # Prefill with sitemap URLs if available
        for sm_url in discover_sitemaps(scope, timeout=args.timeout):
            sitemap_total += 1
            sitemap_used.append(sm_url)
            q.append((sm_url, 0))
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
                        "trust_weight": args.trust_weight,
                        "fetched_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                        "accuracy_caveat": ACCURACY_CAVEAT,
                        "content": text[:20000],
                        "crawl_depth": depth,
                    }
                    raw_records.append(rec)

                    if args.push_endpoint:
                        payload = {
                            "content": rec.get("content", ""),
                            "source": f"offline_ingest::{scope}",
                            "metadata": {
                                "source_url": rec.get("source_url"),
                                "source_domain": rec.get("source_domain"),
                                "url_hash": rec.get("url_hash"),
                                "content_hash": rec.get("content_hash"),
                                "coords_11d": rec.get("coords_11d"),
                                "keywords": rec.get("keywords"),
                                "trust_weight": rec.get("trust_weight"),
                                "fetched_utc": rec.get("fetched_utc"),
                                "accuracy_caveat": rec.get("accuracy_caveat"),
                                "crawl_depth": rec.get("crawl_depth"),
                            },
                        }
                        try:
                            pr = requests.post(args.push_endpoint, json=payload, timeout=args.push_timeout)
                            if pr.status_code == 200:
                                push_ok += 1
                            else:
                                push_err += 1
                        except Exception:
                            push_err += 1

                depth_counts[depth] += 1
                if depth > max_depth_observed:
                    max_depth_observed = depth
                if depth >= max_depth_observed:
                    deepest_urls.append((depth, url))

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

    # Depth diagnostics
    depth_counts_sorted = {str(k): depth_counts[k] for k in sorted(depth_counts.keys())}
    deepest_urls_sorted = sorted(deepest_urls, key=lambda x: (-x[0], x[1]))[:50]

    manifest = {
        "created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "input_count": len(urls),
        "unique_url_count": len(seen_url),
        "records_written": len(raw_records),
        "total_pages_fetched": total_pages,
        "max_pages_per_domain": args.max_pages_per_domain,
        "max_total_pages": args.max_total_pages,
        "max_depth_config": args.max_depth,
        "max_depth_observed": max_depth_observed,
        "min_words": args.min_words,
        "skipped_url_duplicates": skipped_url_dup,
        "skipped_content_duplicates": skipped_content_dup,
        "fetch_errors": fetch_errors,
        "push_endpoint": args.push_endpoint,
        "push_ok": push_ok,
        "push_err": push_err,
        "sitemap_urls_discovered": sitemap_total,
        "sample_sitemaps_used": sitemap_used[:25],
        "depth_counts": depth_counts_sorted,
        "deepest_urls_sample": [{"depth": d, "url": u} for d, u in deepest_urls_sorted],
        "shard_size": args.shard_size,
        "shards": shards,
        "duration_seconds": round(time.time() - t0, 2),
    }
    (out / "ingest_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
