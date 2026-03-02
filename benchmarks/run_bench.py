#!/usr/bin/env python3
"""
Benchmark runner for Jeffrey Torus Inference.
Point TORUS_URL at a running torus instance to reproduce benchmarks.

Usage:
    export TORUS_URL=http://localhost:9001
    python3 run_bench.py
"""

import requests
import time
import os
import statistics
import json
import sys

TORUS = os.environ.get("TORUS_URL", "http://localhost:9001")

def bench(name, n, make_request):
    lats = []
    ok = 0
    t0 = time.time()
    for i in range(n):
        q = time.time()
        try:
            r = make_request(i)
            lats.append((time.time() - q) * 1000)
            if r.status_code == 200:
                ok += 1
        except Exception as e:
            lats.append((time.time() - q) * 1000)
    wall = time.time() - t0
    sl = sorted(lats)
    return {
        "endpoint": name,
        "queries": n,
        "successes": ok,
        "wall_seconds": round(wall, 2),
        "queries_per_sec": round(ok / wall, 1),
        "p50_ms": round(sl[n // 2], 2),
        "p99_ms": round(sl[int(n * 0.99)], 2),
        "avg_ms": round(statistics.mean(lats), 2),
        "min_ms": round(min(lats), 2),
        "max_ms": round(max(lats), 2),
    }


def main():
    # Verify torus is up
    try:
        r = requests.get(f"{TORUS}/health", timeout=5)
        info = r.json()
        print(f"Connected to: {info.get('service', 'unknown')}")
    except Exception:
        print(f"ERROR: Cannot reach torus at {TORUS}")
        sys.exit(1)

    cq = lambda i: requests.post(
        f"{TORUS}/consciousness/query",
        json={"query": f"bench {i} {os.urandom(4).hex()}"}, timeout=5)
    hq = lambda i: requests.get(f"{TORUS}/health", timeout=5)
    mq = lambda i: requests.post(
        f"{TORUS}/memory/store",
        json={"content": f"mem {i} {os.urandom(8).hex()}"}, timeout=5)
    sq = lambda i: requests.post(
        f"{TORUS}/search",
        json={"query": f"search {i}"}, timeout=5)

    print("=" * 60)
    print("  JEFFREY TORUS — BENCHMARK")
    print("=" * 60)

    results = []
    for name, n, fn in [
        ("consciousness/query", 5000, cq),
        ("health", 5000, hq),
        ("memory/store", 3000, mq),
        ("search", 3000, sq),
    ]:
        print(f"  {name} x{n}...", end=" ", flush=True)
        r = bench(name, n, fn)
        results.append(r)
        print(f"{r['queries_per_sec']} q/s | p50={r['p50_ms']}ms | p99={r['p99_ms']}ms")

    print("=" * 60)
    print(f"  {'Endpoint':<25s} {'QPS':>8s} {'p50':>8s} {'p99':>8s}")
    print(f"  {'-'*25} {'-'*8} {'-'*8} {'-'*8}")
    for r in results:
        print(f"  {r['endpoint']:<25s} {r['queries_per_sec']:>8} {r['p50_ms']:>7}ms {r['p99_ms']:>7}ms")

    total_q = sum(r["queries"] for r in results)
    print(f"\n  Total: {total_q:,} queries")
    print("=" * 60)

    # Save results
    out = {"timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"), "results": results}
    with open("benchmarks/results.json", "w") as f:
        json.dump(out, f, indent=2)
    print("\nResults saved to benchmarks/results.json")


if __name__ == "__main__":
    main()
