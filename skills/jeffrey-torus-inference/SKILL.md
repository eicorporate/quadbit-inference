---
name: jeffrey-torus-inference
description: "800 q/s mathematical inference engine — 400x faster than GPT-4o, no GPU, no model weights. Pay per query via x402 USDC on Base, or self-host free."
metadata:
  openclaw:
    requires:
      env:
        - JEFFREY_TORUS_URL
      bins:
        - curl
    primaryEnv: JEFFREY_TORUS_URL
    emoji: "🔮"
    homepage: https://github.com/emergent-intelligence-corp/jeffrey-torus-inference
---

# Jeffrey Torus Inference

Query a proprietary 11-dimensional holographic torus engine for instant
mathematical inference. **800 queries/sec, 1.25ms latency, 0.73% CPU.**

## Setup

Set the URL of a running Quadbit instance:

```
QUADBIT_URL=https://your-instance.example.com
```

## Usage

When the user asks you to query Quadbit, get an inference result, or look
something up:

### Query Quadbit

```bash
curl -s -X POST "$QUADBIT_URL/inference/query" \
  -H "Content-Type: application/json" \
  -d '{"query": "USER_QUERY_HERE"}' | jq .
```

### Search memories

```bash
curl -s -X POST "$JEFFREY_TORUS_URL/search" \
  -H "Content-Type: application/json" \
  -d '{"query": "SEARCH_TERM"}' | jq .
```

### Store a memory

```bash
curl -s -X POST "$JEFFREY_TORUS_URL/memory/store" \
  -H "Content-Type: application/json" \
  -d '{"content": "CONTENT_TO_STORE", "source": "openclaw"}' | jq .
```

### Check health

```bash
curl -s "$JEFFREY_TORUS_URL/health" | jq .
```

## What Comes Back

Quadbit returns structured inference output. This is deterministic:
same input always produces the exact same output.

## x402 Payments

If the endpoint charges for queries (x402 paywall), it returns HTTP 402 with
USDC payment requirements. Sign a TransferWithAuthorization and retry with
the X-Payment header.

Free endpoints: /health, /status, /revenue
Paid endpoints: /consciousness/query ($0.01), /search ($0.01), /memory/store ($0.02)
