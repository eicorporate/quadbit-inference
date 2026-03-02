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
            yield json.loads(line)


def main():
    ap = argparse.ArgumentParser(description="Import offline shards into torus with low CPU impact")
    ap.add_argument("--batch-dir", required=True)
    ap.add_argument("--torus-url", default="http://localhost:9001")
    ap.add_argument("--wave-size", type=int, default=500)
    ap.add_argument("--sleep-ms", type=int, default=50)
    args = ap.parse_args()

    bdir = Path(args.batch_dir)
    shards = sorted(bdir.glob("ingest_shard_*.jsonl"))
    if not shards:
        raise SystemExit("No ingest_shard_*.jsonl found")

    wave_count = 0
    wave_ok = 0
    total_ok = 0
    total_err = 0

    for shard in shards:
        for rec in iter_jsonl(shard):
            payload = {
                "content": rec.get("content", ""),
                "source": f"offline_ingest::{rec.get('source_url','unknown')}",
            }
            try:
                r = requests.post(f"{args.torus_url}/memory/store", json=payload, timeout=10)
                if r.status_code == 200:
                    wave_ok += 1
                    total_ok += 1
                else:
                    total_err += 1
            except Exception:
                total_err += 1

            wave_count += 1
            if wave_count >= args.wave_size:
                print(json.dumps({
                    "wave": int((total_ok + total_err) / max(1, args.wave_size)),
                    "wave_processed": wave_count,
                    "wave_ok": wave_ok,
                    "total_ok": total_ok,
                    "total_err": total_err,
                    "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                }))
                wave_count = 0
                wave_ok = 0
                time.sleep(args.sleep_ms / 1000.0)

    print(json.dumps({
        "status": "done",
        "total_ok": total_ok,
        "total_err": total_err,
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    }))


if __name__ == "__main__":
    main()
