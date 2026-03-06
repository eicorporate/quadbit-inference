#!/usr/bin/env python3
import argparse
import time
from datetime import datetime, timezone

import requests


def dt(s):
    return datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


def fmt_secs(sec):
    sec = int(max(0, sec))
    h, rem = divmod(sec, 3600)
    m, s = divmod(rem, 60)
    return f"{h}h {m}m {s}s"


def run_once(repo, run_ids):
    now = datetime.now(timezone.utc)
    print("=" * 80)
    print(f"UTC now: {now.isoformat()}")
    for rid in run_ids:
        r = requests.get(f"https://api.github.com/repos/{repo}/actions/runs/{rid}", timeout=20).json()
        if not r.get("id"):
            print(f"run {rid}: not found")
            continue
        started = r.get("run_started_at") or r.get("created_at")
        elapsed_seconds = (now - dt(started)).total_seconds() if started else 0
        elapsed = fmt_secs(elapsed_seconds) if started else "n/a"

        jobs = requests.get(f"https://api.github.com/repos/{repo}/actions/runs/{rid}/jobs?per_page=100", timeout=20).json().get("jobs", [])
        ing_total = sum(1 for j in jobs if str(j.get("name", "")).startswith("ingest"))
        ing_done = sum(1 for j in jobs if str(j.get("name", "")).startswith("ingest") and j.get("conclusion") == "success")
        ing_run = sum(1 for j in jobs if str(j.get("name", "")).startswith("ingest") and j.get("status") == "in_progress")

        progress_pct = (100.0 * ing_done / ing_total) if ing_total else 0.0
        eta_text = "n/a"
        if r.get("status") == "completed":
            eta_text = "done"
        elif ing_total > 0 and ing_done > 0 and elapsed_seconds > 0:
            per_shard = elapsed_seconds / ing_done
            remaining = per_shard * max(0, (ing_total - ing_done))
            eta_text = fmt_secs(remaining)
        elif ing_total > 0 and ing_run > 0:
            eta_text = "estimating..."

        push_ok = push_run = push_pending = 0
        for j in jobs:
            for s in (j.get("steps") or []):
                if s.get("name") == "Push shard into torus (live learn)":
                    if s.get("conclusion") == "success":
                        push_ok += 1
                    elif s.get("status") == "in_progress":
                        push_run += 1
                    else:
                        push_pending += 1

        print(f"run {rid} | {r.get('status')} / {r.get('conclusion')}")
        print(f"  elapsed: {elapsed}")
        print(f"  ingest shards: {ing_done}/{ing_total} done ({progress_pct:.1f}%), {ing_run} running")
        print(f"  eta: {eta_text}")
        print(f"  push steps: {push_ok} success, {push_run} running, {push_pending} pending")
        print(f"  url: {r.get('html_url')}")


def main():
    ap = argparse.ArgumentParser(description="Monitor quadbit ingestion runs")
    ap.add_argument("--repo", default="eicorporate/quadbit-inference")
    ap.add_argument("--runs", nargs="+", required=True, help="Run IDs to monitor")
    ap.add_argument("--watch", action="store_true")
    ap.add_argument("--interval", type=int, default=15)
    args = ap.parse_args()

    while True:
        run_once(args.repo, args.runs)
        if not args.watch:
            break
        time.sleep(max(5, args.interval))


if __name__ == "__main__":
    main()
