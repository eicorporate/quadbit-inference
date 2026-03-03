#!/usr/bin/env python3
import argparse
import json
import time
from pathlib import Path

import requests


def iter_jsonl(path: Path):
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except Exception:
                continue


def main():
    ap = argparse.ArgumentParser(description="Push offline shard records into torus memory endpoint")
    ap.add_argument("--shard-dir", required=True, help="Directory containing ingest_shard_*.jsonl")
    ap.add_argument("--endpoint", default="https://myjeffrey.com/api/memory/store")
    ap.add_argument("--sleep-ms", type=int, default=10)
    ap.add_argument("--timeout", type=int, default=20)
    ap.add_argument("--max-records", type=int, default=0, help="0 means all")
    args = ap.parse_args()

    shard_dir = Path(args.shard_dir)
    files = sorted(shard_dir.glob("ingest_shard_*.jsonl"))
    if not files:
        print(json.dumps({"status": "no_shards", "shard_dir": str(shard_dir)}))
        return

    sent = 0
    ok = 0
    err = 0

    for fp in files:
        for rec in iter_jsonl(fp):
            if args.max_records and sent >= args.max_records:
                break

            source_domain = rec.get("source_domain") or "unknown"
            source = f"offline_ingest::{source_domain}"
            content = rec.get("content", "")
            if not content:
                continue

            payload = {
                "content": content,
                "source": source,
                "metadata": {
                    "source_url": rec.get("source_url"),
                    "source_domain": source_domain,
                    "url_hash": rec.get("url_hash"),
                    "content_hash": rec.get("content_hash"),
                    "coords_11d": rec.get("coords_11d"),
                    "keywords": rec.get("keywords"),
                    "trust_weight": rec.get("trust_weight"),
                    "fetched_utc": rec.get("fetched_utc"),
                    "accuracy_caveat": rec.get("accuracy_caveat"),
                },
            }

            try:
                r = requests.post(args.endpoint, json=payload, timeout=args.timeout)
                if r.status_code == 200:
                    ok += 1
                else:
                    err += 1
            except Exception:
                err += 1

            sent += 1
            if args.sleep_ms > 0:
                time.sleep(args.sleep_ms / 1000.0)

        if args.max_records and sent >= args.max_records:
            break

    print(json.dumps({
        "status": "done",
        "sent": sent,
        "ok": ok,
        "err": err,
        "endpoint": args.endpoint,
        "shard_dir": str(shard_dir),
    }))


if __name__ == "__main__":
    main()
